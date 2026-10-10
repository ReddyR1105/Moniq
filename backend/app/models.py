from datetime import date

from sqlalchemy import Boolean, Date, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Profile(Base):
    __tablename__ = "profiles"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80), default="Alex Morgan")
    university: Mapped[str] = mapped_column(String(120), default="Georgia State University")
    academic_year: Mapped[str] = mapped_column(String(30), default="Junior")
    allowance_cents: Mapped[int] = mapped_column(Integer, default=60000)
    income_preference: Mapped[str] = mapped_column(String(60), default="Part-time employment")
    interests: Mapped[str] = mapped_column(String(300), default="food,technology,education,transportation")
    student_verified: Mapped[bool] = mapped_column(Boolean, default=True)
    notifications: Mapped[bool] = mapped_column(Boolean, default=True)


class Account(Base):
    __tablename__ = "accounts"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80), default="Campus checking")
    opening_balance_cents: Mapped[int] = mapped_column(Integer, default=200000)
    mode: Mapped[str] = mapped_column(String(20), default="demo")


class Transaction(Base):
    __tablename__ = "transactions"
    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), default=1)
    date: Mapped[date] = mapped_column(Date, index=True)
    description: Mapped[str] = mapped_column(String(300))
    merchant: Mapped[str] = mapped_column(String(160), index=True)
    amount_cents: Mapped[int] = mapped_column(Integer)
    kind: Mapped[str] = mapped_column(String(20))
    category: Mapped[str] = mapped_column(String(30), index=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    source: Mapped[str] = mapped_column(String(30), default="manual")
    fingerprint: Mapped[str] = mapped_column(String(64), unique=True)


class Budget(Base):
    __tablename__ = "budgets"
    __table_args__ = (UniqueConstraint("category", "period"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    category: Mapped[str] = mapped_column(String(30))
    period: Mapped[str] = mapped_column(String(10), default="monthly")
    limit_cents: Mapped[int] = mapped_column(Integer)


class RecurringPayment(Base):
    __tablename__ = "recurring_payments"
    id: Mapped[int] = mapped_column(primary_key=True)
    merchant: Mapped[str] = mapped_column(String(160), unique=True)
    amount_cents: Mapped[int] = mapped_column(Integer)
    category: Mapped[str] = mapped_column(String(30))
    kind: Mapped[str] = mapped_column(String(20), default="expense")
    next_due: Mapped[date] = mapped_column(Date)
    interval_days: Mapped[int] = mapped_column(Integer, default=30)
    status: Mapped[str] = mapped_column(String(20), default="confirmed")


class Deal(Base):
    __tablename__ = "deals"
    id: Mapped[int] = mapped_column(primary_key=True)
    merchant: Mapped[str] = mapped_column(String(120))
    category: Mapped[str] = mapped_column(String(30))
    description: Mapped[str] = mapped_column(String(300))
    eligibility: Mapped[str] = mapped_column(String(200))
    original_cents: Mapped[int | None] = mapped_column(Integer, nullable=True)
    discounted_cents: Mapped[int | None] = mapped_column(Integer, nullable=True)
    expiration: Mapped[date | None] = mapped_column(Date, nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(300), nullable=True)
    verification: Mapped[str] = mapped_column(String(30), default="synthetic sample")


class Goal(Base):
    __tablename__ = "goals"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80))
    target_cents: Mapped[int] = mapped_column(Integer)
    saved_cents: Mapped[int] = mapped_column(Integer, default=0)


class Notification(Base):
    __tablename__ = "notifications"
    id: Mapped[int] = mapped_column(primary_key=True)
    text: Mapped[str] = mapped_column(Text)
    transaction_id: Mapped[int] = mapped_column(ForeignKey("transactions.id"))


class Correction(Base):
    __tablename__ = "corrections"
    id: Mapped[int] = mapped_column(primary_key=True)
    description: Mapped[str] = mapped_column(String(300))
    previous_category: Mapped[str] = mapped_column(String(30))
    corrected_category: Mapped[str] = mapped_column(String(30))


class AccountDetails(Base):
    """Additive metadata: existing accounts and transactions require no ALTER/DROP."""
    __tablename__ = "account_details"
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), primary_key=True)
    account_type: Mapped[str] = mapped_column(String(20), default="checking")
    last_four: Mapped[str | None] = mapped_column(String(4), nullable=True)
    balance_date: Mapped[date] = mapped_column(Date)


