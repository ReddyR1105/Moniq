import re
from decimal import Decimal

from .finance import dashboard, deal_recommendations, forecast, insights
from .schemas import cents


def answer_question(db, question):
    q = question.lower()
    data = dashboard(db)
    evidence = {}
    if re.search(r"\b(stocks?|crypto|tax(?:es)?|invest(?:ment)?|credit score)\b", q):
        return {"answer": "Investment, tax, and credit advice are outside this prototype. Ask about your stored spending, rent, or a purchase amount.", "mode": "local", "evidence": {}}
    if re.search(r"\b(afford|purchase|buy)\b", q):
        amounts = re.findall(r"(?<![\w.])\$?(-?[\d,]+(?:\.\d+)?)(?![\w.])", q)
        if len(amounts) != 1:
            return {"answer": "Tell me the purchase amount, for example: Can I afford a $150 purchase?", "mode": "local", "evidence": {}}
        try:
            purchase_cents = cents(Decimal(amounts[0].replace(",", "")))
            if purchase_cents <= 0:
                raise ValueError("Purchase must be positive")
        except ValueError:
            return {"answer": "Use one positive amount up to $1,000,000 with at most two decimal places.", "mode": "local", "evidence": {}}
        value = purchase_cents / 100
        result = forecast(db, {"purchase_cents": purchase_cents})
        response = f"With a ${value:.2f} purchase tomorrow, your estimated 30-day balance is ${result['projected_balance']:.2f}; the lowest estimated balance is ${result['minimum_balance']:.2f}. "
        response += "This scenario predicts a cash shortfall. Consider delaying or reducing the purchase." if result["cash_shortfall"] else "No cash shortfall appears in this scenario, but keep a reserve for unexpected expenses."
        evidence = {"purchase": value, "projected_balance": result["projected_balance"], "minimum_balance": result["minimum_balance"]}
    elif "paycheck" in q or "payroll" in q:
        from .finance import records
        from sqlalchemy import select
        from .models import ApprovalAudit
        reversed_ids = set(db.scalars(select(ApprovalAudit.transaction_id).where(ApprovalAudit.action == "reversed")))
        paychecks = [t for t in records(db) if t.kind == "income" and t.amount_cents > 0 and t.id not in reversed_ids and re.search(r"payroll|paycheck|salary|wages", t.description + " " + t.merchant, re.I)]
        latest = max(paychecks, key=lambda t: (t.date, t.id), default=None)
        response = f"Your last recorded confirmed paycheck was ${latest.amount_cents/100:.2f} from {latest.merchant} on {latest.date.isoformat()}." if latest else "No confirmed paycheck is recorded. A future income schedule is not a deposited paycheck."
        evidence = {"last_paycheck": {"date": latest.date.isoformat(), "amount": latest.amount_cents / 100, "merchant": latest.merchant}} if latest else {"last_paycheck": None}
    elif "goal" in q:
        from .goals import goal_rows
        goals = goal_rows(db)
        response = " ".join(f"{g['name']}: ${g['saved']:.2f} recorded toward ${g['target']:.2f}. {g['recommendation']} " + (f"Estimated completion {g['projected_completion']}. " if g['projected_completion'] else "") for g in goals) if goals else "No savings goal is stored. Create one in Settings to track your progress."
        response += " Plans are estimates, not deposited money or a guarantee of being on track."
        evidence = {"goals": goals}
    elif any(word in q for word in ("shared", "roommate", "circle", "owe", "owed")):
        from .circles import summary
        shared = summary(db)
        usd = shared["currencies"].get("USD", {"receivable_cents": 0, "payable_cents": 0})
        response = f"Your local Circles show ${usd['receivable_cents']/100:.2f} owed to you and ${usd['payable_cents']/100:.2f} owed by you. Your own shared meals this month are ${shared['shared_meals_cents']/100:.2f}. Reserve ${shared['next_month_rent_reserve_cents']/100:.2f} for the next month of expenses marked as recurring shared rent. Outstanding repayments are never assumed to be cash or paycheck income. Other currencies stay separate."
        subscriptions = [r for r in shared["recurring"] if r["category"] == "subscriptions"]
        response += " Recurring shared subscriptions: " + ("; ".join(f"{r['title']}: your share {r['currency']} {r['own_share_cents']/100:.2f}" for r in subscriptions) if subscriptions else "none marked in your ledger.")
        response += f" Your budgets reflect ${data['expenses']:.2f} of total personal spending this month, including your shared allocations."
        evidence = shared
    elif "rent" in q:
        result = forecast(db)
        rent = next((e for e in result["events"] if e["category"] == "rent" and e["kind"] == "expense"), None)
        if rent:
            after = next(p["balance"] for p in result["timeline"] if p["date"] == rent["date"])
            response = f"Your stored rent payment is ${rent['amount']:.2f}, due {rent['date']}. Including other scheduled cash flows and estimated spending, your balance that day is about ${after:.2f}."
            evidence = {"rent": rent["amount"], "after_rent": after}
        else:
            response = "No upcoming rent payment is stored. Add a bill schedule before using an after-rent estimate."
    elif any(word in q for word in ("discount", "deal", "offer")):
        deals = deal_recommendations(db)["items"]
        response = "These are synthetic demonstration offers, not redeemable discounts. "
        response += " ".join(f"{d['merchant']}: ${d['savings']:.2f} potential savings on a planned purchase." for d in deals[:3]) if deals else "No sample offers currently match your eligibility and remaining budget."
        evidence = {"sample_deal_savings": [d["savings"] for d in deals[:3]]}
    elif "week" in q:
        response = f"You spent ${data['week_total']:.2f} net of refunds since Monday. The seven-day chart uses a rolling window, so it may differ from this calendar-week total."
        evidence = {"calendar_week_spending": data["week_total"]}
    elif any(word in q for word in ("increase", "recent", "changed")):
        changes = insights(db)["increases"]
        response = "Comparing the last 30 days with the preceding 30 days: "
        response += "; ".join(f"{r['category']} increased ${r['change']:.2f}" for r in changes[:3]) if changes else "no category increased by more than $10."
        evidence = {"increases": changes[:3]}
    elif any(word in q for word in ("wast", "sav", "cut", "reduce")):
        net = round(data["income"] - data["expenses"], 2)
        response = f"Your month-to-date income less personal spending is ${net:.2f}. Shared purchases use your own share; this differs from bank cash flow and is not a guaranteed month-end saving. " + " ".join(insights(db)["suggestions"][:2])
        evidence = {"monthly_income": data["income"], "monthly_net_expenses": data["expenses"], "net_cash_flow": net}
    elif "subscription" in q:
        response = f"Detected recurring services total about ${data['subscriptions_total']:.2f} per month. Review and confirm them on Subscriptions; marking a charge does not cancel it."
        evidence = {"subscriptions_monthly": data["subscriptions_total"]}
    elif any(word in q for word in ("balance", "left", "forecast", "budget", "spend", "money")):
        response = f"Your available balance is ${data['balance']:.2f}. Month-to-date net expenses are ${data['expenses']:.2f}, with ${data['remaining_budget']:.2f} of your category budgets remaining."
        evidence = {"balance": data["balance"], "expenses": data["expenses"], "remaining_budget": data["remaining_budget"]}
    else:
        response = "I can answer questions about stored spending, budgets, subscriptions, sample student deals, rent, and purchase affordability. Try 'How much did I spend this week?' Investment, tax, and credit advice are outside this prototype."
    return {"answer": response, "mode": "local", "evidence": evidence,
            "note": "Values come from stored records and deterministic calculations. Forecasts are estimates. No external model receives your records."}
