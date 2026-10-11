"""Explicit synthetic walkthrough in a separate local database or visitor-owned demo."""

import json
import base64
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import delete, select
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field, field_validator

from . import config
from .circles import ledger_lock
from .database import get_db, scenario_engine
from .gmail_routes import ConfirmIn, account_rows, confirm_item, match_account, require_local, serialize_item
from .gmail_parser import parse_financial_email
from .models import Account, AccountDetails, Base, Budget, GmailItem, Goal, Profile, TrustedSender
from .smartapprove import try_approve
from .workspace import workspace_classifier
from .schemas import cents

router = APIRouter(prefix="/api/upgrade-demo")


class StartIn(BaseModel):
    starting_balance: Decimal = Field(default=Decimal("100.00"), ge=0, le=1_000_000)

    @field_validator("starting_balance")
    @classmethod
    def exact_balance(cls, value):
        cents(value)
        return value


def seed_scenario(db, opening=10000):
    for table in reversed(Base.metadata.sorted_tables):
        db.execute(delete(table))
    db.add(Profile(id=1, name="Alex Morgan", university="Georgia State University", allowance_cents=0))
    db.add(Account(id=1, name="Synthetic checking", opening_balance_cents=opening, mode="scenario"))
    db.flush()
    db.add(
        AccountDetails(account_id=1, account_type="checking", last_four="1234", balance_date=config.today())
    )
    db.add(Budget(category="food", period="monthly", limit_cents=10000))
    db.add(Goal(id=1, name="Emergency fund", target_cents=150000, saved_cents=0))
    db.add(
        TrustedSender(
            sender="alerts@bank.example.test",
            match_type="address",
            institution="Synthetic Bank",
            account_id=1,
            events='["purchase"]',
            enabled=True,
            suspended=False,
            removed=False,
            transaction_cap=5000,
            daily_cap=10000,
        )
    )
    db.commit()


@router.post("/start")
def start(
    request: Request, response: Response, payload: StartIn | None = None, db: Session = Depends(get_db)
):
    opening = cents((payload or StartIn()).starting_balance)
    with ledger_lock:
        if request.app.state.public_demo:
            seed_scenario(db, opening)  # The middleware holds this visitor's session lock.
        else:
            require_local(request)
            with Session(scenario_engine(request.app)) as separate:
                seed_scenario(separate, opening)
            response.set_cookie("moniq_workspace", "scenario", httponly=True, samesite="lax", max_age=2592000)
    return {"started": True, "starting_balance": opening / 100, "synthetic": True}


class FixtureIn(BaseModel):
    event: str = Field(pattern="^(paycheck|purchase)$")


@router.post("/financial-alert")
def financial_alert(payload: FixtureIn, request: Request, db: Session = Depends(get_db)):
    with ledger_lock:
        account = db.get(Account, 1)
        if not account or account.mode != "scenario":
            raise HTTPException(409, "Start the isolated synthetic scenario first.")
        identifier = "manual-" + payload.event
        prior = db.scalar(select(GmailItem).where(GmailItem.mailbox_key == "controlled-scenario", GmailItem.message_id == identifier))
        if prior:
            return serialize_item(prior)
        body = (f"Confirmed paycheck deposit of $400.00 from Campus job payroll on {config.today()}. Account ending in 1234." if payload.event == "paycheck" else f"Posted purchase of $15.00 at Chick-fil-A on {config.today()}. Card ending in 1234.")
        message = {"internalDate": "0", "payload": {"mimeType": "text/plain", "headers": [{"name": "Subject", "value": "Simulated " + payload.event + " notification"}, {"name": "From", "value": "Synthetic Bank <alerts@bank.example.test>"}], "body": {"data": base64.urlsafe_b64encode(body.encode()).decode()}}}
        values = parse_financial_email(message, workspace_classifier(request))
        if not values:
            raise HTTPException(500, "Synthetic fixture did not produce a financial event.")
        values["account_id"] = match_account(db, values)
        values["reasons"] = json.dumps(values["reasons"])
        row = GmailItem(mailbox_key="controlled-scenario", message_id=identifier, **values)
        db.add(row)
        db.commit()
        return serialize_item(row)