class GmailItem(Base):
    __tablename__ = "gmail_items"
    __table_args__ = (UniqueConstraint("mailbox_key", "message_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    mailbox_key: Mapped[str] = mapped_column(String(64))
    message_id: Mapped[str] = mapped_column(String(128))
    subject: Mapped[str] = mapped_column(String(300))
    sender: Mapped[str] = mapped_column(String(200))
    event_type: Mapped[str] = mapped_column(String(30))
    merchant: Mapped[str] = mapped_column(String(160))
    amount_cents: Mapped[int | None] = mapped_column(Integer, nullable=True)
    date: Mapped[date] = mapped_column(Date)
    last_four: Mapped[str | None] = mapped_column(String(4), nullable=True)
    category: Mapped[str] = mapped_column(String(30))
    confidence: Mapped[float] = mapped_column(Float)
    reasons: Mapped[str] = mapped_column(Text, default="[]")
    account_id: Mapped[int | None] = mapped_column(ForeignKey("accounts.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="review")
    transaction_id: Mapped[int | None] = mapped_column(ForeignKey("transactions.id"), nullable=True)


class Circle(Base):
    __tablename__ = "circles"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80))
    kind: Mapped[str] = mapped_column(String(30))
    currency: Mapped[str] = mapped_column(String(3), default="USD")


class CircleMember(Base):
    __tablename__ = "circle_members"
    id: Mapped[int] = mapped_column(primary_key=True)
    circle_id: Mapped[int] = mapped_column(ForeignKey("circles.id"))
    name: Mapped[str] = mapped_column(String(80))
    is_self: Mapped[bool] = mapped_column(Boolean, default=False)


class CircleExpense(Base):
    __tablename__ = "circle_expenses"
    id: Mapped[int] = mapped_column(primary_key=True)
    circle_id: Mapped[int] = mapped_column(ForeignKey("circles.id"))
    payer_id: Mapped[int] = mapped_column(ForeignKey("circle_members.id"))
    title: Mapped[str] = mapped_column(String(120))
    date: Mapped[date] = mapped_column(Date)
    amount_cents: Mapped[int] = mapped_column(Integer)
    category: Mapped[str] = mapped_column(String(30))
    method: Mapped[str] = mapped_column(String(20))
    recurring: Mapped[bool] = mapped_column(Boolean, default=False)
    transaction_id: Mapped[int | None] = mapped_column(ForeignKey("transactions.id"), nullable=True, unique=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class CircleShare(Base):
    __tablename__ = "circle_shares"
    __table_args__ = (UniqueConstraint("expense_id", "member_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    expense_id: Mapped[int] = mapped_column(ForeignKey("circle_expenses.id"))
    member_id: Mapped[int] = mapped_column(ForeignKey("circle_members.id"))
    amount_cents: Mapped[int] = mapped_column(Integer)


class CircleSettlement(Base):
    __tablename__ = "circle_settlements"
    id: Mapped[int] = mapped_column(primary_key=True)
    expense_id: Mapped[int] = mapped_column(ForeignKey("circle_expenses.id"))
    member_id: Mapped[int] = mapped_column(ForeignKey("circle_members.id"))
    amount_cents: Mapped[int] = mapped_column(Integer)
    date: Mapped[date] = mapped_column(Date)
    transaction_id: Mapped[int | None] = mapped_column(ForeignKey("transactions.id"), nullable=True, unique=True)
    request_key: Mapped[str] = mapped_column(String(80), unique=True)


class LedgerAudit(Base):
    __tablename__ = "ledger_audits"
    id: Mapped[int] = mapped_column(primary_key=True)
    action: Mapped[str] = mapped_column(String(50))
    day: Mapped[date] = mapped_column(Date)
    details: Mapped[str] = mapped_column(Text)


class TrustedSender(Base):
    __tablename__ = "trusted_senders"
    id: Mapped[int] = mapped_column(primary_key=True)
    sender: Mapped[str] = mapped_column(String(200))
    match_type: Mapped[str] = mapped_column(String(10))
    institution: Mapped[str] = mapped_column(String(80))
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"))
    events: Mapped[str] = mapped_column(Text)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    suspended: Mapped[bool] = mapped_column(Boolean, default=False)
    removed: Mapped[bool] = mapped_column(Boolean, default=False)
    transaction_cap: Mapped[int] = mapped_column(Integer)
    daily_cap: Mapped[int] = mapped_column(Integer)


class ApprovalAudit(Base):
    __tablename__ = "approval_audits"
    id: Mapped[int] = mapped_column(primary_key=True)
    action: Mapped[str] = mapped_column(String(30))
    day: Mapped[date] = mapped_column(Date)
    rule_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    transaction_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    amount_cents: Mapped[int] = mapped_column(Integer, default=0)
    details: Mapped[str] = mapped_column(Text)


class GmailEvidence(Base):
    __tablename__ = "gmail_evidence"
    item_id: Mapped[int] = mapped_column(ForeignKey("gmail_items.id"), primary_key=True)
    details: Mapped[str] = mapped_column(Text)


class DebitCard(Base):
    __tablename__ = "debit_cards"
    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"))
    name: Mapped[str] = mapped_column(String(80))
    last_four: Mapped[str] = mapped_column(String(4), unique=True)


class AccountTransfer(Base):
    __tablename__ = "account_transfers"
    id: Mapped[int] = mapped_column(primary_key=True)
    request_key: Mapped[str] = mapped_column(String(80), unique=True)
    debit_id: Mapped[int] = mapped_column(ForeignKey("transactions.id"), unique=True)
    credit_id: Mapped[int] = mapped_column(ForeignKey("transactions.id"), unique=True)


class GoalContribution(Base):
    __tablename__ = "goal_contributions"
    id: Mapped[int] = mapped_column(primary_key=True)
    goal_id: Mapped[int] = mapped_column(ForeignKey("goals.id"))
    date: Mapped[date] = mapped_column(Date)
    amount_cents: Mapped[int] = mapped_column(Integer)
    request_key: Mapped[str] = mapped_column(String(80), unique=True)


class GoalPlan(Base):
    __tablename__ = "goal_plans"
    goal_id: Mapped[int] = mapped_column(ForeignKey("goals.id"), primary_key=True)
    monthly_cents: Mapped[int] = mapped_column(Integer, default=0)
