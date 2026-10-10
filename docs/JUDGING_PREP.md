# Moniq judging preparation

**What makes it different?** A complete local workflow connects a user-pasted purchase notification to a real saved transaction, an ML category, updated budgets, grounded answers, and a cash-flow estimate. Students review decisions rather than blindly accepting a model.

**What financial problem does it solve?** It reduces manual budget upkeep and helps students understand how everyday spending interacts with irregular income, rent, tuition, and recurring services.

**Who benefits?** College students and young adults; the demo is a synthetic Georgia State student. This is personal finance, not business bookkeeping.

**Why machine learning?** Merchant wording and bank descriptors vary. A text classifier learns reusable features and probabilities instead of requiring a rule for every merchant. Deterministic math handles money; ML supplies editable categorization, not financial arithmetic. Deal ranking and unusual-spending detection are transparent algorithms, not falsely labeled trained models.

**How is the classifier evaluated?** 1,056 synthetic labeled descriptions across 11 categories; 792 training and 264 test rows; merchant families disjoint across splits. The baseline measured 94.69697% raw accuracy. An independent fit from the saved CSV reproduced 250/264 correct and macro F1 0.943244. The 45% review threshold flags 109 rows; automatic coverage is 58.71%, and miscellaneous fallback accuracy is 63.64%. Full per-category metrics and errors are available. Formatting variants are correlated, probabilities are uncalibrated, and no real-bank accuracy is claimed.

**What prevents inaccurate advice?** All assistant values come from backend database calculations. Forecasts state their spending-history window and bill/income assumptions. Low-confidence categories are flagged; forecasts remain estimates. Unsupported investment, tax, and credit advice is declined by the local assistant.

**How is information protected?** This demo uses synthetic local data, loopback binding, restricted CORS/origin writes, validation, bounded CSV uploads, ORM queries, no frontend API keys, no-store responses, and export/deletion controls. It has no production identity system or encrypted SQLite and must not expose real records publicly. Deletion does not claim forensic disk erasure.

**What works now?** All eight screens, CSV import/deduplication, transaction CRUD/correction, notification parsing/confirmation, trained classification, budgets, bill/income schedules, forecasts/scenarios, ranked sample offers, subscription review, local assistant, profile/goals, export, deletion, and reset. See the acceptance audit and actual QA report.

**What requires production integration?** Live banking, consent-based external message import, verified deal feeds, real student verification, account authentication, cloud deployment/security, optional Gemini language explanations, and supported cancellation links. No integration is represented as working merely because its interface exists.

**What did the team build during Hacklanta?** Answer from `WORK_DISCLOSURE.md` after confirming the actual hacking window. The source and docs were AI-assisted in this session. Team identities/contributions and event eligibility are not known. Disclose any pre-window work explicitly; do not infer eligibility from the event date alone.
