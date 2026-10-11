"""Local owner routes. Public synthetic sessions cannot reach these handlers."""
import ipaddress
import json
import re
from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from . import config
from .access import hosted, private
from .database import get_personal_db
from .gmail_parser import parse_financial_email
from .gmail_service import STATE_COOKIE, GmailManager, configuration
from .models import Account, AccountDetails, DebitCard, GmailEvidence, GmailItem, Transaction
from .schemas import TransactionIn, cents
from .transactions import add_transaction, serialize_transaction
from .workspace import personal_classifier


def require_local(request: Request):
    if hosted(request):
        if request.url.path == "/api/workspace" and hasattr(request.state, "identity"):
            return
        if not private(request):
            raise HTTPException(403, "Gmail requires an authenticated private workspace.")
        return
    if request.cookies.get("moniq_workspace") == "scenario" and request.url.path.startswith("/api/gmail/"):
        raise HTTPException(403, "Real Gmail is unavailable inside the isolated synthetic scenario.")
    if getattr(request.app.state, "public_demo", config.PUBLIC_DEMO):
        raise HTTPException(403, "Gmail and personal accounts are unavailable in public demo sessions.")
    try:
        loopback = ipaddress.ip_address(request.client.host).is_loopback
    except (ValueError, AttributeError):
        loopback = False
    if not loopback or request.url.hostname not in {"127.0.0.1", "localhost"}:
        raise HTTPException(403, "Personal finance is available only to the local owner on loopback.")
    callback = request.url.path == "/api/gmail/callback"
    origin = request.headers.get("origin")
    allowed = {*config.CORS_ORIGINS, config.GMAIL_FRONTEND_URL.rstrip("/"), "http://127.0.0.1:8000", "http://localhost:8000"}
    if (origin and origin not in allowed) or (not callback and request.headers.get("sec-fetch-site") == "cross-site"):
        raise HTTPException(403, "Use your local Moniq frontend to access personal finance.")
    if not callback and request.method in {"POST", "PUT", "DELETE"} and not origin:
        raise HTTPException(403, "An authorized local browser Origin is required.")


router = APIRouter(prefix="/api", dependencies=[Depends(require_local)])


def manager(request):
    if hosted(request):
        from .hosted_gmail import HostedGmailManager
        require_local(request)
        return HostedGmailManager(request.app.state.identity_store, request.state.identity)
    if getattr(request.app.state, "gmail", None) is None:
        request.app.state.gmail = GmailManager()
    return request.app.state.gmail


def validate_personal_transaction(request, payload, db):
    if not private(request):
        return
    details = db.get(AccountDetails, payload.account_id)
    if not details:
        raise HTTPException(422, "Register and choose a personal account in Settings first.")
    if payload.date < details.balance_date or payload.date > config.today():
        raise HTTPException(422, "Use a posted date between the account's starting-balance date and today.")
    if payload.kind == "income" and details.account_type == "credit":
        raise HTTPException(422, "Choose a checking or savings account for income.")


class WorkspaceIn(BaseModel):
    workspace: str = Field(pattern="^(demo|personal|scenario)$")


@router.post("/workspace")
def switch_workspace(payload: WorkspaceIn, request: Request, response: Response):
    if hosted(request):
        from .identity import MODE_COOKIE, SESSION_SECONDS
        if not hasattr(request.state, "identity") or payload.workspace == "scenario":
            raise HTTPException(403, "Choose your authenticated private workspace or the separate demo.")
        if payload.workspace == "demo":
            from .demo_sessions import COOKIE_NAME
            token = request.app.state.demo_store.bootstrap(request.cookies.get(COOKIE_NAME))
            response.set_cookie(COOKIE_NAME, token, httponly=True, secure=True, samesite="lax", max_age=config.SESSION_TTL_SECONDS)
        response.set_cookie(MODE_COOKIE, payload.workspace, httponly=True, secure=True, samesite="lax", path="/", max_age=SESSION_SECONDS)
        return {"workspace": payload.workspace}
    response.set_cookie("moniq_workspace", payload.workspace, httponly=True, samesite="lax", secure=False, max_age=2592000)
    return {"workspace": payload.workspace}


class RegisteredAccountIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    account_type: str = Field(pattern="^(checking|savings|credit)$")
    last_four: str | None = Field(default=None, pattern=r"^\d{4}$")
    opening_balance: Decimal = Field(ge=-1_000_000, le=1_000_000)
    balance_date: date

    @field_validator("opening_balance")
    @classmethod
    def exact_cents(cls, value):
        cents(value)
        return value

    @field_validator("name")
    @classmethod
    def nonempty_name(cls, value):
        if not value.strip():
            raise ValueError("Account name is required.")
        return value.strip()


def account_rows(db):
    result = []
    for account in db.scalars(select(Account).order_by(Account.id)):
        details = db.get(AccountDetails, account.id)
        if not details:
            continue
        posted = sum(t.amount_cents for t in db.scalars(select(Transaction).where(Transaction.account_id == account.id, Transaction.date <= config.today())))
        result.append({"id": account.id, "name": account.name, "account_type": details.account_type, "last_four": details.last_four,
                       "opening_balance": account.opening_balance_cents / 100, "balance_date": details.balance_date.isoformat(),
                       "balance": (account.opening_balance_cents + posted) / 100, "estimated": True,
                       "outstanding": max(0, -(account.opening_balance_cents + posted)) / 100 if details.account_type == "credit" else None,
                       "debit_cards": [{"id": c.id, "name": c.name, "last_four": c.last_four} for c in db.scalars(select(DebitCard).where(DebitCard.account_id == account.id))]})
    return result


@router.get("/gmail/accounts")
def registered_accounts(db: Session = Depends(get_personal_db)):
    return account_rows(db)


@router.post("/gmail/accounts", status_code=201)
def register_account(payload: RegisteredAccountIn, db: Session = Depends(get_personal_db)):
    if payload.balance_date > config.today():
        raise HTTPException(422, "The starting balance date must be today or earlier.")
    if payload.last_four and (db.scalar(select(AccountDetails.account_id).where(AccountDetails.last_four == payload.last_four)) or db.scalar(select(DebitCard.id).where(DebitCard.last_four == payload.last_four))):
        raise HTTPException(409, "This suffix is already registered. Use the existing account.")
    row = Account(name=payload.name.strip(), opening_balance_cents=cents(payload.opening_balance), mode="registered")
    if not row.name:
        raise HTTPException(422, "Account name is required.")
    db.add(row)
    db.flush()
    db.add(AccountDetails(account_id=row.id, account_type=payload.account_type, last_four=payload.last_four, balance_date=payload.balance_date))
    db.commit()
    return account_rows(db)


@router.put("/gmail/accounts/{account_id}")
def edit_account(account_id: int, payload: RegisteredAccountIn, db: Session = Depends(get_personal_db)):
    row, details = db.get(Account, account_id), db.get(AccountDetails, account_id)
    if not row or not details:
        raise HTTPException(404, "Registered account not found.")
    if payload.account_type != details.account_type and (db.scalar(select(Transaction.id).where(Transaction.account_id == account_id)) or db.scalar(select(DebitCard.id).where(DebitCard.account_id == account_id))):
        raise HTTPException(409, "Account type cannot change after transactions or linked debit cards exist.")
    if payload.balance_date > config.today():
        raise HTTPException(422, "The starting balance date must be today or earlier.")
    if payload.last_four and (db.scalar(select(AccountDetails.account_id).where(AccountDetails.last_four == payload.last_four, AccountDetails.account_id != account_id)) or db.scalar(select(DebitCard.id).where(DebitCard.last_four == payload.last_four))):
        raise HTTPException(409, "That suffix belongs to another account.")
    if db.scalar(select(Transaction.id).where(Transaction.account_id == account_id, Transaction.date < payload.balance_date)):
        raise HTTPException(409, "Starting balance date cannot exclude transactions already recorded.")
    row.name, row.opening_balance_cents = payload.name.strip(), cents(payload.opening_balance)
    details.account_type, details.last_four, details.balance_date = payload.account_type, payload.last_four, payload.balance_date
    db.commit()
    return account_rows(db)


@router.get("/gmail/status")
def status(request: Request):
    service = manager(request)
    configured = service.configured() if hosted(request) else configuration()
    connection_error = None
    with service.lock:
        stored = None
        if configured:
            try:
                service.ready()
                stored = service.vault.load()
            except HTTPException as exc:
                connection_error = exc.detail
    return {"configured": configured, "connected": bool(stored), "email": stored["email"] if stored else None,
            "tokens_present": bool(stored) if hosted(request) else (config.GMAIL_TOKEN_DIR / "credentials.enc").exists(), "connection_error": connection_error,
            "scope": config.GMAIL_SCOPE, "redirect_uri": service.settings.redirect_uri if hosted(request) else config.GMAIL_REDIRECT_URI,
            "frontend_url": service.settings.origin if hosted(request) else config.GMAIL_FRONTEND_URL}


