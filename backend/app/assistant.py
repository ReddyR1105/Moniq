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
        response = f"Your month-to-date income less net expenses is ${net:.2f}. This is a current cash-flow measure, not a guaranteed month-end saving. " + " ".join(insights(db)["suggestions"][:2])
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