approvals_router = APIRouter(prefix="/api/approvals")


def active_approvals(request, db):
    if not request.app.state.public_demo and request.cookies.get("moniq_workspace") == "personal":
        require_local(request)
        return list(db.scalars(select(GmailItem).order_by(GmailItem.id.desc())))
    account = db.get(Account, 1)
    if account and account.mode == "scenario":
        return list(db.scalars(select(GmailItem).where(GmailItem.mailbox_key == "controlled-scenario").order_by(GmailItem.id.desc())))
    return []


@approvals_router.get("")
def approvals(request: Request, db: Session = Depends(get_db)):
    account = db.get(Account, 1)
    return {"items": [serialize_item(i) for i in active_approvals(request, db) if i.status == "review"], "accounts": account_rows(db) if active_approvals(request, db) else [], "synthetic_scenario": bool(account and account.mode == "scenario")}


@approvals_router.post("/{item_id}/confirm")
def confirm_active(item_id: int, payload: ConfirmIn, request: Request, db: Session = Depends(get_db)):
    item = next((i for i in active_approvals(request, db) if i.id == item_id), None)
    if not item:
        raise HTTPException(404, "Review item is not in this workspace.")
    if request.app.state.public_demo:
        from .demo_policy import require_sample
        require_sample(payload.description == item.merchant and payload.merchant == item.merchant and cents(payload.amount) == item.amount_cents and payload.date == item.date and payload.account_id == item.account_id and payload.kind == ("income" if item.event_type == "income" else "expense") and payload.category and payload.category.value == item.category)
    return confirm_item(item_id, payload, db, workspace_classifier(request))


@approvals_router.post("/{item_id}/dismiss")
def dismiss_active(item_id: int, request: Request, db: Session = Depends(get_db)):
    with ledger_lock:
        item = next((i for i in active_approvals(request, db) if i.id == item_id), None)
        if not item:
            raise HTTPException(404, "Review item is not in this workspace.")
        if item.status != "review":
            raise HTTPException(409, "Item is already reviewed.")
        item.status = "dismissed"
        db.commit()
        return {"status": item.status}


@router.post("/alert")
def alert(request: Request, db: Session = Depends(get_db)):
    with ledger_lock:
        account = db.get(Account, 1)
        if not account or account.mode != "scenario":
            raise HTTPException(409, "Start the isolated upgrade walkthrough first.")
        if db.scalar(select(GmailItem.id).where(GmailItem.mailbox_key == "controlled-scenario", GmailItem.message_id == "dinner-40")):
            raise HTTPException(
                409, "Synthetic alert already processed. The same purchase is never added twice."
            )
        item = GmailItem(
            mailbox_key="controlled-scenario",
            message_id="dinner-40",
            subject="Controlled posted purchase",
            sender="alerts@bank.example.test",
            event_type="purchase",
            merchant="Chick-fil-A",
            amount_cents=4000,
            date=config.today(),
            last_four="1234",
            category="food",
            confidence=1,
            reasons="[]",
            account_id=1,
        )
        db.add(item)
        db.flush()
        evidence = {
            "sender": "alerts@bank.example.test",
            "aligned": True,
            "reasons": [],
            "synthetic": True,
            "posted": True,
            "date_explicit": True,
            "provider": "server-owned-test-fixture",
        }
        approved = try_approve(db, item, evidence, workspace_classifier(request), controlled=True)
        db.commit()
        from .finance import balance_cents

        return {
            "auto_approved": approved,
            "transaction_id": item.transaction_id,
            "estimated_balance": balance_cents(db) / 100,
            "synthetic": True,
            "reasons": json.loads(item.reasons),
        }
