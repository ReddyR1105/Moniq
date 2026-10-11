"""Account aliases and atomic internal movements; no bank connection or money transfer."""
import hashlib
from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import config
from .access import demo, hosted, private
from .circles import audit, ledger_lock
from .database import get_db
from .gmail_routes import RegisteredAccountIn, account_rows, edit_account, register_account, require_local
from .models import Account, AccountDetails, AccountTransfer, DebitCard, Transaction
from .schemas import cents

router = APIRouter(prefix="/api/accounts")


def owner_workspace(request: Request, db: Session = Depends(get_db)):
    if demo(request):
        raise HTTPException(403, "Personal account management is disabled in public demo sessions.")
    require_local(request)
    if not (private(request) if hosted(request) else request.cookies.get("moniq_workspace") in {"personal", "scenario"}):
        raise HTTPException(409, "Open your personal workspace or isolated scenario first.")
    return db


Db = Depends(owner_workspace)


@router.get("")
def accounts(db: Session = Db):
    return account_rows(db)


@router.post("", status_code=201)
def create(payload: RegisteredAccountIn, db: Session = Db):
    with ledger_lock:
        if payload.last_four and db.scalar(select(DebitCard.id).where(DebitCard.last_four == payload.last_four)):
            raise HTTPException(409, "This suffix is already linked to a debit card.")
        return register_account(payload, db)


@router.put("/{account_id}")
def update(account_id: int, payload: RegisteredAccountIn, db: Session = Db):
    with ledger_lock:
        if payload.last_four and db.scalar(select(DebitCard.id).where(DebitCard.last_four == payload.last_four)):
            raise HTTPException(409, "This suffix is already linked to a debit card.")
        return edit_account(account_id, payload, db)


class DebitIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    last_four: str = Field(pattern=r"^\d{4}$")

    @field_validator("name")
    @classmethod
    def nonblank(cls, value):
        if not value.strip():
            raise ValueError("Card nickname is required.")
        return value.strip()


@router.post("/{account_id}/debit-cards", status_code=201)
def debit_card(account_id: int, payload: DebitIn, db: Session = Db):
    with ledger_lock:
        details = db.get(AccountDetails, account_id)
        if not details or details.account_type != "checking":
            raise HTTPException(422, "Link a debit card to a registered checking account.")
        if db.scalar(select(AccountDetails.account_id).where(AccountDetails.last_four == payload.last_four)) or db.scalar(select(DebitCard.id).where(DebitCard.last_four == payload.last_four)):
            raise HTTPException(409, "That suffix is already registered.")
        db.add(DebitCard(account_id=account_id, **payload.model_dump()))
        audit(db, "debit-card-linked", account_id=account_id, last_four=payload.last_four)
        db.commit()
        return account_rows(db)


class MoneyIn(BaseModel):
    amount: Decimal = Field(gt=0, le=1_000_000)
    date: date
    request_key: str = Field(min_length=8, max_length=80, pattern=r"^[A-Za-z0-9_-]+$")

    @field_validator("amount")
    @classmethod
    def precise(cls, value):
        cents(value)
        return value


class TransferIn(MoneyIn):
    from_account: int = Field(ge=1)
    to_account: int = Field(ge=1)


def posted_account(db, account_id, day):
    account, details = db.get(Account, account_id), db.get(AccountDetails, account_id)
    if not account or not details or not details.balance_date <= day <= config.today():
        raise HTTPException(422, "Choose a registered account and a posted date within its balance history.")
    return account, details


def movement(db, account_id, day, value, key, kind, description):
    row = Transaction(account_id=account_id, date=day, description=description, merchant=description,
                      amount_cents=value, kind=kind, category="miscellaneous", source="account-ledger",
                      fingerprint=hashlib.sha256(key.encode()).hexdigest())
    db.add(row)
    db.flush()
    return row


@router.post("/transfers")
def transfer(payload: TransferIn, db: Session = Db):
    with ledger_lock:
        if payload.from_account == payload.to_account:
            raise HTTPException(422, "Choose two different accounts.")
        _, source_details = posted_account(db, payload.from_account, payload.date)
        posted_account(db, payload.to_account, payload.date)
        if source_details.account_type == "credit":
            raise HTTPException(422, "Credit accounts cannot fund a cash transfer.")
        existing = db.scalar(select(AccountTransfer).where(AccountTransfer.request_key == payload.request_key))
        amount = cents(payload.amount)
        if existing:
            debit, credit = db.get(Transaction, existing.debit_id), db.get(Transaction, existing.credit_id)
            if (debit.account_id, credit.account_id, debit.date, -debit.amount_cents) != (payload.from_account, payload.to_account, payload.date, amount):
                raise HTTPException(409, "This request key belongs to a different transfer.")
            return account_rows(db)
        debit = movement(db, payload.from_account, payload.date, -amount, payload.request_key + "-out", "transfer", "Internal transfer / card payment")
        credit = movement(db, payload.to_account, payload.date, amount, payload.request_key + "-in", "transfer", "Internal transfer / card payment")
        db.add(AccountTransfer(request_key=payload.request_key, debit_id=debit.id, credit_id=credit.id))
        audit(db, "internal-transfer", from_account=payload.from_account, to_account=payload.to_account, amount_cents=amount)
        db.commit()
        return account_rows(db)


class ReconcileIn(BaseModel):
    observed_balance: Decimal = Field(ge=-1_000_000, le=1_000_000)
    confirmed: bool = False

    @field_validator("observed_balance")
    @classmethod
    def precise(cls, value):
        cents(value)
        return value


@router.post("/{account_id}/reconcile")
def reconcile(account_id: int, payload: ReconcileIn, db: Session = Db):
    if not payload.confirmed:
        raise HTTPException(422, "Confirm the observed balance before reconciling.")
    with ledger_lock:
        account, _ = posted_account(db, account_id, config.today())
        before = account.opening_balance_cents + sum(t.amount_cents for t in db.scalars(select(Transaction).where(Transaction.account_id == account_id, Transaction.date <= config.today())))
        delta = cents(payload.observed_balance) - before
        if delta:
            import uuid
            movement(db, account_id, config.today(), delta, str(uuid.uuid4()), "adjustment", "Manual balance reconciliation")
            audit(db, "balance-reconciled", account_id=account_id, previous_cents=before, observed_cents=cents(payload.observed_balance))
            db.commit()
        return account_rows(db)
