import calendar
import random
from datetime import date, timedelta

from sqlalchemy import delete, select

from .config import today
from .models import Account, Base, Budget, Deal, Goal, Profile, RecurringPayment, Transaction
from .transactions import fingerprint


def seed_demo(db, reset=False):
    if reset:
        for table in reversed(Base.metadata.sorted_tables):
            db.execute(delete(table))
        db.flush()
    if db.scalar(select(Profile.id)):
        return
    now = today()
    rng = random.Random(42)
    db.add(Profile(id=1))
    db.add(Account(id=1, opening_balance_cents=310000))
    db.flush()

    def transaction(day, merchant, amount, category, kind="expense"):
        value = abs(amount) * (-1 if kind == "expense" else 1)
        db.add(Transaction(date=day, merchant=merchant, description=merchant, amount_cents=value,
                           kind=kind, category=category, source="demo", fingerprint=fingerprint(day, merchant, value), confidence=None))

    for offset in range(90, -1, -1):
        day = now - timedelta(days=offset)
        if day.day == 1:
            transaction(day, "Family allowance", 60000, "income", "income")
            transaction(day, "Campus apartment rent", 72500, "rent")
        if day.day in (5, 19):
            transaction(day, "Campus job payroll", 62000, "income", "income")
        if day.day == 8:
            transaction(day, "Spotify premium", 599, "subscriptions")
        if day.day == 12:
            transaction(day, "Netflix subscription", 1549, "subscriptions")
        if day.day == 22:
            transaction(day, "Adobe membership", 1999, "subscriptions")
        if day.weekday() in (0, 2, 4):
            transaction(day, rng.choice(["Chick-fil-A restaurant", "Chipotle Mexican grill", "Starbucks coffee"]), rng.randint(850, 2100), "food")
        if day.weekday() == 6:
            transaction(day, "Kroger grocery", rng.randint(3200, 6500), "groceries")
        if day.weekday() == 1:
            transaction(day, "MARTA transit", 500, "transportation")
        if day.day == 16:
            transaction(day, "AMC cinema", 1850, "entertainment")
        if day.day == 24:
            transaction(day, "Target clothing", 4599, "shopping")
    transaction(now - timedelta(days=40), "Financial aid disbursement", 95000, "income", "income")
    transaction(now - timedelta(days=39), "GSU tuition", 80000, "education")
    transaction(now - timedelta(days=4), "University bookstore", 6800, "education")
    transaction(now - timedelta(days=3), "CVS pharmacy", 1650, "healthcare")
    transaction(now - timedelta(days=2), "Target clothing", 1500, "shopping", "refund")
    for category, limit in {"food": 18000, "groceries": 22000, "shopping": 7500, "transportation": 5000, "rent": 72500,
                            "education": 12000, "subscriptions": 4500, "entertainment": 6000, "healthcare": 3000, "miscellaneous": 3000}.items():
        db.add(Budget(category=category, limit_cents=limit, period="monthly"))
    db.add(Budget(category="food", limit_cents=4500, period="weekly"))
    for merchant, amount, category, due, kind in [
        ("Campus apartment rent", 72500, "rent", 1, "expense"),
        ("Family allowance", 60000, "income", 1, "income"),
        ("Campus job payroll", 62000, "income", 19, "income"),
    ]:
        year, month = now.year, now.month
        if due <= now.day:
            month += 1
            if month == 13:
                year, month = year + 1, 1
        next_due = date(year, month, min(due, calendar.monthrange(year, month)[1]))
        db.add(RecurringPayment(merchant=merchant, amount_cents=amount, category=category, kind=kind, next_due=next_due,
                                interval_days=14 if merchant == "Campus job payroll" else 30))
    db.add(Goal(name="Emergency fund", target_cents=150000, saved_cents=45000))
    deals = [
        ("Campus Coffee", "food", "Sample: 20% off your usual coffee", 500, 400, "Current student ID; illustrative offer"),
        ("StudyStream", "subscriptions", "Sample: student tier for an existing music subscription", 1199, 599, "Verified enrollment; illustrative offer"),
        ("Fresh Market", "groceries", "Sample: save $8 on a planned $40 grocery basket", 4000, 3200, "Student ID; illustrative offer"),
        ("Campus Transit", "transportation", "Sample: student monthly transit pass", 9500, 6800, "Full-time enrollment; illustrative offer"),
        ("NoteLab", "education", "Sample: discounted course study tools", 1200, 600, "University email; illustrative offer"),
        ("Tech Workshop", "shopping", "Sample: $60 off a planned laptop purchase", 60000, 54000, "Student verification; illustrative offer"),
        ("Cinema Club", "entertainment", "Sample: weekday student movie ticket", 1600, 1000, "Student ID; illustrative offer"),
        ("Campus Closet", "shopping", "Sample: 15% off planned clothing", 4000, 3400, "Student ID; illustrative offer"),
    ]
    for merchant, category, description, original, discounted, eligibility in deals:
        db.add(Deal(merchant=merchant, category=category, description=description, eligibility=eligibility,
                    original_cents=original, discounted_cents=discounted, expiration=None, source_url=None))
    db.commit()
