# Synthetic data provenance

`sample_statement.csv`, `synthetic_training.csv`, `ml_evaluation.json`, seeded profile/transactions/goals/budgets, and sample offer descriptions were generated for Moniq. No real student or bank records were used. For reuse, the project authors dedicate their rights in the synthetic dataset contents to CC0 1.0 Universal: https://creativecommons.org/publicdomain/zero/1.0/

Merchant and university names remain references to their respective owners. The synthetic data license does not grant trademark rights, imply affiliation, or establish real student offer eligibility. Sample offers are not live or verified discounts.

The training-data generator, seed code, and evaluation method are in `backend/app/ml.py` and `backend/app/seed.py`. Generated model artifacts stay in ignored runtime storage. The baseline report contains actual predictions, not invented evaluation metrics.