@router.post("/gmail/connect")
def connect(request: Request, response: Response):
    url, cookie = manager(request).begin()
    response.set_cookie(STATE_COOKIE, cookie, path="/api/gmail/callback", max_age=600, httponly=True, secure=hosted(request), samesite="lax")
    return {"authorization_url": url}


@router.get("/gmail/callback")
def callback(request: Request, code: str | None = None, state: str | None = None, error: str | None = None):
    result = manager(request).finish(state, request.cookies.get(STATE_COOKIE), code, error)
    frontend = request.app.state.hosted_settings.origin if hosted(request) else config.GMAIL_FRONTEND_URL.rstrip("/")
    response = RedirectResponse(frontend + "/?gmail=" + result + "#settings", status_code=303)
    response.delete_cookie(STATE_COOKIE, path="/api/gmail/callback")
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Cache-Control"] = "no-store"
    return response


@router.post("/gmail/disconnect")
def disconnect(request: Request):
    revoked = manager(request).disconnect()
    return {"connected": False, "google_revoked": revoked,
            "message": "Local tokens removed. Confirmed records remain." + (" Remove Moniq in your Google Account permissions to finish remote revocation." if not revoked else "")}


def serialize_item(row):
    return {"id": row.id, "subject": row.subject, "sender": row.sender, "event_type": row.event_type,
            "merchant": row.merchant, "amount": row.amount_cents / 100 if row.amount_cents is not None else None,
            "date": row.date.isoformat(), "last_four": row.last_four, "category": row.category, "confidence": row.confidence,
            "reasons": json.loads(row.reasons), "account_id": row.account_id, "status": row.status, "transaction_id": row.transaction_id}


@router.get("/gmail/items")
def review_queue(db: Session = Depends(get_personal_db)):
    return [serialize_item(row) for row in db.scalars(select(GmailItem).order_by(GmailItem.id.desc()).limit(500))]


def match_account(db, values):
    registered = list(db.scalars(select(AccountDetails)))
    if values["last_four"]:
        card_accounts = set(db.scalars(select(DebitCard.account_id).where(DebitCard.last_four == values["last_four"])))
        matches = [r for r in registered if r.last_four == values["last_four"] or r.account_id in card_accounts]
    else:
        matches = []
    if len(matches) == 1:
        if values["event_type"] == "income" and matches[0].account_type == "credit":
            values["reasons"].append("Income cannot be assigned automatically to a credit account.")
            return None
        return matches[0].account_id
    values["reasons"].append("No unique registered account match. Select an account before confirming.")
    return None


