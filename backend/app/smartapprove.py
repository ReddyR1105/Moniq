"""Optional, fail-closed email approval policy; no visible-From-only trust."""

import json
import re
from datetime import timedelta
from decimal import Decimal
from email.utils import getaddresses
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import config
from .access import demo, hosted
from .circles import guard_transaction, ledger_lock
from .database import get_db, get_personal_db
from .gmail_routes import require_local
from .models import AccountDetails, ApprovalAudit, GmailItem, Transaction, TrustedSender
from .schemas import TransactionIn, cents
from .transactions import add_transaction

router = APIRouter(prefix="/api/smartapprove")


def smart_db(request: Request):
    if hosted(request):
        yield from get_db(request)
        return
    # Public rules are synthetic and session-owned; never reach private Gmail storage.
    if (
        request.app.state.public_demo
        or request.cookies.get("moniq_workspace") == "scenario"
        or (
            request.query_params.get("workspace") == "active"
            and request.method == "GET"
            and request.url.path == "/api/smartapprove/summary"
            and request.cookies.get("moniq_workspace") != "personal"
        )
    ):
        yield from get_db(request)
    else:
        require_local(request)
        yield from get_personal_db(request)


class RuleIn(BaseModel):
    sender: str = Field(min_length=3, max_length=200)
    match_type: Literal["address", "domain"] = "address"
    institution: str = Field(min_length=1, max_length=80)
    account_id: int = Field(ge=1)
    events: list[Literal["purchase", "income", "refund", "subscription"]] = Field(min_length=1, max_length=4)
    enabled: bool = False
    suspended: bool = False
    transaction_limit: str = "100.00"
    daily_limit: str = "500.00"

    @field_validator("transaction_limit", "daily_limit")
    @classmethod
    def valid_limit(cls, value):
        if cents(value) <= 0:
            raise ValueError("Limits must be positive exact amounts.")
        return value


def log(db, action, rule_id=None, transaction=None, **details):
    db.add(
        ApprovalAudit(
            action=action,
            day=config.today(),
            rule_id=rule_id,
            transaction_id=transaction.id if transaction else None,
            amount_cents=abs(transaction.amount_cents) if transaction else 0,
            details=json.dumps(details, default=str),
        )
    )


def rule_data(r):
    return {
        "id": r.id,
        "sender": r.sender,
        "match_type": r.match_type,
        "institution": r.institution,
        "account_id": r.account_id,
        "events": json.loads(r.events),
        "enabled": r.enabled,
        "suspended": r.suspended,
        "transaction_limit": f"{r.transaction_cap // 100}.{r.transaction_cap % 100:02d}",
        "daily_limit": f"{r.daily_cap // 100}.{r.daily_cap % 100:02d}",
    }


@router.get("/rules")
def rules(db: Session = Depends(smart_db)):
    return [
        rule_data(r)
        for r in db.scalars(
            select(TrustedSender).where(TrustedSender.removed.is_(False)).order_by(TrustedSender.id)
        )
    ]


def store_rule(db, payload, request, existing=None):
    sender = payload.sender.strip().lower()
    domain = sender.rsplit("@", 1)[-1]
    if (
        not re.fullmatch(r"[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?\.[a-z]{2,}", domain)
        or ".." in domain
        or (
            payload.match_type == "address"
            and not re.fullmatch(r"[a-z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-z0-9.-]+", sender)
        )
        or (payload.match_type == "domain" and "@" in sender)
    ):
        raise HTTPException(422, "Use an exact email address or domain, without wildcard or display name.")
    if demo(request) and (
        domain != "bank.example.test" or payload.institution != "Synthetic Bank"
    ):
        raise HTTPException(403, "Public sender settings accept Synthetic Bank at bank.example.test only.")
    if not db.get(AccountDetails, payload.account_id):
        raise HTTPException(422, "Choose a registered account with an account suffix.")
    duplicate = db.scalar(
        select(TrustedSender).where(
            TrustedSender.sender == sender,
            TrustedSender.match_type == payload.match_type,
            TrustedSender.removed.is_(False),
        )
    )
    if duplicate and (not existing or duplicate.id != existing.id):
        raise HTTPException(409, "Edit the existing sender rule.")
    r = existing or TrustedSender()
    before = rule_data(r) if existing else None
    for key, value in {
        "sender": sender,
        "match_type": payload.match_type,
        "institution": payload.institution.strip(),
        "account_id": payload.account_id,
        "events": json.dumps(sorted(set(payload.events))),
        "enabled": payload.enabled,
        "suspended": payload.suspended,
        "transaction_cap": cents(payload.transaction_limit),
        "daily_cap": cents(payload.daily_limit),
    }.items():
        setattr(r, key, value)
    db.add(r)
    db.flush()
    log(db, "rule-updated" if existing else "rule-created", r.id, before=before, after=rule_data(r))
    db.commit()
    return rule_data(r)


