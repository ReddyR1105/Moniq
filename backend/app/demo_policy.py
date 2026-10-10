"""Public visitors can change only fictional values and allowlisted sample text."""
import csv
import re

from fastapi import HTTPException

from .config import ROOT, today
from .ml import MERCHANTS
from .notifications import EXAMPLES

ASSISTANT_QUESTIONS = [
    "When was my last confirmed paycheck?", "How much money do I have left?", "Am I on track with my savings goal?", "Can I afford a $100 purchase?",
    "How much do my roommates owe me?", "How much have I spent on shared meals?", "What shared subscriptions are recurring?", "How much should I reserve for shared rent?", "Which shared expenses affect my budget?",
    "How much did I spend this week?", "Can I afford a $150 purchase?",
    "How much will I have left after rent?", "Where can I save money?",
    "Which expenses increased recently?", "Which student deals are relevant to me?",
    "Which subscriptions am I paying for?", "How much should I save this month?",
    "Which student deals match my spending?", "Which stock should I invest in?",
]
SCHEDULE_MERCHANTS = ["Campus apartment rent", "Family allowance", "Campus job payroll", "One-time tuition payment",
                      "Meal plan", "Scholarship deposit", "Tutoring wages"]
UNIVERSITIES = ["Georgia State University", "Georgia Tech", "Emory University", "Other synthetic university"]
INTERESTS = {"food", "groceries", "shopping", "technology", "education", "transportation", "entertainment", "clothing", "restaurants"}


def sample_messages():
    return [EXAMPLES[0], f"Purchase of $42.60 at Kroger grocery on {today().isoformat()}.", *EXAMPLES[2:]]


def require_sample(condition):
    if not condition:
        raise HTTPException(403, "Public demo accepts only built-in synthetic samples. Use local mode for custom input; never enter personal banking data here.")


def descriptions():
    result = {merchant for group in MERCHANTS.values() for merchant in group}
    result.update({"Chick-fil-A", "Unknown synthetic demo purchase", "Sample campus coffee"})
    with (ROOT / "data/sample_statement.csv").open(encoding="utf-8") as source:
        result.update(row["Description"] for row in csv.DictReader(source))
    return result


def check_transaction(payload):
    allowed = descriptions()
    require_sample(payload.account_id == 1 and payload.description in allowed and (not payload.merchant or payload.merchant in allowed))
    require_sample(not payload.notification_text or payload.notification_text in sample_messages())


def check_profile(payload):
    require_sample(payload.name == "Alex Morgan" and payload.university in UNIVERSITIES)
    require_sample(payload.academic_year in {"Freshman", "Sophomore", "Junior", "Senior", "Graduate"})
    require_sample(payload.income_preference in {"Part-time employment", "Family allowance", "Scholarships / financial aid", "Mixed income"})
    require_sample({v.strip().lower() for v in payload.interests.split(",") if v.strip()} <= INTERESTS)


def check_question(question):
    require_sample(question.strip().lower() in {q.lower() for q in ASSISTANT_QUESTIONS}
                   or bool(re.fullmatch(r"can i afford a?\s*\$\d+(?:\.\d{1,2})? purchase\?", question.strip(), re.I)))
