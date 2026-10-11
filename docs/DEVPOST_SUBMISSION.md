# Moniq

**Spending, Made Smarter.** | Hacklanta 2026 | Fintech

## Inspiration and the problem

College life combines rent, tuition, financial aid, part-time pay, subscriptions and shared dinners on irregular schedules. A bank balance does not explain what is left after tomorrow's bills. Moniq helps students maintain a useful financial picture with less manual upkeep and clearer decisions.

## Target audience

College students managing their own money, especially students combining allowance, financial aid, payroll and roommate expenses. Our built-in Georgia State profile is fictional.

## What we built

A working React/TypeScript companion with a FastAPI backend, persistent local SQLite and a trained scikit-learn expense classifier. Nine responsive pages connect transactions, budgets, predictions, savings goals, subscriptions, offers, a grounded assistant and Moniq Circles.

The main dashboard surfaces financial-email approvals. Confirming a parsed synthetic $400 paycheck takes a $10 starting account to $410; confirming a $15 restaurant purchase takes it to $395. These are actual stored ledger calculations, not a chart animation.

## How it works

Money is stored as signed integer cents. A starting balance plus confirmed transactions maintains an estimated account balance. Checking and savings cash stay separate from outstanding credit debt. Debit-card last-four aliases map to a checking account without adding another account balance. Paired internal transfers and credit card payments are excluded from new income and spending. Reconciliation creates an immutable adjustment rather than rewriting history.

CSV statements support preview, column mapping, sign/date conventions, refunds, deduplication and atomic validation. User-pasted alerts remain available. Gmail is optional and requires explicit Google authorization before official Gmail API reads. Backend tokens are encrypted; the frontend receives no token or client secret. Email bodies are processed temporarily; extracted review fields remain in the local database. The recording uses server-owned synthetic email fixtures, never personal messages. Mocked Google responses test real OAuth/API code; they do not prove real-bank email coverage.

## Artificial intelligence and machine learning

TF-IDF features and logistic regression classify merchant descriptions across 11 categories. Confidence and manual category correction are visible; local retraining uses eligible corrections. The independent evaluation reproduced **250/264 correct, 94.70% raw synthetic accuracy and macro F1 0.943244** with 792 training rows and disjoint merchant families. At the 45% confidence threshold, 109 test rows require review; automatic coverage is 58.71%. These measurements apply to synthetic descriptions, not real-world financial emails. Probabilities are uncalibrated.

Financial math, forecasts, deal ranking and the assistant use deterministic calculations. The assistant is a local intent-based service, not an externally hosted language model. It answers supported questions with database evidence, including the last recorded paycheck, savings progress and roommate debt. Unsupported investment/tax/credit advice is declined.

## SmartApprove

Automation is off by default. Users define exact trusted senders, accounts, event types, per-transaction and daily limits. Provider authentication evidence must align; uncertain, conflicting, synthetic or incomplete alerts remain manual. Explicit posted status/date, account mapping, category confidence, deduplication and caps also gate approval. Append-only approval history preserves corrections and reversals. Only the explicitly selected isolated demonstration accepts a server-owned synthetic authentication fixture. Visible sender text alone never authorizes a real transaction.

## Moniq Circles

Create local circles and participants; split expenses equally, by custom amounts or percentages with exact-cent allocation. Link an existing bank charge and use only the personal share in budgets. A $40 dinner creates a $20 personal expense and $20 receivable. A confirmed $20 roommate repayment clears the debt without becoming a paycheck. Partial settlements, history, suggestions and shared-spending insights work. Moniq performs bookkeeping; it sends no money and has no live participant collaboration.

## Predictions, goals and student deals

The 30-day forecast combines historical variable cash spending and stored bills/income schedules, counting scheduled merchants once and showing its assumptions. What-if purchase, spending reduction, extra income and delay scenarios change estimates only. Savings goals record progress and contributions separately from account cash; monthly plans estimate completion dates without assuming deposits. Student offers are explicitly fictional samples, filtered by category and ranked against interests, spending and remaining budgets; they are not verified or redeemable deals.

## Challenges and what we learned

Correct accounting required separating bank cash, credit debt, personal expense allocations and reimbursements. Gmail required authorization-state protection, token encryption, conservative authentication evidence, and ambiguous-message review. Windows process/tooling and strict source scanning required isolated test/recording databases and portable tools. Tests caught sign/date/duplicate edge cases, subscription false positives, calendar renewals and mobile overflow. Confidence is not certainty, and readable financial assumptions matter as much as a model score.

## Future development

Bank reconciliation through a licensed provider, supported bank-specific email formats with real consented evaluation, authenticated persistent hosting, multi-user Circles, auditable settled-expense corrections and shared refunds, verified student-offer feeds, international statements, and independently reviewed accessibility/security. These are future work.

## Privacy and security limitations

This is a local-owner financial prototype, not production-certified financial software. Real Gmail and personal data remain loopback-only; public mode uses temporary isolated synthetic sessions and blocks personal uploads and free-form personal fields. SQLite and OS backups are not encrypted by Moniq, and tokens require protection of the local encryption key. Email identity evidence is conservative provider-reported evidence, not proof of a bank transaction. No real bank integration, money movement, enrollment verification or subscription cancellation is claimed.

## Technology and attribution

React, TypeScript, Vite, Tailwind CSS, Recharts, Lucide, Workbox, Python, FastAPI, SQLAlchemy, SQLite, scikit-learn, pandas, joblib, Authlib, cryptography, pytest, Ruff, ESLint, Playwright and GitHub Actions. The premium video uses FFmpeg and new Microsoft Edge neural narration; earlier preserved videos use Windows speech synthesis. Training, statements, offers, profiles and recorded emails are synthetic. Dependency/data/media attribution is in `ATTRIBUTIONS.md` and `data/LICENSE.md`.

## AI assistance and work-window disclosure

OpenAI Codex assisted implementation, design, debugging, tests, documentation and video production. The finalization extended the existing Moniq project and preserved its published baseline. The team must identify preexisting work and work completed during the official hacking period in `WORK_DISCLOSURE.md`; do not claim that all substantial work occurred during Hacklanta until verified. The rules prohibit presenting a previously completed project as new hackathon work.

## Links and submission instructions

Repository: https://github.com/ReddyR1105/Moniq (published baseline; final local commit awaits approval).

Premium video preparation: `docs/demo/Moniq_Hacklanta_Premium_Final.mp4`; preserved final video: `docs/demo/Moniq_Hacklanta_Final.mp4`; extended walkthrough: `docs/demo/Moniq_All_Features.mp4`. Complete the owner's premium listening review before public upload. Upload instructions and captions are in `DEMO_SCRIPT.md`. Public video URLs and any approved hosted demo URL must be entered by the team after upload/verification. Local testing is fully documented in the README; no deployment or Devpost receipt is claimed.

The web app now has a static-only PWA installation path and automated mobile touch coverage. Financial APIs remain online-only; native Android/iOS builds are future work. No actual cloud demo URL or APK is available yet. See `MOBILE_SETUP.md` and `PUBLIC_RELEASE_STATUS.md`.
