import csv
import hashlib
import io
import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

import pandas as pd
from sqlalchemy import select

from .ml import identify_merchant
from .models import Account, Correction, Notification, Transaction
from .schemas import TransactionIn, cents

MAX_CSV_BYTES = 2 * 1024 * 1024
MAX_CSV_ROWS = 10000


def fingerprint(day, merchant, amount_cents):
    canonical = re.sub(r"\s+", " ", merchant.strip().casefold())
    return hashlib.sha256(f"{day}|{canonical}|{amount_cents}".encode()).hexdigest()


def serialize_transaction(row):
    return {"id": row.id, "date": row.date.isoformat(), "description": row.description,
            "merchant": row.merchant, "amount": row.amount_cents / 100, "kind": row.kind,
            "category": row.category, "confidence": row.confidence, "source": row.source}


def prepare_transaction(payload: TransactionIn, classifier, source="manual"):
    prediction = classifier.classify(payload.description)
    amount = abs(cents(payload.amount)) * (-1 if payload.kind == "expense" else 1)
    category = "income" if payload.kind == "income" else (payload.category.value if payload.category else prediction["category"])
    if category == "income" and payload.kind != "income":
        category = "miscellaneous"
    merchant = payload.merchant or identify_merchant(payload.description)
    return {"date": payload.date, "description": payload.description, "merchant": merchant,
            "amount_cents": amount, "kind": payload.kind, "category": category,
            "confidence": prediction["confidence"], "source": source,
            "fingerprint": fingerprint(payload.date, merchant, amount)}


def add_transaction(db, payload, classifier, source="manual"):
    values = prepare_transaction(payload, classifier, source)
    if db.scalar(select(Transaction.id).where(Transaction.fingerprint == values["fingerprint"])):
        return None
    if not db.get(Account, 1):
        db.add(Account(id=1, opening_balance_cents=0))
        db.flush()
    row = Transaction(**values)
    db.add(row)
    db.flush()
    if payload.category and payload.kind != "income":
        prediction = classifier.classify(payload.description)
        if prediction["category"] != payload.category.value:
            db.add(Correction(description=payload.description, previous_category=prediction["category"], corrected_category=payload.category.value))
    if payload.notification_text:
        db.add(Notification(text=payload.notification_text, transaction_id=row.id))
    return row


def read_csv(content: bytes, filename: str):
    if not filename.lower().endswith(".csv"):
        raise ValueError("Choose a .csv file.")
    if len(content) > MAX_CSV_BYTES:
        raise ValueError("CSV exceeds the 2 MB limit.")
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError("CSV must use UTF-8 encoding.") from exc
    if "\x00" in text:
        raise ValueError("CSV contains unsupported binary content.")
    try:
        frame = pd.read_csv(io.StringIO(text), sep=None, engine="python", dtype=str, keep_default_na=False, nrows=MAX_CSV_ROWS + 1)
    except (csv.Error, pd.errors.ParserError, pd.errors.EmptyDataError, ValueError) as exc:
        raise ValueError("Unable to read CSV. Check the delimiter and header row.") from exc
    if len(frame) > MAX_CSV_ROWS or len(frame.columns) > 50:
        raise ValueError("CSV may contain at most 10,000 rows and 50 columns.")
    if frame.empty:
        raise ValueError("CSV has no transaction rows.")
    return frame


def parse_money(value):
    raw = str(value).strip()
    if not raw:
        return Decimal(0)
    negative = raw.startswith("(") and raw.endswith(")") or raw.upper().endswith("DR")
    raw = re.sub(r"(?:USD|CR|DR)", "", raw, flags=re.I)
    raw = raw.replace("$", "").replace(",", "").replace("(", "").replace(")", "").strip()
    try:
        amount = Decimal(raw)
        cents(amount)
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"Invalid currency amount: {value!s}") from exc
    return -abs(amount) if negative else amount


def parse_date(value, day_first=False):
    raw = str(value).strip()
    try:
        return date.fromisoformat(raw[:10])
    except ValueError:
        pass
    formats = ["%d/%m/%Y", "%d/%m/%y", "%d-%m-%Y"] if day_first else ["%m/%d/%Y", "%m/%d/%y", "%m-%d-%Y"]
    formats += ["%b %d, %Y", "%B %d, %Y", "%Y/%m/%d"]
    for fmt in formats:
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    raise ValueError("Unsupported date. Use ISO, US/UK numeric dates, or 'Oct 9, 2026'.")


def csv_payloads(frame, mapping, convention, day_first=False):
    if convention not in {"negative_expense", "positive_expense"}:
        raise ValueError("Choose a valid amount convention.")
    if not isinstance(mapping, dict) or not mapping.get("date") or not mapping.get("description"):
        raise ValueError("Map the date and description columns.")
    if not mapping.get("amount") and not (mapping.get("debit") and mapping.get("credit")):
        raise ValueError("Map an amount column or both debit and credit columns.")
    if any(value not in frame.columns for value in mapping.values() if value):
        raise ValueError("Mapped column does not exist in this CSV.")
    payloads = []
    for index, row in frame.iterrows():
        try:
            if mapping.get("amount"):
                amount = parse_money(row[mapping["amount"]])
                if convention == "positive_expense":
                    amount = -amount
            else:
                debit = abs(parse_money(row[mapping["debit"]]))
                credit = abs(parse_money(row[mapping["credit"]]))
                if debit and credit:
                    raise ValueError("A row cannot have both debit and credit amounts.")
                amount = credit - debit
            kind = "expense" if amount < 0 else "income"
            if mapping.get("kind"):
                raw_kind = row[mapping["kind"]].strip().lower()
                aliases = {"debit": "expense", "credit": "income", "refund": "refund", "expense": "expense", "income": "income"}
                if raw_kind not in aliases:
                    raise ValueError("Type must be expense, income, refund, debit or credit.")
                kind = aliases[raw_kind]
            category = row[mapping["category"]].strip().lower() if mapping.get("category") else None
            payloads.append(TransactionIn(date=parse_date(row[mapping["date"]], day_first), description=row[mapping["description"]], amount=amount, kind=kind, category=category or None))
        except (ValueError, TypeError, KeyError) as exc:
            raise ValueError(f"Row {index + 2}: {exc}") from exc
    return payloads
