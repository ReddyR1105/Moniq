"""Local TF-IDF/logistic regression. Evaluation keeps merchant families disjoint."""
import json
import re
from pathlib import Path

import joblib
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.pipeline import Pipeline

from .config import MODEL_DIR, ROOT

MERCHANTS = {
    "food": ["Chick-fil-A restaurant", "Chipotle Mexican grill", "Starbucks coffee", "Panera cafe", "Campus dining", "Pizza Hut restaurant", "Local burger grill", "Peachtree coffee cafe"],
    "groceries": ["Kroger grocery", "Publix supermarket", "Aldi groceries", "Trader Joe's market", "Lidl food market", "Fresh grocery store", "Neighborhood supermarket", "Whole Foods grocery"],
    "shopping": ["Target clothing", "Amazon retail", "Walmart shopping", "H&M apparel", "Nike shoes", "Campus clothing store", "Downtown apparel", "Online shoe store"],
    "transportation": ["MARTA transit", "Uber ride", "Lyft trip", "Shell fuel", "Campus parking", "Chevron gas", "City transit pass", "Airport taxi ride"],
    "rent": ["Campus apartment rent", "Student housing lease", "Peachtree rental", "University housing rent", "Downtown apartment lease", "Monthly housing payment", "Parkside rental apartment", "Oak Street housing lease"],
    "education": ["GSU tuition", "University bookstore", "Pearson textbook", "Coursera course", "Campus lab fee", "College course supplies", "Academic textbook store", "Student tuition payment"],
    "subscriptions": ["Spotify premium", "Netflix subscription", "Adobe membership", "Apple music", "YouTube premium", "Notion monthly subscription", "Streaming service membership", "Cloud monthly subscription"],
    "entertainment": ["AMC cinema", "Regal movie theater", "Bowling game", "Concert ticket", "Museum admission", "Arcade games", "Live music ticket", "City cinema admission"],
    "healthcare": ["CVS pharmacy", "Walgreens prescription", "Student health clinic", "Dental appointment", "Medical copay", "Urgent care clinic", "Local pharmacy prescription", "Campus medical visit"],
    "income": ["Campus job payroll", "Family allowance", "Scholarship deposit", "Financial aid disbursement", "Tutoring wages", "Part-time salary", "Student job paycheck", "Monthly allowance deposit"],
    "miscellaneous": ["Post office stamps", "Laundry service", "Bank service fee", "Charity donation", "Document notary", "Storage locker fee", "Parcel postage", "Coin laundry wash"],
}


def synthetic_data():
    rows = []
    prefixes = ["", "POS ", "DEBIT CARD ", "ACH ", "ONLINE PAYMENT ", "CARD PURCHASE "]
    suffixes = [" ATLANTA GA", " #104", " GSU", " MOBILE", " 2026", ""]
    for category, merchants in MERCHANTS.items():
        for index, merchant in enumerate(merchants):
            for variant in range(12):
                rows.append({
                    "description": f"{prefixes[variant % 6]}{merchant}{suffixes[(variant // 2) % 6]}",
                    "category": category, "merchant_family": merchant,
                    "split": "test" if index >= 6 else "train",
                })
    return pd.DataFrame(rows)


class Classifier:
    def __init__(self, model_dir: Path = MODEL_DIR):
        self.model_dir = model_dir
        self.model_dir.mkdir(parents=True, exist_ok=True)
        self.path = self.model_dir / "classifier.joblib"
        self.report_path = self.model_dir / "evaluation.json"
        if self.path.exists() and self.report_path.exists():
            self.pipeline = joblib.load(self.path)
            self.report = json.loads(self.report_path.read_text(encoding="utf-8"))
        else:
            self.train()

    def train(self, corrections=()):
        frame = synthetic_data()
        train, test = frame[frame.split == "train"], frame[frame.split == "test"]
        pipeline = Pipeline([
            ("tfidf", TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True, strip_accents="unicode")),
            ("logistic", LogisticRegression(max_iter=1000, C=8, random_state=42)),
        ])
        descriptions, labels = train.description.tolist(), train.category.tolist()
        # A correction resembling a held-out merchant is excluded from evaluation training.
        held_out = {merchant.lower() for merchant in test.merchant_family}
        used = 0
        for correction in corrections:
            if not any(merchant in correction.description.lower() for merchant in held_out):
                descriptions.append(correction.description)
                labels.append(correction.corrected_category)
                used += 1
        pipeline.fit(descriptions, labels)
        predictions = pipeline.predict(test.description)
        probabilities = pipeline.predict_proba(test.description).max(axis=1)
        errors = [
            {"description": str(row.description), "expected": str(row.category),
             "predicted": str(predicted), "confidence": round(float(confidence), 4)}
            for row, predicted, confidence in zip(test.itertuples(), predictions, probabilities)
            if row.category != predicted
        ]
        self.report = {
            "accuracy": float(accuracy_score(test.category, predictions)),
            "classification_report": classification_report(test.category, predictions, output_dict=True, zero_division=0),
            "confusion_matrix": confusion_matrix(test.category, predictions, labels=sorted(MERCHANTS)).tolist(),
            "labels": sorted(MERCHANTS), "training_rows": len(descriptions), "test_rows": len(test),
            "corrections_used": used, "representative_errors": errors[:12],
            "split": "Six merchant families per category train; two unseen families per category test. Fixed seed 42.",
            "limitations": "Synthetic English descriptions only. Repeated formatting variants are correlated. This measures synthetic merchant generalization, not real banking accuracy. Probabilities are uncalibrated. Ambiguous merchants and novel wording need review.",
        }
        # Swap only a fully fitted model; prediction requests can continue during training.
        self.pipeline = pipeline
        joblib.dump(self.pipeline, self.path)
        self.report_path.write_text(json.dumps(self.report, indent=2), encoding="utf-8")
        return self.report

    def classify(self, description: str):
        probabilities = self.pipeline.predict_proba([description])[0]
        index = int(probabilities.argmax())
        predicted = str(self.pipeline.classes_[index])
        confidence = float(probabilities[index])
        uncertain = confidence < 0.45
        return {
            "category": "miscellaneous" if uncertain else predicted,
            "predicted_category": predicted, "confidence": round(confidence, 4),
            "needs_review": uncertain,
            "explanation": "Low model confidence; assigned miscellaneous for your review." if uncertain else "TF-IDF description features classified by logistic regression. Review and correct when needed.",
        }


def identify_merchant(description: str):
    cleaned = re.sub(r"^(POS|DEBIT CARD|CARD PURCHASE|ONLINE PAYMENT|ACH)\s+", "", description.strip(), flags=re.I)
    cleaned = re.sub(r"\s+(ATLANTA GA|#\d+|MOBILE|\d{4})$", "", cleaned, flags=re.I)
    return cleaned[:160] or "Unknown merchant"


if __name__ == "__main__":
    classifier = Classifier()
    report = classifier.train()
    synthetic_data().to_csv(ROOT / "data" / "synthetic_training.csv", index=False)
    (ROOT / "data" / "ml_evaluation.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"accuracy": report["accuracy"], "test_rows": report["test_rows"], "errors": report["representative_errors"]}, indent=2))
