import calendar
import re
import statistics
from collections import defaultdict
from datetime import date, timedelta
from functools import wraps
from threading import RLock

from sqlalchemy import select

from .config import today
from .models import Account, AccountDetails, Budget, Deal, Profile, RecurringPayment, Transaction

_recurring_lock = RLock()


def serialized_detection(function):
    @wraps(function)
    def wrapped(*args, **kwargs):
        with _recurring_lock:
            return function(*args, **kwargs)
    return wrapped


def money(value):
    return round(value / 100, 2)


def records(db, start=None, end=None):
    query = select(Transaction).where(Transaction.date <= (end or today()))
    if start:
        query = query.where(Transaction.date >= start)
    return list(db.scalars(query.order_by(Transaction.date, Transaction.id)))


def spending(rows, db=None, start=None, end=None):
    if db is not None:
        from .circles import allocated_rows
        rows = allocated_rows(db, rows, start, end)
    totals = defaultdict(int)
    for row in rows:
        if row.kind not in {"income", "reimbursement", "settlement", "transfer", "adjustment"}:
            totals[row.category] -= row.amount_cents
    return dict(totals)


def balance_cents(db):
    credit = set(db.scalars(select(AccountDetails.account_id).where(AccountDetails.account_type == "credit")))
    opening = sum(a.opening_balance_cents for a in db.scalars(select(Account)) if a.id not in credit)
    return opening + sum(t.amount_cents for t in records(db) if t.account_id not in credit)


def period_start(period, now=None):
    now = now or today()
    return now - timedelta(days=now.weekday()) if period == "weekly" else now.replace(day=1)


def budgets(db):
    result = []
    for row in db.scalars(select(Budget).order_by(Budget.period, Budget.category)):
        used = spending(records(db, period_start(row.period)), db, period_start(row.period)).get(row.category, 0)
        result.append({"id": row.id, "category": row.category, "period": row.period,
                       "limit": money(row.limit_cents), "spent": money(used), "remaining": money(row.limit_cents - used),
                       "progress": round(max(0, used) / row.limit_cents, 4) if row.limit_cents else (1 if used > 0 else 0),
                       "overspent": used > row.limit_cents})
    return result


def advance_due(day, interval, anchor_day=None):
    if interval == 30:
        month, year = day.month + 1, day.year
        if month == 13:
            month, year = 1, year + 1
        return date(year, month, min(anchor_day or day.day, calendar.monthrange(year, month)[1]))
    return day + timedelta(days=interval)


@serialized_detection
def detect_subscriptions(db):
    grouped = defaultdict(list)
    for row in records(db, today() - timedelta(days=180)):
        if row.kind == "expense" and row.category not in {"rent", "education", "income"}:
            grouped[row.merchant].append(row)
    existing = {r.merchant: r for r in db.scalars(select(RecurringPayment))}
    result = []
    for merchant, rows in grouped.items():
        if len(rows) < 3:
            continue
        # Regular shopping trips or cinema visits are not necessarily subscriptions.
        if not any(r.category == "subscriptions" for r in rows) and not re.search(r"subscription|premium|membership|streaming|monthly service", merchant, re.I):
            continue
        rows.sort(key=lambda r: r.date)
        intervals = [(b.date - a.date).days for a, b in zip(rows, rows[1:])]
        typical_interval = statistics.median(intervals)
        amounts = [abs(r.amount_cents) for r in rows]
        typical_amount = int(statistics.median(amounts))
        if not (25 <= typical_interval <= 35) or max(amounts) - min(amounts) > typical_amount * 0.15:
            continue
        if any(not 20 <= interval <= 45 for interval in intervals):
            continue
        anchor_day = max(row.date.day for row in rows)
        renewal = advance_due(rows[-1].date, 30, anchor_day)
        while renewal <= today():
            renewal = advance_due(renewal, 30, anchor_day)
        recurring = existing.get(merchant)
        if not recurring:
            recurring = RecurringPayment(merchant=merchant, amount_cents=typical_amount, category=rows[-1].category,
                                         kind="expense", next_due=renewal, interval_days=30, status="candidate")
            db.add(recurring)
            db.flush()
        else:
            if recurring.status == "candidate":
                recurring.next_due = renewal
                recurring.amount_cents = typical_amount
            else:
                renewal = recurring.next_due
                while renewal <= today() and recurring.interval_days:
                    renewal = advance_due(renewal, recurring.interval_days, recurring.next_due.day)
                typical_amount = recurring.amount_cents
        result.append({"id": recurring.id, "merchant": merchant, "amount": money(typical_amount),
                       "renewal": renewal.isoformat(), "annual_cost": money(typical_amount * 12),
                       "status": recurring.status, "category": recurring.category, "evidence_count": len(rows),
                       "explanation": f"{len(rows)} similar charges, approximately every {typical_interval:g} days."})
    detected = {r["merchant"] for r in result}
    for merchant, recurring in existing.items():
        if recurring.status == "candidate" and merchant not in detected:
            db.delete(recurring)
    db.commit()
    active = [r for r in result if r["status"] != "incorrect"]
    return {"items": result, "monthly_total": round(sum(r["amount"] for r in active), 2),
            "annual_total": round(sum(r["annual_cost"] for r in active), 2),
            "possible_duplicates": ["Multiple streaming subscriptions: review whether both are useful."] if sum("Netflix" in r["merchant"] or "Spotify" in r["merchant"] for r in active) > 1 else [],
            "note": "Pattern detection is an estimate. Confirmation does not cancel a subscription."}


