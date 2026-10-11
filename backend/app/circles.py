"""Original local expense ledger. Integer cents; allocations never change bank cash."""

import hashlib
import json
from collections import defaultdict
from datetime import date
from decimal import Decimal
from threading import RLock
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from . import config
from .access import demo
from .database import get_db
from .models import (
    Account,
    AccountDetails,
    Circle,
    CircleExpense,
    CircleMember,
    CircleSettlement,
    CircleShare,
    LedgerAudit,
    Transaction,
)
from .schemas import Category, cents

router = APIRouter(prefix="/api/circles")
ledger_lock = RLock()
KINDS = Literal["roommates", "friends", "trips", "dining", "subscriptions", "one-time"]
SAMPLE_NAMES = {"Me", "Alex", "Jordan", "Sam", "Taylor", "Roommate"}
SAMPLE_TITLES = {"Shared dinner", "Shared rent", "Shared subscription", "Campus trip", "Groceries"}


def audit(db, action, **details):
    db.add(LedgerAudit(action=action, day=config.today(), details=json.dumps(details, default=str)))


class CircleIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    kind: KINDS = "friends"
    currency: Literal["USD", "EUR", "GBP", "CAD"] = "USD"
    participants: list[str] = Field(min_length=1, max_length=19)

    @field_validator("name", "participants")
    @classmethod
    def nonblank(cls, value):
        values = value if isinstance(value, list) else [value]
        if any(not v.strip() or len(v.strip()) > 80 for v in values):
            raise ValueError("Names must be nonempty and at most 80 characters.")
        if isinstance(value, list) and (
            len({v.strip().casefold() for v in values}) != len(values)
            or any(v.strip().casefold() == "me" for v in values)
        ):
            raise ValueError("Use distinct participant names; Me is included automatically.")
        return [v.strip() for v in value] if isinstance(value, list) else value.strip()


class ExpenseIn(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    date: date
    amount: Decimal = Field(gt=0, le=1_000_000)
    payer_id: int
    category: Category = Category.food
    method: Literal["equal", "amount", "percentage"] = "equal"
    shares: dict[int, Decimal] = Field(min_length=1, max_length=20)
    transaction_id: int | None = None
    recurring: bool = False

    @field_validator("amount")
    @classmethod
    def exact_amount(cls, value):
        cents(value)
        return value


class MemberIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)


@router.post("/{circle_id}/members", status_code=201)
def add_member(circle_id: int, payload: MemberIn, request: Request, db: Session = Depends(get_db)):
    with ledger_lock:
        circle = find(db, Circle, circle_id)
        name = payload.name.strip()
        members = list(db.scalars(select(CircleMember).where(CircleMember.circle_id == circle_id)))
        if not name or name.casefold() in {m.name.casefold() for m in members} or len(members) >= 20:
            raise HTTPException(422, "Use a distinct name; circles allow at most 20 participants.")
        if demo(request) and name not in SAMPLE_NAMES:
            raise HTTPException(403, "Public participants must use sample names.")
        db.add(CircleMember(circle_id=circle_id, name=name, is_self=False))
        audit(db, "member-added", circle_id=circle_id, name=name)
        db.commit()
        return circle_data(db, circle)


class SettlementIn(BaseModel):
    member_id: int
    amount: Decimal = Field(gt=0, le=1_000_000)
    date: date
    request_key: str = Field(min_length=8, max_length=80, pattern=r"^[A-Za-z0-9_-]+$")
    record_cash: bool = False
    account_id: int | None = None
    transaction_id: int | None = None
    confirmed: bool = False

    @field_validator("amount")
    @classmethod
    def exact_amount(cls, value):
        cents(value)
        return value