@router.post("/rules", status_code=201)
def create_rule(payload: RuleIn, request: Request, db: Session = Depends(smart_db)):
    with ledger_lock:
        return store_rule(db, payload, request)


@router.put("/rules/{rule_id}")
def edit_rule(rule_id: int, payload: RuleIn, request: Request, db: Session = Depends(smart_db)):
    with ledger_lock:
        r = db.get(TrustedSender, rule_id)
        if not r or r.removed:
            raise HTTPException(404, "Sender rule not found.")
        return store_rule(db, payload, request, r)


@router.delete("/rules/{rule_id}")
def remove_rule(rule_id: int, db: Session = Depends(smart_db)):
    with ledger_lock:
        r = db.get(TrustedSender, rule_id)
        if not r or r.removed:
            raise HTTPException(404, "Sender rule not found.")
        r.removed, r.enabled = True, False
        log(db, "rule-removed", r.id, sender=r.sender)
        db.commit()
        return {"removed": True, "audit_preserved": True}


def authentication(message):
    """Require one Google receiving boundary, three aligned passes, no ARC forwarding.

    This evaluates provider-delivered headers, not independent DNS/signature proofs.
    Imported/raw messages and contradictory chains remain manual review.
    """
    headers = [
        (str(h.get("name", "")).lower(), str(h.get("value", "")))
        for h in message.get("payload", {}).get("headers", [])
    ]
    reasons = []
    froms = [(i, v) for i, (k, v) in enumerate(headers) if k == "from"]
    addresses = getaddresses([v for _, v in froms])
    sender = addresses[0][1].lower() if len(froms) == 1 and len(addresses) == 1 else ""
    if not re.fullmatch(r"[^\s<>@]+@[a-z0-9.-]+", sender):
        reasons.append("Sender address is missing or ambiguous.")
    domain = sender.rsplit("@", 1)[-1]
    ars = [(i, v) for i, (k, v) in enumerate(headers) if k == "authentication-results"]
    received = [
        (i, v)
        for i, (k, v) in enumerate(headers)
        if k == "received" and re.search(r"\bby\s+mx\.google\.com(?=\s|;|$)", v, re.I)
    ]
    google = [(i, v) for i, v in ars if re.match(r"\s*mx\.google\.com\s*;", v, re.I)]
    if (
        len(google) != 1
        or len(received) != 1
        or not froms
        or not (received[0][0] < google[0][0] < froms[0][0])
    ):
        reasons.append("Uncertain Google receiving authentication boundary.")
    ar = google[0][1].lower() if len(google) == 1 else ""
    for method, prop in (("spf", "smtp.mailfrom"), ("dkim", "header.d"), ("dmarc", "header.from")):
        clauses = [s for s in ar.split(";") if re.match(r"\s*" + method + r"=", s)]
        if len(clauses) != 1 or not re.match(r"\s*" + method + r"=pass\b", clauses[0]):
            reasons.append(f"{method.upper()} is missing, contradictory or failed.")
            continue
        match = re.search(re.escape(prop) + r'\s*=\s*"?([^\s;"()]+)', clauses[0])
        aligned = match.group(1).rsplit("@", 1)[-1].strip("<>") if match else ""
        if aligned != domain:
            reasons.append(f"{method.upper()} does not exactly align with the sender domain.")
    if any(
        re.search(r"\b(?:spf|dkim|dmarc)=(?:fail|softfail|neutral|none|temperror|permerror)\b", v, re.I)
        for _, v in ars
    ):
        reasons.append("Contradictory authentication results.")
    if any(k.startswith("arc-") or k in {"resent-from", "resent-sender"} for k, _ in headers):
        reasons.append("Forwarded or ARC evidence requires manual review.")
    if "INBOX" not in message.get("labelIds", []):
        reasons.append("Inbox delivery evidence is missing.")
    if set(message.get("labelIds", [])) & {"SENT", "DRAFT", "SPAM", "TRASH"}:
        reasons.append("Non-inbox provenance requires manual review.")
    if domain.endswith((".test", ".example", ".invalid", ".localhost")) or domain in {
        "example.com",
        "example.org",
        "example.net",
    }:
        reasons.append("Synthetic senders cannot approve real Gmail transactions.")
    return {
        "sender": sender,
        "aligned": not reasons,
        "reasons": reasons,
        "provider": "gmail",
        "synthetic": False,
    }