def scheduled_events(db, days=30):
    end = today() + timedelta(days=days)
    events = []
    for row in db.scalars(select(RecurringPayment).where(RecurringPayment.status != "incorrect")):
        due = row.next_due
        if row.interval_days == 0:
            if today() < due <= end:
                events.append({"date": due.isoformat(), "merchant": row.merchant, "amount": money(row.amount_cents),
                               "category": row.category, "kind": row.kind, "status": row.status})
            continue
        while due <= today():
            due = advance_due(due, row.interval_days, row.next_due.day)
        while due <= end:
            events.append({"date": due.isoformat(), "merchant": row.merchant, "amount": money(row.amount_cents),
                           "category": row.category, "kind": row.kind, "status": row.status})
            due = advance_due(due, row.interval_days, row.next_due.day)
    return sorted(events, key=lambda e: (e["date"], e["merchant"]))


def forecast(db, scenario=None):
    detect_subscriptions(db)
    now = today()
    start = now - timedelta(days=59)
    history = records(db, start)
    earliest = min((r.date for r in history), default=now)
    observed_days = max(1, (now - max(start, earliest)).days + 1)
    recurring_merchants = {r.merchant for r in db.scalars(select(RecurringPayment).where(RecurringPayment.status != "incorrect")) if r.interval_days or r.next_due > now}
    # Forecast bank cash from full historical cash charges, never anticipated reimbursements.
    credit = set(db.scalars(select(AccountDetails.account_id).where(AccountDetails.account_type == "credit")))
    discretionary_cents = max(0, -sum(r.amount_cents for r in history if r.kind in {"expense", "refund"} and r.account_id not in credit and r.merchant not in recurring_merchants))
    expected_cents = round(discretionary_cents * 30 / observed_days)
    events = scheduled_events(db)
    by_date = defaultdict(list)
    for event in events:
        by_date[event["date"]].append(event)
    purchase = scenario.get("purchase_cents", 0) if scenario else 0
    requested_savings = scenario.get("savings_cents", 0) if scenario else 0
    savings = min(expected_cents, requested_savings)
    extra_income = scenario.get("extra_income_cents", 0) if scenario else 0
    delay = scenario.get("delay_days", 0) if scenario else 0
    current = balance_cents(db)
    timeline = [{"date": now.isoformat(), "balance": money(current), "scheduled_net": 0}]
    scheduled_expense, scheduled_income = 0, 0
    for offset in range(1, 31):
        day = (now + timedelta(days=offset)).isoformat()
        # Quotient/remainder distribution preserves the exact 30-day total.
        baseline = ((expected_cents - savings) * offset // 30) - ((expected_cents - savings) * (offset - 1) // 30)
        net = 0
        for event in by_date[day]:
            amount = round(event["amount"] * 100)
            if event["kind"] == "income":
                net += amount
                scheduled_income += amount
            else:
                net -= amount
                scheduled_expense += amount
        current += net - baseline
        if offset == 1:
            current += extra_income
        if offset == max(1, delay):
            current -= purchase
        timeline.append({"date": day, "balance": money(current), "scheduled_net": money(net)})
    minimum = min(point["balance"] for point in timeline)
    current_budgets = budgets(db)
    month_days = calendar.monthrange(now.year, now.month)[1]
    risks = [{"category": b["category"], "projected": round(b["spent"] / now.day * month_days, 2), "limit": b["limit"]}
             for b in current_budgets if b["period"] == "monthly" and b["category"] not in {"rent", "education", "subscriptions"}
             and b["spent"] / now.day * month_days > b["limit"]]
    return {"timeline": timeline, "current_balance": money(balance_cents(db)), "projected_balance": money(current),
            "minimum_balance": minimum, "cash_shortfall": minimum < 0,
            "shortfall_date": next((p["date"] for p in timeline if p["balance"] < 0), None),
            "expected_spending": money(expected_cents - savings + scheduled_expense),
            "discretionary_spending": money(expected_cents), "scheduled_expenses": money(scheduled_expense),
            "scheduled_income": money(scheduled_income), "events": events, "budget_risks": risks,
            "applied_savings": money(savings), "purchase_in_horizon": delay <= 30,
            "assumptions": [f"Daily variable spending uses {observed_days} observed days of the last 60 days, net of refunds.",
                            "Scheduled merchants are excluded from the daily average and counted on their due dates once.",
                            "Monthly charges follow calendar months; payroll repeats every 14 days. Candidate subscriptions are included until marked incorrect.",
                            "Only stored income schedules are included; no hypothetical scholarship or earnings are assumed.",
                            "Shared purchases retain their full bank cash charge. Outstanding reimbursements are never assumed to arrive.",
                            "Scenarios apply extra income tomorrow and distribute spending reductions across 30 days, capped at estimated variable spending.",
                            "Forecasts are estimates, not guarantees. Sparse or irregular history can distort the average."]}


def deal_recommendations(db):
    profile = db.get(Profile, 1)
    totals = spending(records(db, today() - timedelta(days=29)), db, today() - timedelta(days=29))
    limits = {b["category"]: b for b in budgets(db) if b["period"] == "monthly"}
    interests = {interest.strip() for interest in (profile.interests if profile else "").lower().split(",") if interest.strip()}
    if "technology" in interests or "clothing" in interests:
        interests.add("shopping")
    if "restaurants" in interests:
        interests.add("food")
    result = []
    omitted = 0
    for row in db.scalars(select(Deal)):
        known_prices = row.original_cents is not None and row.discounted_cents is not None
        savings = row.original_cents - row.discounted_cents if known_prices else 0
        relevant = totals.get(row.category, 0) > 0 or row.category in interests
        budget = limits.get(row.category)
        room = max(0, round(budget["remaining"] * 100)) if budget else max(0, balance_cents(db))
        affordable = row.discounted_cents is None or row.discounted_cents <= min(room, max(0, balance_cents(db)))
        eligible = bool(profile and profile.student_verified)
        expired = bool(row.expiration and row.expiration < today())
        if not relevant or not affordable or not eligible or expired or savings <= 0:
            omitted += 1
            continue
        score = savings / max(row.original_cents, 1) * 35 + min(totals.get(row.category, 0) / 1000, 35) + (15 if row.category in interests else 0)
        result.append({"id": row.id, "merchant": row.merchant, "category": row.category, "description": row.description,
                       "eligibility": row.eligibility, "original_price": money(row.original_cents) if known_prices else None,
                       "discounted_price": money(row.discounted_cents) if known_prices else None, "savings": money(savings),
                       "expiration": row.expiration.isoformat() if row.expiration else None, "source_url": row.source_url,
                       "verification": row.verification, "score": round(score, 2),
                       "reason": f"Matches your {row.category} spending or interests and fits your remaining category budget. Save ${money(savings):.2f} only if this replaces a planned purchase."})
    return {"items": sorted(result, key=lambda r: (-r["score"], r["id"])), "omitted": omitted,
            "potential_savings": round(sum(r["savings"] for r in result), 2),
            "notice": "All offers are synthetic examples, not verified or redeemable discounts. Savings are alternatives, not guaranteed or additive."}


def insights(db):
    now = today()
    recent = records(db, now - timedelta(days=29))
    prior = records(db, now - timedelta(days=59), now - timedelta(days=30))
    recent_totals, prior_totals = spending(recent, db, now - timedelta(days=29)), spending(prior, db, now - timedelta(days=59), now - timedelta(days=30))
    increases = [{"category": cat, "change": money(total - prior_totals.get(cat, 0)), "recent": money(total)}
                 for cat, total in recent_totals.items() if total - prior_totals.get(cat, 0) > 1000]
    history = records(db, now - timedelta(days=90), now - timedelta(days=7))
    amounts = defaultdict(list)
    for row in history:
        if row.kind == "expense":
            amounts[row.category].append(abs(row.amount_cents))
    anomalies = []
    for row in records(db, now - timedelta(days=6)):
        previous = amounts[row.category]
        if row.kind == "expense" and len(previous) >= 3:
            median = statistics.median(previous)
            if abs(row.amount_cents) > max(2000, median * 2.5):
                anomalies.append({"merchant": row.merchant, "amount": money(abs(row.amount_cents)), "category": row.category,
                                  "explanation": f"Above 2.5× your prior median of ${money(median):.2f}. This may be intentional."})
    warnings = [f"{b['category'].title()} is ${-b['remaining']:.2f} over its {b['period']} limit." for b in budgets(db) if b["overspent"]]
    suggestions = ["Replace a planned grocery or meal purchase with a sample student offer; do not spend just to get a discount.",
                   "Review recurring services and keep the ones you use. Mark incorrect detections to improve your forecast."]
    if recent_totals.get("food", 0) > 0:
        suggestions.insert(0, f"Reducing restaurant spending by 10% of the last 30 days would save about ${money(round(recent_totals['food'] * 0.1)):.2f}.")
    return {"increases": sorted(increases, key=lambda r: -r["change"]), "anomalies": anomalies,
            "warnings": warnings, "suggestions": suggestions, "method": "Equal 30-day comparisons and category medians; statistical rules, not fraud detection."}


def dashboard(db):
    now = today()
    month = records(db, now.replace(day=1))
    totals = spending(month, db, now.replace(day=1))
    income = sum(t.amount_cents for t in month if t.kind == "income")
    expense = sum(totals.values())
    monthly_limits = sum(b.limit_cents for b in db.scalars(select(Budget).where(Budget.period == "monthly")))
    weekly = []
    for offset in range(6, -1, -1):
        day = now - timedelta(days=offset)
        weekly.append({"date": day.isoformat(), "day": day.strftime("%a"), "amount": money(sum(spending(records(db, day, day), db, day, day).values()))})
    subscriptions = detect_subscriptions(db)
    deals = deal_recommendations(db)
    from .circles import summary as circles_summary
    credit = set(db.scalars(select(AccountDetails.account_id).where(AccountDetails.account_type == "credit")))
    credit_debt = sum(max(0, -a.opening_balance_cents - sum(t.amount_cents for t in records(db) if t.account_id == a.id)) for a in db.scalars(select(Account)) if a.id in credit)
    return {"credit_outstanding": money(credit_debt), "estimated": any(a.mode in {"registered", "scenario"} for a in db.scalars(select(Account))), "circles": circles_summary(db), "cash_expenses": money(-sum(t.amount_cents for t in month if t.amount_cents < 0 and t.account_id not in credit and t.kind not in {"transfer", "adjustment"})), "as_of": now.isoformat(), "balance": money(balance_cents(db)), "income": money(income),
            "expenses": money(expense), "remaining_budget": money(monthly_limits - expense), "budget_total": money(monthly_limits),
            "weekly_spending": weekly, "week_total": money(sum(spending(records(db, period_start("weekly")), db, period_start("weekly")).values())),
            "categories": [{"category": c, "amount": money(v)} for c, v in sorted(totals.items(), key=lambda pair: -pair[1])],
            "subscriptions_total": subscriptions["monthly_total"], "potential_savings": deals["potential_savings"],
            "upcoming_bills": [event for event in scheduled_events(db) if event["kind"] == "expense"],
            "budgets": budgets(db), "insights": insights(db),
            "recent_transactions": [{"id": t.id, "merchant": t.merchant, "date": t.date.isoformat(), "category": t.category,
                                     "amount": money(t.amount_cents), "kind": t.kind, "description": t.description, "source": t.source,
                                     "confidence": t.confidence} for t in sorted(month, key=lambda t: (t.date, t.id), reverse=True)[:5]]}