def allocate(total, method, values):
    """Largest remainder with stable member-ID ties allocates every single cent."""
    ordered = sorted(values)
    if any(not v.is_finite() or v < 0 for v in values.values()):
        raise HTTPException(422, "Shares must be finite and nonnegative.")
    if method == "amount":
        try:
            result = {m: cents(values[m]) for m in ordered}
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc
        if sum(result.values()) != total:
            raise HTTPException(422, "Custom amounts must equal the complete expense.")
        return result
    if method == "percentage" and sum(values.values()) != Decimal(100):
        raise HTTPException(422, "Percentages must add up to exactly 100.")
    exact = {
        m: Decimal(total) / len(ordered) if method == "equal" else Decimal(total) * values[m] / 100
        for m in ordered
    }
    result = {m: int(v) for m, v in exact.items()}
    remainder = total - sum(result.values())
    for m in sorted(ordered, key=lambda m: (-(exact[m] - result[m]), m))[:remainder]:
        result[m] += 1
    return result


def find(db, model, row_id):
    row = db.get(model, row_id)
    if not row:
        raise HTTPException(404, "Circle record not found in this workspace.")
    return row


def active_expense(db, expense_id):
    row = find(db, CircleExpense, expense_id)
    if not row.active:
        raise HTTPException(409, "This expense was deleted.")
    return row


def debts(db, expense):
    settled = defaultdict(int)
    for s in db.scalars(select(CircleSettlement).where(CircleSettlement.expense_id == expense.id)):
        settled[s.member_id] += s.amount_cents
    return [
        {
            "member_id": s.member_id,
            "share_cents": s.amount_cents,
            "remaining_cents": 0
            if s.member_id == expense.payer_id
            else s.amount_cents - settled[s.member_id],
        }
        for s in db.scalars(
            select(CircleShare).where(CircleShare.expense_id == expense.id).order_by(CircleShare.member_id)
        )
    ]


def circle_data(db, circle):
    members = [
        {"id": m.id, "name": m.name, "is_self": m.is_self}
        for m in db.scalars(
            select(CircleMember).where(CircleMember.circle_id == circle.id).order_by(CircleMember.id)
        )
    ]
    expenses = []
    history = []
    for e in db.scalars(
        select(CircleExpense)
        .where(CircleExpense.circle_id == circle.id, CircleExpense.active.is_(True))
        .order_by(CircleExpense.date.desc(), CircleExpense.id.desc())
    ):
        shares = debts(db, e)
        tx = db.get(Transaction, e.transaction_id) if e.transaction_id else None
        expenses.append(
            {
                "id": e.id,
                "title": e.title,
                "date": e.date.isoformat(),
                "amount_cents": e.amount_cents,
                "payer_id": e.payer_id,
                "method": e.method,
                "category": tx.category if tx else e.category,
                "transaction_id": e.transaction_id,
                "recurring": e.recurring,
                "shares": shares,
            }
        )
        for s in db.scalars(
            select(CircleSettlement).where(CircleSettlement.expense_id == e.id).order_by(CircleSettlement.id)
        ):
            history.append(
                {
                    "id": s.id,
                    "expense_id": e.id,
                    "title": e.title,
                    "member_id": s.member_id,
                    "payer_id": e.payer_id,
                    "date": s.date.isoformat(),
                    "amount_cents": s.amount_cents,
                    "transaction_id": s.transaction_id,
                    "cash_recorded": s.transaction_id is not None,
                }
            )
    self_id = next(m["id"] for m in members if m["is_self"])
    receivable = sum(s["remaining_cents"] for e in expenses if e["payer_id"] == self_id for s in e["shares"])
    payable = sum(
        s["remaining_cents"]
        for e in expenses
        if e["payer_id"] != self_id
        for s in e["shares"]
        if s["member_id"] == self_id
    )
    suggestions = [
        {
            "expense_id": e["id"],
            "from_member": s["member_id"],
            "to_member": e["payer_id"],
            "amount_cents": s["remaining_cents"],
        }
        for e in expenses
        for s in e["shares"]
        if s["remaining_cents"] > 0
    ]
    return {
        "id": circle.id,
        "name": circle.name,
        "kind": circle.kind,
        "currency": circle.currency,
        "members": members,
        "expenses": expenses,
        "settlements": history,
        "receivable_cents": receivable,
        "payable_cents": payable,
        "suggestions": suggestions,
        "note": "Local participants. Repayment recording is bookkeeping; Moniq sends no payments.",
    }


