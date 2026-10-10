from datetime import date
from decimal import Decimal, InvalidOperation
from enum import Enum

from pydantic import BaseModel, Field, field_validator, model_validator


class Category(str, Enum):
    food = "food"
    groceries = "groceries"
    shopping = "shopping"
    transportation = "transportation"
    rent = "rent"
    education = "education"
    subscriptions = "subscriptions"
    entertainment = "entertainment"
    healthcare = "healthcare"
    income = "income"
    miscellaneous = "miscellaneous"


def cents(amount) -> int:
    try:
        value = Decimal(str(amount))
        if not value.is_finite() or abs(value) > 1_000_000:
            raise ValueError("Amount must be finite and within $1,000,000.")
        if value != value.quantize(Decimal("0.01")):
            raise ValueError("Amount must have no more than two decimal places.")
        return int(value * 100)
    except InvalidOperation as exc:
        raise ValueError("Invalid amount.") from exc


class TransactionIn(BaseModel):
    date: date
    description: str = Field(min_length=1, max_length=300)
    merchant: str | None = Field(default=None, max_length=160)
    amount: Decimal
    kind: str = Field(default="expense", pattern="^(expense|income|refund|reimbursement|settlement)$")
    category: Category | None = None
    notification_text: str | None = Field(default=None, max_length=2000)
    account_id: int = Field(default=1, ge=1)

    @field_validator("description", "merchant")
    @classmethod
    def not_blank(cls, value):
        if value is not None and not value.strip():
            raise ValueError("Text must not be blank.")
        return value.strip() if value else value

    @field_validator("amount")
    @classmethod
    def valid_money(cls, value):
        if cents(value) == 0:
            raise ValueError("Transaction amount must not be zero.")
        return value

    @model_validator(mode="after")
    def valid_category(self):
        if self.kind != "income" and self.category == Category.income:
            raise ValueError("Income category requires income transaction type.")
        return self


class ClassifyIn(BaseModel):
    description: str = Field(min_length=1, max_length=300)


class MessageIn(BaseModel):
    text: str = Field(min_length=1, max_length=2000)


class BudgetIn(BaseModel):
    category: Category
    period: str = Field(default="monthly", pattern="^(monthly|weekly)$")
    limit: Decimal = Field(ge=0, le=1_000_000)

    @field_validator("limit")
    @classmethod
    def valid_limit(cls, value):
        cents(value)
        return value


class ScenarioIn(BaseModel):
    purchase: Decimal = Field(default=0, ge=0, le=1_000_000)
    savings: Decimal = Field(default=0, ge=0, le=1_000_000)
    extra_income: Decimal = Field(default=0, ge=0, le=1_000_000)
    delay_days: int = Field(default=0, ge=0, le=365)

    @field_validator("purchase", "savings", "extra_income")
    @classmethod
    def valid_amount(cls, value):
        cents(value)
        return value


class ProfileIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    university: str = Field(min_length=1, max_length=120)
    academic_year: str = Field(min_length=1, max_length=30)
    allowance: Decimal = Field(ge=0, le=1_000_000)
    income_preference: str = Field(min_length=1, max_length=60)
    interests: str = Field(max_length=300)
    student_verified: bool
    notifications: bool

    @field_validator("allowance")
    @classmethod
    def valid_allowance(cls, value):
        cents(value)
        return value

    @field_validator("name", "university", "academic_year", "income_preference")
    @classmethod
    def nonempty(cls, value):
        if not value.strip():
            raise ValueError("Text must not be blank.")
        return value.strip()


class GoalIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    target: Decimal = Field(gt=0, le=1_000_000)
    saved: Decimal = Field(ge=0, le=1_000_000)

    @field_validator("target", "saved")
    @classmethod
    def valid_goal_money(cls, value):
        cents(value)
        return value


class SubscriptionIn(BaseModel):
    status: str = Field(pattern="^(confirmed|incorrect)$")


class ScheduleIn(BaseModel):
    merchant: str = Field(min_length=1, max_length=160)
    amount: Decimal = Field(gt=0, le=1_000_000)
    category: Category
    kind: str = Field(pattern="^(expense|income)$")
    next_due: date
    interval_days: int = Field(default=30, ge=0, le=365)

    @field_validator("amount")
    @classmethod
    def valid_schedule_amount(cls, value):
        cents(value)
        return value

    @field_validator("merchant")
    @classmethod
    def valid_merchant(cls, value):
        if not value.strip():
            raise ValueError("Merchant must not be blank.")
        return value.strip()

    @model_validator(mode="after")
    def valid_income(self):
        if (self.kind == "income") != (self.category == Category.income):
            raise ValueError("Income schedules require the income category; expenses require a spending category.")
        return self
