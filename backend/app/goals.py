"""Savings progress records are separate from cash; plans never become deposits."""
import math
from datetime import date, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import config
from .circles import ledger_lock
from .database import get_db
from .models import Goal, GoalContribution, GoalPlan
from .schemas import cents

router = APIRouter(prefix="/api/goals")


def goal_rows(db):
    rows = []
    for g in db.scalars(select(Goal).order_by(Goal.id)):
        plan = db.get(GoalPlan, g.id)
        monthly = plan.monthly_cents if plan else 0
        remaining = max(0, g.target_cents - g.saved_cents)
        days = math.ceil(remaining / monthly * 30) if monthly else None
        completion = config.today() if remaining == 0 else config.today() + timedelta(days=days) if days is not None and days < 365 * 100 else None
        rows.append({"id": g.id, "name": g.name, "target": g.target_cents / 100, "saved": g.saved_cents / 100,
                     "monthly_contribution": monthly / 100, "projected_completion": completion.isoformat() if completion else None,
                     "recommendation": f"Plan ${monthly/100:.2f} per month toward the ${remaining/100:.2f} remaining. Adjust the plan to fit your budget." if monthly else f"Set a monthly contribution plan for the ${remaining/100:.2f} remaining; no completion date is assumed.",
                     "assumption": "Linear estimate using your planned monthly contribution; no interest or automatic money movement.",
                     "contributions": [{"id": c.id, "date": c.date.isoformat(), "amount": c.amount_cents / 100} for c in db.scalars(select(GoalContribution).where(GoalContribution.goal_id == g.id).order_by(GoalContribution.date))]})
    return rows


class PlanIn(BaseModel):
    monthly_contribution: Decimal = Field(ge=0, le=1_000_000)

    @field_validator("monthly_contribution")
    @classmethod
    def precise(cls, value):
        cents(value)
        return value


@router.put("/{goal_id}/plan")
def plan(goal_id: int, payload: PlanIn, db: Session = Depends(get_db)):
    with ledger_lock:
        if not db.get(Goal, goal_id):
            raise HTTPException(404, "Savings goal not found.")
        row = db.get(GoalPlan, goal_id)
        if not row:
            row = GoalPlan(goal_id=goal_id)
            db.add(row)
        row.monthly_cents = cents(payload.monthly_contribution)
        db.commit()
        return goal_rows(db)


class ContributionIn(BaseModel):
    amount: Decimal = Field(gt=0, le=1_000_000)
    date: date
    request_key: str = Field(min_length=8, max_length=80, pattern=r"^[A-Za-z0-9_-]+$")

    @field_validator("amount")
    @classmethod
    def precise(cls, value):
        cents(value)
        return value


@router.post("/{goal_id}/contributions", status_code=201)
def contribute(goal_id: int, payload: ContributionIn, db: Session = Depends(get_db)):
    with ledger_lock:
        goal = db.get(Goal, goal_id)
        if not goal:
            raise HTTPException(404, "Savings goal not found.")
        if payload.date > config.today():
            raise HTTPException(422, "Future contributions belong in your plan, not recorded progress.")
        prior = db.scalar(select(GoalContribution).where(GoalContribution.request_key == payload.request_key))
        amount = cents(payload.amount)
        if prior:
            if (prior.goal_id, prior.date, prior.amount_cents) != (goal_id, payload.date, amount):
                raise HTTPException(409, "That request key belongs to another contribution.")
            return goal_rows(db)
        if goal.saved_cents + amount > 100_000_000:
            raise HTTPException(422, "Recorded progress cannot exceed $1,000,000.")
        goal.saved_cents += amount
        db.add(GoalContribution(goal_id=goal_id, date=payload.date, amount_cents=amount, request_key=payload.request_key))
        db.commit()
        return goal_rows(db)
