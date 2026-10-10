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