@router.get("")
def list_circles(db: Session = Depends(get_db)):
    return [circle_data(db, c) for c in db.scalars(select(Circle).order_by(Circle.id))]


@router.post("", status_code=201)
def create_circle(payload: CircleIn, request: Request, db: Session = Depends(get_db)):
    if demo(request) and (
        payload.name
        not in {
            "Campus friends",
            "Roommates",
            "Dining group",
            "Campus trip",
            "Shared subscriptions",
            "One-time expense",
        }
        or any(p not in SAMPLE_NAMES for p in payload.participants)
    ):
        raise HTTPException(403, "Public Circles use sample circle names and participants only.")
    with ledger_lock:
        circle = Circle(name=payload.name, kind=payload.kind, currency=payload.currency)
        db.add(circle)
        db.flush()
        db.add(CircleMember(circle_id=circle.id, name="Me", is_self=True))
        db.add_all(CircleMember(circle_id=circle.id, name=p, is_self=False) for p in payload.participants)
        audit(db, "circle-created", circle_id=circle.id)
        db.commit()
        return circle_data(db, circle)


def save_expense(db, circle, payload, request, existing=None):
    if payload.date > config.today() or not payload.title.strip() or payload.category == Category.income:
        raise HTTPException(422, "Use a posted date, title, and spending category.")
    if demo(request) and payload.title not in SAMPLE_TITLES:
        raise HTTPException(403, "Choose a sample expense title in the public demo.")
    members = {m.id: m for m in db.scalars(select(CircleMember).where(CircleMember.circle_id == circle.id))}
    if payload.payer_id not in members or not set(payload.shares).issubset(members):
        raise HTTPException(422, "Payer and participants must belong to this circle.")
    total = cents(payload.amount)
    if existing and db.scalar(select(CircleSettlement.id).where(CircleSettlement.expense_id == existing.id)):
        raise HTTPException(
            409, "Settled expenses are preserved for audit. Changing settled allocations requires a future auditable workflow."
        )
    if payload.transaction_id:
        tx = find(db, Transaction, payload.transaction_id)
        if (
            circle.currency != "USD"
            or not members[payload.payer_id].is_self
            or tx.kind != "expense"
            or tx.amount_cents != -total
            or tx.date != payload.date
        ):
            raise HTTPException(
                422, "Link a USD expense paid by Me with its unchanged posted amount and date."
            )
        linked = db.scalar(select(CircleExpense).where(CircleExpense.transaction_id == tx.id))
        if linked and (not existing or linked.id != existing.id):
            raise HTTPException(409, "This transaction already has an allocation.")
    allocation = allocate(total, payload.method, payload.shares)
    e = existing or CircleExpense(circle_id=circle.id)
    before = {"amount_cents": e.amount_cents, "transaction_id": e.transaction_id} if existing else None
    for key, value in {
        "payer_id": payload.payer_id,
        "title": payload.title.strip(),
        "date": payload.date,
        "amount_cents": total,
        "category": payload.category.value,
        "method": payload.method,
        "recurring": payload.recurring,
        "transaction_id": payload.transaction_id,
    }.items():
        setattr(e, key, value)
    db.add(e)
    db.flush()
    db.execute(delete(CircleShare).where(CircleShare.expense_id == e.id))
    db.add_all(CircleShare(expense_id=e.id, member_id=m, amount_cents=v) for m, v in allocation.items())
    audit(
        db,
        "expense-edited" if existing else "expense-created",
        expense_id=e.id,
        before=before,
        allocation=allocation,
        transaction_id=e.transaction_id,
    )
    db.commit()
    return circle_data(db, circle)


@router.post("/{circle_id}/expenses", status_code=201)
def create_expense(circle_id: int, payload: ExpenseIn, request: Request, db: Session = Depends(get_db)):
    with ledger_lock:
        return save_expense(db, find(db, Circle, circle_id), payload, request)