@router.post("/gmail/sync")
def sync(request: Request, db: Session = Depends(get_personal_db)):
    if not hosted(request) and request.cookies.get("moniq_workspace") == "scenario":
        raise HTTPException(403, "Real Gmail synchronization is unavailable in the isolated scenario.")
    service = manager(request)
    with service.lock:
        stored = service.authorized()
        token, mailbox = stored["token"], stored["mailbox_key"]
        imported, already_seen, visited, pages, cursor = 0, 0, 0, 0, stored.get("sync_cursor")
        buffered = []
        while pages < 5 and visited < 250:
            query = {"maxResults": 50, "includeSpamTrash": "false",
                     "q": 'newer_than:30d {purchase charged payment paid receipt "direct deposit" deposit paycheck payroll salary refund subscription bill renewal membership}'}
            if cursor:
                query["pageToken"] = cursor
            page = service.api(token, "/messages", query)
            pages += 1
            for item in page.get("messages", [])[:50]:
                identifier = item.get("id", "")
                if not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", identifier):
                    continue
                visited += 1
                if db.scalar(select(GmailItem.id).where(GmailItem.mailbox_key == mailbox, GmailItem.message_id == identifier)) or identifier in {x[0] for x in buffered}:
                    already_seen += 1
                    continue
                message = service.api(token, "/messages/" + identifier, {"format": "full"})
                values = parse_financial_email(message, personal_classifier(request))
                if values:
                    values["account_id"] = match_account(db, values)
                    details = db.get(AccountDetails, values["account_id"]) if values["account_id"] else None
                    if details and values["date"] < details.balance_date:
                        values["reasons"].append("Before the account's starting-balance date; do not count this again.")
                    from .smartapprove import authentication
                    from .gmail_parser import email_text
                    evidence = authentication(message)
                    text = values["subject"] + "\n" + email_text(message)
                    evidence["date_explicit"] = len(set(re.findall(r"\b(?:\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{4})\b", email_text(message)))) == 1
                    evidence["posted"] = bool(re.search(r"\b(?:posted|completed|confirmed|credited|deposited)\b", text, re.I)) and not bool(re.search(r"\b(?:pending|authorization|order|receipt|pay ?stub|transfer|expected|scheduled|will be)\b", text, re.I))
                    buffered.append((identifier, values, evidence))
            cursor = page.get("nextPageToken")
            if not cursor:
                break
        auto_approved = queued = duplicates = 0
        from .circles import ledger_lock
        from .smartapprove import try_approve
        ledger_lock.acquire()
        try:
            for identifier, values, evidence in buffered:
                values["reasons"] = json.dumps(values["reasons"])
                row = GmailItem(mailbox_key=mailbox, message_id=identifier, **values)
                db.add(row)
                db.flush()
                db.add(GmailEvidence(item_id=row.id, details=json.dumps(evidence)))
                auto_approved += int(try_approve(db, row, evidence, personal_classifier(request)))
                queued += int(row.status == "review")
                duplicates += int(row.status == "duplicate")
                imported += 1
            db.commit()
        finally:
            ledger_lock.release()
        stored["sync_cursor"] = cursor
        service.vault.save(stored)
        return {"queued": queued, "auto_approved": auto_approved, "duplicates": duplicates, "already_seen": already_seen, "messages_checked": visited,
                "more_available": bool(cursor), "message": f"{auto_approved} auto-approved; {queued} queued for manual review. Gmail balances are estimates."}


class ConfirmIn(TransactionIn):
    posted_confirmed: bool = False


@router.post("/gmail/items/{item_id}/confirm")
def confirm(item_id: int, payload: ConfirmIn, request: Request, db: Session = Depends(get_personal_db)):
    with manager(request).lock:
        return confirm_item(item_id, payload, db, personal_classifier(request))


def confirm_item(item_id, payload, db, classifier):
    from .circles import ledger_lock
    with ledger_lock:
        row = db.get(GmailItem, item_id)
        if not row:
            raise HTTPException(404, "Email review item not found.")
        if row.status != "review":
            raise HTTPException(409, "This email has already been reviewed.")
        if not payload.posted_confirmed:
            raise HTTPException(422, "Confirm that this is a posted transaction, not a future bill, pending payment or estimate.")
        details = db.get(AccountDetails, payload.account_id)
        if not details:
            raise HTTPException(422, "Choose a registered personal account.")
        if payload.date < details.balance_date or payload.date > config.today():
            raise HTTPException(422, "Use a posted date on or after the starting-balance date and no later than today.")
        if payload.kind == "income" and details.account_type == "credit":
            raise HTTPException(422, "Choose a checking or savings account for a paycheck deposit.")
        if payload.notification_text:
            raise HTTPException(422, "Only extracted fields are saved; raw email content is not persisted.")
        try:
            transaction = add_transaction(db, payload, classifier, "gmail")
        except IntegrityError as exc:
            db.rollback()
            raise HTTPException(409, "A concurrent transaction was saved. Review and retry; duplicate amounts are not added twice.") from exc
        if transaction is None:
            row.status = "duplicate"
            db.commit()
            return {"status": "duplicate", "message": "The same account, date, merchant and signed amount is already recorded."}
        row.status, row.account_id, row.transaction_id = "confirmed", payload.account_id, transaction.id
        from .smartapprove import log
        log(db, "manual-confirmed", transaction=transaction, item_id=row.id)
        db.commit()
        return {"status": "confirmed", "transaction": serialize_transaction(transaction)}


@router.post("/gmail/items/{item_id}/dismiss")
def dismiss(item_id: int, request: Request, db: Session = Depends(get_personal_db)):
    with manager(request).lock:
        row = db.get(GmailItem, item_id)
        if not row:
            raise HTTPException(404, "Email review item not found.")
        if row.status != "review":
            raise HTTPException(409, "This email has already been reviewed.")
        row.status = "dismissed"
        db.commit()
        return {"status": row.status}
