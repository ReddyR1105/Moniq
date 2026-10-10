"""Fit independently from the saved CSV; never import the application's classifier."""
import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.pipeline import Pipeline

ROOT = Path(__file__).resolve().parents[1]


def reproduce():
    frame = pd.read_csv(ROOT / "data/synthetic_training.csv")
    train = frame.loc[frame["split"] == "train"]
    test = frame.loc[frame["split"] == "test"]
    assert len(train) == 792 and len(test) == 264 and len(frame) == 1056
    assert not set(train.merchant_family) & set(test.merchant_family)
    assert not set(train.description) & set(test.description)
    model = Pipeline([
        ("tfidf", TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True, strip_accents="unicode")),
        ("logistic", LogisticRegression(C=8, max_iter=1000, random_state=42)),
    ])
    model.fit(train.description, train.category)
    predicted = model.predict(test.description)
    confidence = model.predict_proba(test.description).max(axis=1)
    review = confidence < 0.45
    fallback = np.where(review, "miscellaneous", predicted)
    labels = sorted(frame.category.unique())
    report = classification_report(test.category, predicted, output_dict=True, zero_division=0)
    baseline = json.loads((ROOT / "data/ml_evaluation.json").read_text(encoding="utf-8"))
    accuracy = float(accuracy_score(test.category, predicted))
    matrix = confusion_matrix(test.category, predicted, labels=labels).tolist()
    assert abs(accuracy - baseline["accuracy"]) < 1e-12, "Saved accuracy differs from independent fit"
    assert matrix == baseline["confusion_matrix"], "Saved confusion matrix differs"
    assert abs(report["macro avg"]["f1-score"] - baseline["classification_report"]["macro avg"]["f1-score"]) < 1e-12
    return {
        "method": "Independent fit from saved synthetic CSV; no application classifier import or joblib reuse",
        "training_rows": len(train), "test_rows": len(test), "merchant_families_disjoint": True,
        "raw_accuracy": accuracy, "raw_correct": int((predicted == test.category).sum()),
        "raw_macro_f1": report["macro avg"]["f1-score"],
        "raw_errors": int((predicted != test.category).sum()),
        "saved_baseline_matches": True, "classification_report": report, "confusion_matrix": matrix,
        "review_threshold": 0.45, "review_rows": int(review.sum()),
        "automatic_coverage": float((~review).mean()),
        "accuracy_after_miscellaneous_fallback": float(accuracy_score(test.category, fallback)),
        "automatic_only_accuracy": float(accuracy_score(test.category[~review], predicted[~review])) if (~review).any() else None,
        "limitations": "Synthetic English descriptions with correlated formatting variants. Not real-bank accuracy; confidence is uncalibrated. Corrections are excluded from this baseline.",
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="Verify saved independent report without rewriting it")
    args = parser.parse_args()
    result = reproduce()
    destination = ROOT / "data/ml_independent_evaluation.json"
    if args.check:
        saved = json.loads(destination.read_text(encoding="utf-8"))
        assert saved == result, "Independent evaluation changed; investigate before updating the report"
    else:
        destination.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k not in {"classification_report", "confusion_matrix"}}, indent=2))