@router.put("/expenses/{expense_id}")
def edit_expense(expense_id: int, payload: ExpenseIn, request: Request, db: Session = Depends(get_db)):
    with ledger_lock:
        e = active_expense(db, expense_id)
        return save_expense(db, find(db, Circle, e.circle_id), payload, request, e)


@router.delete("/expenses/{expense_id}")
def remove_expense(expense_id: int, db: Session = Depends(get_db)):
    with ledger_lock:
        e = active_expense(db, expense_id)
        if db.scalar(select(CircleSettlement.id).where(CircleSettlement.expense_id == e.id)):
            raise HTTPException(409, "Settled expenses remain in the audit ledger.")
        audit(db, "expense-deleted", expense_id=e.id, transaction_id=e.transaction_id)
        e.active, e.transaction_id = False, None
        db.commit()
        return {"deleted": True, "bank_transaction_preserved": True}


@router.post("/expenses/{expense_id}/settlements", status_code=201)
def settle(expense_id: int, payload: SettlementIn, db: Session = Depends(get_db)):
    with ledger_lock:
        prior = db.scalar(select(CircleSettlement).where(CircleSettlement.request_key == payload.request_key))
        if prior:
            if (
                prior.expense_id != expense_id
                or prior.member_id != payload.member_id
                or prior.amount_cents != cents(payload.amount)
            ):
                raise HTTPException(409, "Repayment request key is already used for a different record.")
            return {"id": prior.id, "duplicate": True}
        e = active_expense(db, expense_id)
        if not payload.confirmed or payload.date < e.date or payload.date > config.today():
            raise HTTPException(
                422, "Confirm the repayment and use a date from the expense date through today."
            )
        debt = next((s for s in debts(db, e) if s["member_id"] == payload.member_id), None)
        amount = cents(payload.amount)
        if not debt or amount > debt["remaining_cents"]:
            raise HTTPException(422, "Repayment exceeds this participant's outstanding share.")
        circle = find(db, Circle, e.circle_id)
        payer = find(db, CircleMember, e.payer_id)
        member = find(db, CircleMember, payload.member_id)
        tx = None
        if payload.record_cash or payload.transaction_id:
            if circle.currency != "USD" or payer.is_self == member.is_self:
                raise HTTPException(422, "Bank cash can only be recorded for your own USD repayment.")
            signed = amount if payer.is_self else -amount
            if payload.transaction_id:
                tx = find(db, Transaction, payload.transaction_id)
                if (
                    tx.amount_cents != signed
                    or tx.date != payload.date
                    or tx.kind not in {"income", "refund", "expense"}
                ):
                    raise HTTPException(
                        422, "Match an existing posted cash transaction with the exact amount and date."
                    )
                if db.scalar(
                    select(CircleSettlement.id).where(CircleSettlement.transaction_id == tx.id)
                ) or db.scalar(select(CircleExpense.id).where(CircleExpense.transaction_id == tx.id)):
                    raise HTTPException(409, "This cash movement is already linked.")
                audit(db, "cash-reclassified", transaction_id=tx.id, previous_kind=tx.kind)
                tx.kind = "reimbursement" if signed > 0 else "settlement"
            else:
                account = find(db, Account, payload.account_id or 0)
                details = db.get(AccountDetails, account.id)
                if details and (payload.date < details.balance_date or details.account_type == "credit"):
                    raise HTTPException(422, "Choose a checking or savings account and a valid posted date.")
                tx = Transaction(
                    account_id=account.id,
                    date=payload.date,
                    description=f"Circle repayment: {e.title}",
                    merchant=member.name if payer.is_self else payer.name,
                    amount_cents=signed,
                    kind="reimbursement" if signed > 0 else "settlement",
                    category=e.category,
                    confidence=None,
                    source="circles",
                    fingerprint=hashlib.sha256(
                        f"circle-repayment:{payload.request_key}".encode()
                    ).hexdigest(),
                )
                db.add(tx)
                db.flush()
        s = CircleSettlement(
            expense_id=e.id,
            member_id=member.id,
            amount_cents=amount,
            date=payload.date,
            request_key=payload.request_key,
            transaction_id=tx.id if tx else None,
        )
        db.add(s)
        db.flush()
        audit(
            db, "repayment-recorded", settlement_id=s.id, amount_cents=amount, transaction_id=s.transaction_id
        )
        db.commit()
        return {"id": s.id, "transaction_id": s.transaction_id}


