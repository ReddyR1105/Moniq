"""Conservative email extraction. An email never directly changes a balance."""
import base64
import re
from email.utils import parseaddr
from datetime import datetime
from decimal import Decimal, InvalidOperation
from html.parser import HTMLParser
from zoneinfo import ZoneInfo

from .config import today
from .ml import identify_merchant
from .transactions import parse_date


class VisibleText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.hidden = 0
        self.text = []

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style"}:
            self.hidden += 1
        elif tag in {"br", "p", "div", "tr", "li"}:
            self.text.append("\n")

    def handle_endtag(self, tag):
        if tag in {"script", "style"}:
            self.hidden = max(0, self.hidden - 1)

    def handle_data(self, data):
        if not self.hidden:
            self.text.append(data)


def email_text(message):
    plain, html = [], []
    remaining = 65536
    visited = 0

    def walk(part, depth=0):
        nonlocal remaining, visited
        visited += 1
        if depth > 10 or visited > 100 or remaining <= 0 or part.get("filename"):
            return
        mime = part.get("mimeType", "")
        encoded = part.get("body", {}).get("data", "")
        if mime in {"text/plain", "text/html"} and encoded and len(encoded) < 100000:
            try:
                raw = base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4))[:remaining]
                text = raw.decode("utf-8", errors="replace")
                remaining -= len(raw)
                if mime == "text/plain":
                    plain.append(text)
                else:
                    parser = VisibleText()
                    parser.feed(text)
                    html.append(" ".join(parser.text))
            except (ValueError, UnicodeError):
                pass
        for child in part.get("parts", [])[:100]:
            walk(child, depth + 1)

    walk(message.get("payload", {}))
    return "\n".join(plain or html) or message.get("snippet", "")[:2000]


def parse_financial_email(message, classifier):
    if set(message.get("labelIds", [])) & {"SPAM", "TRASH"}:
        return None
    headers = {v["name"].lower(): v.get("value", "") for v in message.get("payload", {}).get("headers", []) if "name" in v}
    subject = headers.get("subject", "")[:300]
    sender = headers.get("from", "")[:200]
    body = email_text(message)
    text = subject + "\n" + body
    lower = text.lower()
    if not re.search(r"\b(purchase|charged|payment|paid|deposit|paycheck|payroll|salary|refund|subscription|bill|receipt|renewal)\b", lower):
        return None
    if re.search(r"\b(discount|coupon|promotion|earn cashback)\b", lower) and not re.search(r"\b(charged|paid|deposited|refunded|posted)\b", lower):
        return None
    uncertain = []
    display_name = parseaddr(sender)[0]
    if re.search(r"\b(?:synthetic|simulated|demonstration|demo|test (?:alert|transaction|message))\b", text + "\n" + display_name, re.I):
        uncertain.append("Synthetic or test email: manual review only outside the isolated controlled scenario.")
    notice = bool(re.search(r"\b(due|upcoming|scheduled|pending|expected|estimated|will be|declined|failed|cancelled|canceled)\b", lower))
    if "refund" in lower or "refunded" in lower:
        event = "refund"
    elif re.search(r"\b(payroll|paycheck|salary|direct deposit|deposit)\b", lower):
        event = "income"
        if not re.search(r"\b(payroll|paycheck|salary|direct deposit)\b", lower):
            uncertain.append("Deposit source is not identified as a paycheck; verify that it is not an account transfer.")
        if not re.search(r"\b(confirmed|posted|credited|received|deposited|completed)\b", lower):
            uncertain.append("The email does not explicitly confirm that the deposit posted.")
    elif notice or ("bill" in lower and not re.search(r"\b(paid|charged|posted|completed)\b", lower)):
        event = "bill"
    elif re.search(r"\b(subscription|renewal|membership)\b", lower):
        event = "subscription"
    else:
        event = "purchase"
    if notice:
        uncertain.append("A pending, future, failed or due notification is not a posted cash flow.")
    if re.search(r"\b(transfer|card payment|payment received)\b", lower):
        uncertain.append("Possible account transfer or card payment; reconcile both accounts manually instead of treating it as new income or spending.")
    amounts = list(dict.fromkeys(re.findall(r"(?:\$|USD\s*)([\d,]+(?:\.\d+)?)", text, flags=re.I)))
    amount = None
    if len(amounts) == 1:
        try:
            value = Decimal(amounts[0].replace(",", ""))
            if value <= 0 or value > 1_000_000 or value != value.quantize(Decimal(".01")):
                raise ValueError()
            amount = int(value * 100)
        except (InvalidOperation, ValueError):
            uncertain.append("Invalid or unsupported amount; enter a verified USD amount.")
    else:
        uncertain.append("No single unambiguous USD amount; verify it manually.")
    if re.search(r"\b(?:CAD|AUD|EUR|GBP|JPY)\b|[\u20ac\u00a3\u00a5]", text, re.I):
        amount = None
        uncertain.append("Non-USD or mixed currencies require manual verification; no currency conversion is applied.")
    last_fours = set(re.findall(r"(?:ending(?:\s+in)?|last\s+four(?:\s+digits)?|[x*]{2,})\s*[:#]?\s*(\d{4})(?!\d)", text, flags=re.I))
    last_four = next(iter(last_fours)) if len(last_fours) == 1 else None
    if len(last_fours) > 1:
        uncertain.append("Multiple card/account suffixes; select the correct account.")
    try:
        day = datetime.fromtimestamp(int(message["internalDate"]) / 1000, ZoneInfo("America/New_York")).date()
    except (KeyError, ValueError, OverflowError, OSError):
        day = today()
        uncertain.append("Missing received date; verify the transaction date.")
    dates = set(re.findall(r"\b(?:\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{4})\b", body))
    if len(dates) == 1:
        try:
            day = parse_date(next(iter(dates)))
        except ValueError:
            uncertain.append("Invalid date in email; verify the received-date fallback.")
    elif dates:
        uncertain.append("Multiple email dates; verify which is the transaction date.")
    merchant_match = re.search(r"(?:\bat\b|\bfrom\b|merchant\s*:|payee\s*:|biller\s*:)\s+([A-Za-z][A-Za-z0-9 &'().-]{1,120}?)(?=\s+(?:on\s+\d|for\b|card\b|account\b|has been\b)|[.!\n]|$)", body, re.I)
    merchant = identify_merchant(merchant_match.group(1)) if merchant_match else "Unknown email merchant"
    if not merchant_match:
        uncertain.append("Merchant could not be extracted; enter the verified merchant.")
    prediction = classifier.classify(merchant)
    category = "income" if event == "income" else prediction["category"]
    if event != "income" and category == "income":
        category = "miscellaneous"
    if prediction["needs_review"]:
        uncertain.append("The ML category prediction needs review.")
    if day > today():
        uncertain.append("A future-dated email cannot be treated as a current posted transaction.")
    return {"subject": subject, "sender": sender, "event_type": event, "merchant": merchant[:160],
            "amount_cents": amount, "date": day, "last_four": last_four, "category": category,
            "confidence": prediction["confidence"], "reasons": uncertain}