def try_approve(db, item, evidence, classifier, controlled=False):
    """Only server-owned controlled scenarios can use synthetic evidence."""
    sender = evidence.get("sender", "")
    candidates = [
        r
        for r in db.scalars(
            select(TrustedSender).where(
                TrustedSender.enabled.is_(True),
                TrustedSender.suspended.is_(False),
                TrustedSender.removed.is_(False),
            )
        )
        if sender == r.sender or (r.match_type == "domain" and sender.rsplit("@", 1)[-1] == r.sender)
    ]
    reasons = list(json.loads(item.reasons))
    reasons.extend(evidence.get("reasons", []))
    if not evidence.get("aligned") or (evidence.get("synthetic") and not controlled):
        reasons.append("Authentication evidence is insufficient for automatic approval.")
    if len(candidates) != 1:
        reasons.append("No single active trusted sender rule matches exactly.")
    rule = candidates[0] if len(candidates) == 1 else None
    # Preserve the original imported event identity even after an edit or reversal.
    previous = db.scalar(
        select(GmailItem.id).where(
            GmailItem.id != item.id,
            GmailItem.account_id == item.account_id,
            GmailItem.date == item.date,
            GmailItem.amount_cents == item.amount_cents,
            GmailItem.merchant == item.merchant,
            GmailItem.event_type == item.event_type,
            GmailItem.status.in_(["confirmed", "auto-approved", "reversed"]),
        )
    )
    if previous:
        item.status = "duplicate"
        return False
    nearby = db.scalar(
        select(GmailItem.id).where(
            GmailItem.id != item.id,
            GmailItem.account_id == item.account_id,
            GmailItem.date >= item.date - timedelta(days=3),
            GmailItem.date <= item.date + timedelta(days=3),
            GmailItem.amount_cents == item.amount_cents,
            GmailItem.merchant == item.merchant,
            GmailItem.event_type == item.event_type,
            GmailItem.status.in_(["confirmed", "auto-approved", "reversed"]),
        )
    )
    if nearby:
        reasons.append(
            "Possible receipt/authorization/posted duplicate with a different date; reconcile manually."
        )
    details = db.get(AccountDetails, item.account_id) if item.account_id else None
    if (
        not details
        or not item.last_four
        or details.last_four != item.last_four
        or (rule and rule.account_id != item.account_id)
    ):
        reasons.append("Account match is missing or outside the sender restriction.")
    if details and (
        item.date < details.balance_date
        or item.date > config.today()
        or (item.event_type == "income" and details.account_type == "credit")
    ):
        reasons.append("Posted date or account type is invalid.")
    if (
        item.amount_cents is None
        or item.amount_cents <= 0
        or item.event_type not in {"purchase", "income", "refund", "subscription"}
    ):
        reasons.append("This is not an unambiguous posted financial event.")
    if not evidence.get("posted", False):
        reasons.append("Explicit posted-event evidence is required.")
    if not evidence.get("date_explicit", False):
        reasons.append("An explicit transaction date is required for automatic approval.")
    if rule:
        if item.event_type not in json.loads(rule.events):
            reasons.append("Event type is not permitted by this sender rule.")
        used = sum(
            a.amount_cents
            for a in db.scalars(
                select(ApprovalAudit).where(
                    ApprovalAudit.rule_id == rule.id,
                    ApprovalAudit.action == "auto-approved",
                    ApprovalAudit.day == config.today(),
                )
            )
        )
        if item.amount_cents and (
            item.amount_cents > rule.transaction_cap or used + item.amount_cents > rule.daily_cap
        ):
            reasons.append("Transaction or daily approval limit exceeded.")
    if reasons:
        item.reasons = json.dumps(list(dict.fromkeys(reasons)))
        return False
    kind = "income" if item.event_type == "income" else "refund" if item.event_type == "refund" else "expense"
    payload = TransactionIn(
        date=item.date,
        description=item.merchant,
        merchant=item.merchant,
        amount=Decimal(item.amount_cents) / Decimal(100),
        kind=kind,
        category=item.category,
        account_id=item.account_id,
    )
    tx = add_transaction(db, payload, classifier, "gmail-auto")
    if not tx:
        item.status = "duplicate"
        return False
    item.status, item.transaction_id = "auto-approved", tx.id
    log(
        db,
        "auto-approved",
        rule.id,
        tx,
        item_id=item.id,
        authentication=evidence,
        original={"amount_cents": tx.amount_cents, "kind": tx.kind, "category": tx.category},
        controlled=controlled,
    )
    db.flush()
    return True