def allocated_rows(db, rows, start=None, end=None):
    """Personal spending stream, distinct from immutable bank cash rows."""
    from types import SimpleNamespace

    allocations = {}
    extras = []
    for e in db.scalars(select(CircleExpense).where(CircleExpense.active.is_(True))):
        c = db.get(Circle, e.circle_id)
        if c.currency != "USD":
            continue
        member = db.scalar(
            select(CircleMember).where(CircleMember.circle_id == c.id, CircleMember.is_self.is_(True))
        )
        share = db.scalar(
            select(CircleShare).where(CircleShare.expense_id == e.id, CircleShare.member_id == member.id)
        )
        own = share.amount_cents if share else 0
        if e.transaction_id:
            allocations[e.transaction_id] = own
        elif e.date <= (end or config.today()) and (not start or e.date >= start):
            extras.append(
                SimpleNamespace(
                    id=None,
                    date=e.date,
                    amount_cents=-own,
                    kind="expense",
                    category=e.category,
                    merchant=e.title,
                )
            )
    result = []
    for t in rows:
        if t.kind in {"reimbursement", "settlement"}:
            continue
        amount = -allocations[t.id] if t.id in allocations else t.amount_cents
        result.append(
            SimpleNamespace(
                id=t.id,
                date=t.date,
                amount_cents=amount,
                kind=t.kind,
                category=t.category,
                merchant=t.merchant,
            )
        )
    return result + extras


def summary(db):
    circles = list_circles(db)
    currencies = {}
    shared_meals = rent = 0
    recurring = []
    for c in circles:
        totals = currencies.setdefault(c["currency"], {"receivable_cents": 0, "payable_cents": 0})
        totals["receivable_cents"] += c["receivable_cents"]
        totals["payable_cents"] += c["payable_cents"]
        self_id = next(m["id"] for m in c["members"] if m["is_self"])
        for e in c["expenses"]:
            own = sum(s["share_cents"] for s in e["shares"] if s["member_id"] == self_id)
            if (
                c["currency"] == "USD"
                and e["category"] == "food"
                and e["date"] >= config.today().replace(day=1).isoformat()
            ):
                shared_meals += own
            if e["recurring"]:
                recurring.append(
                    {
                        "title": e["title"],
                        "currency": c["currency"],
                        "own_share_cents": own,
                        "category": e["category"],
                    }
                )
                if c["currency"] == "USD" and e["category"] == "rent":
                    rent += own
    return {
        "circle_count": len(circles),
        "currencies": currencies,
        "shared_meals_cents": shared_meals,
        "next_month_rent_reserve_cents": rent,
        "recurring": recurring,
    }


@router.get("/insights")
def get_insights(db: Session = Depends(get_db)):
    return summary(db)


def guard_transaction(db, tx_id):
    from .models import AccountTransfer
    tx = db.get(Transaction, tx_id)
    if tx and (tx.source == "account-ledger" or db.scalar(select(AccountTransfer.id).where((AccountTransfer.debit_id == tx_id) | (AccountTransfer.credit_id == tx_id)))):
        raise HTTPException(409, "Account transfers and reconciliation entries are immutable. Record a new movement or reconciliation.")
    if db.scalar(
        select(CircleExpense.id).where(CircleExpense.transaction_id == tx_id, CircleExpense.active.is_(True))
    ) or db.scalar(select(CircleSettlement.id).where(CircleSettlement.transaction_id == tx_id)):
        raise HTTPException(
            409,
            "This transaction is linked to the Circles ledger. Preserve its cash movement; edit the allocation in Circles.",
        )
