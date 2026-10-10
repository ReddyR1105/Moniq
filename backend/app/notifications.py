import re
from decimal import Decimal

from .config import today
from .ml import identify_merchant
from .transactions import parse_date

EXAMPLES = [
    "Your card ending in 1234 was charged $15.75 at Chick-fil-A.",
    "Purchase of $42.60 at Kroger grocery on 10/09/2026.",
    "Refund of $15.00 from Target clothing.",
    "Payroll deposit of $620.00 from Campus job payroll.",
]


def parse_message(text, classifier):
    matches = re.findall(r"(?:\$|USD\s*)([\d,]+(?:\.\d{1,2})?)", text, flags=re.I)
    if len(matches) != 1:
        raise ValueError("Message must contain one unambiguous dollar amount. Edit the text or enter the transaction manually.")
    amount = Decimal(matches[0].replace(",", ""))
    if not amount.is_finite() or amount <= 0 or amount > 1_000_000:
        raise ValueError("Message amount must be between $0.01 and $1,000,000.")
    lower = text.lower()
    kind = "refund" if re.search(r"\b(refund|refunded|reversal)\b", lower) else "income" if re.search(r"\b(payroll|deposit|salary|allowance|wages)\b", lower) else "expense"
    merchant_match = re.search(r"\b(?:at|from|to)\s+(.+?)(?=\s+on\s+\d|[.!\n]|$)", text, flags=re.I)
    if not merchant_match:
        raise ValueError("Could not identify a merchant. Try 'charged $15.75 at Chick-fil-A'.")
    merchant = identify_merchant(merchant_match.group(1))
    date_match = re.search(r"\b(\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{2,4})\b", text)
    day = parse_date(date_match.group(1)) if date_match else today()
    prediction = classifier.classify(merchant)
    category = "income" if kind == "income" else prediction["category"]
    if kind != "income" and category == "income":
        category = "miscellaneous"
    return {"merchant": merchant, "description": merchant, "amount": float(amount), "kind": kind,
            "date": day.isoformat(), "category": category, "confidence": prediction["confidence"],
            "needs_review": prediction["needs_review"], "explanation": prediction["explanation"],
            "date_assumption": "Date found in message (US month/day convention)." if date_match else "No date provided; using today in America/New_York.",
            "notification_text": text}