@router.get("/summary")
def summary(db: Session = Depends(smart_db)):
    items = list(db.scalars(select(GmailItem)))
    audit = list(db.scalars(select(ApprovalAudit).order_by(ApprovalAudit.id.desc()).limit(50)))
    return {
        "pending": sum(i.status == "review" for i in items),
        "requiring_review": sum(i.status == "review" and bool(json.loads(i.reasons)) for i in items),
        "auto_approved": sum(i.status == "auto-approved" for i in items),
        "active_senders": sum(
            r.enabled and not r.suspended
            for r in db.scalars(select(TrustedSender).where(TrustedSender.removed.is_(False)))
        ),
        "history": [
            {
                "id": a.id,
                "action": a.action,
                "date": a.day.isoformat(),
                "transaction_id": a.transaction_id,
                "rule_id": a.rule_id,
                "amount_cents": a.amount_cents,
                "details": json.loads(a.details),
            }
            for a in audit
        ],
        "estimate": True,
    }


def auto_record(db, tx_id):
    return db.scalar(
        select(ApprovalAudit).where(
            ApprovalAudit.transaction_id == tx_id, ApprovalAudit.action == "auto-approved"
        )
    )


def record_correction(db, row, before):
    if auto_record(db, row.id):
        log(
            db,
            "corrected",
            transaction=row,
            before=before,
            after={
                "amount_cents": row.amount_cents,
                "kind": row.kind,
                "category": row.category,
                "account_id": row.account_id,
                "date": row.date,
            },
        )


@router.post("/transactions/{tx_id}/reverse")
def reverse(tx_id: int, db: Session = Depends(smart_db)):
    import hashlib

    with ledger_lock:
        tx = db.get(Transaction, tx_id)
        if not tx or not auto_record(db, tx_id):
            raise HTTPException(404, "Automatically approved transaction not found.")
        guard_transaction(db, tx_id)
        if db.scalar(
            select(ApprovalAudit.id).where(
                ApprovalAudit.transaction_id == tx_id, ApprovalAudit.action == "reversed"
            )
        ):
            raise HTTPException(409, "Already reversed; a second adjustment is blocked.")
        adjustment = Transaction(
            account_id=tx.account_id,
            date=tx.date,
            description=f"Reversal: {tx.description}",
            merchant=tx.merchant,
            amount_cents=-tx.amount_cents,
            kind="income" if tx.kind == "income" else "refund" if tx.amount_cents < 0 else "expense",
            category=tx.category,
            confidence=None,
            source="smartapprove-adjustment",
            fingerprint=hashlib.sha256(f"smart-reversal:{tx.id}".encode()).hexdigest(),
        )
        db.add(adjustment)
        db.flush()
        log(
            db,
            "reversed",
            transaction=tx,
            adjustment_id=adjustment.id,
            signed_adjustment_cents=adjustment.amount_cents,
        )
        for i in db.scalars(select(GmailItem).where(GmailItem.transaction_id == tx_id)):
            i.status = "reversed"
        db.commit()
        return {"reversed": True, "adjustment_id": adjustment.id}
