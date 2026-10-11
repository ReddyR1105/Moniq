# Moniq

**Spending, Made Smarter.**

Moniq is a working financial companion for college students. It replaces manual spreadsheet upkeep with statement imports, purchase-alert extraction, a trained transaction classifier, editable budgets, and understandable cash-flow estimates. The default synthetic student attends Georgia State University. Primary Hacklanta 2026 track: **Fintech**; AI/ML is a technology focus, not a claimed additional track.

## What works

- Nine responsive pages: Overview, Transactions, Budgets, AI Insights, Student Deals, Subscriptions, Circles, AI Assistant, and Settings.
- Database-derived balances, income, net expenses, budgets, seven-day/category charts, upcoming bills, subscriptions, savings suggestions, and recent transactions.
- Transaction creation, editing, deletion, search, category/type/date filters, pagination, and category corrections.
- UTF-8 CSV preview and column mapping; signed amounts or separate debit/credit columns; US/UK and ISO dates; refunds via a type column; deduplication; atomic validation.
- User-pasted alerts and a live sample-alert simulator, with editable confirmation before any database write.
- Optional local Gmail read-only OAuth connection, encrypted backend tokens, registered personal accounts, and a confirmed financial-email review queue. [Exact Google setup and local testing](docs/GMAIL_SETUP.md).
- Pending financial-email approvals on the main dashboard. The isolated scenario demonstrates $10 + $400 confirmed paycheck - $15 purchase = $395 using actual parsed fields and database records.
- Checking and savings, linked debit-card aliases, separate credit debt, internal transfers/card payments, and auditable manual reconciliation. Transfers and reimbursements never become new paycheck income or spending.
- Multiple savings goals, contribution history, monthly contribution plans and estimated completion dates. Progress records and forecasts never move money or create bank deposits.
- **Moniq Circles:** original local expense sharing with equal/custom/percentage splits, linked cash transactions, partial repayments, and personal-share budgets.
- **SmartApprove:** optional trusted-sender settings, strict sender/authentication/posted-event/account/limit policy, estimates, and auditable corrections/reversals.
- [Feature decisions, accounting invariants, security limitations and isolated walkthrough](docs/CIRCLES_SMARTAPPROVE.md); [latest upgrade verification](docs/UPGRADE_QA.md). Google consent remains a local owner step; no real Gmail reads are claimed by synthetic tests.
- Actual scikit-learn TF-IDF/logistic regression, saved locally, with prediction confidence, uncertain-description fallback, correction storage, retraining, and measured held-out results.
- Independent weekly/monthly category budgets, overspending alerts, unusual spending flags, and financial goals.
- A 30-day deterministic forecast, editable one-time/recurring bill and income schedules, and numerical purchase/spending/income/delay scenarios.
- Synthetic sample offers ranked by spending, interests, eligibility, savings, and remaining budget. Browser bookmarks work; offers are not redeemable.
- Monthly subscription candidates inferred from transaction history, renewal estimates, annualized costs, and persistent confirmation/dismissal.
- A local financial assistant that answers supported questions using calculated database values, with evidence shown in the UI.
- Editable profile, allowance schedule, in-app alert preference, JSON/CSV export, persistent data deletion, and demo reset.
- Guided demo, loading/error/empty states, native keyboard-accessible dialogs, reduced-motion support, and PWA-ready manifest/icons.

## Run on this Windows workspace

The app lives in **`D:\Map\Moniq`**. Dependencies have been installed in `.venv` and `frontend/node_modules`. A project-local official Node.js 24 LTS runtime is in ignored `.tools`; launch scripts use it automatically.

Open two PowerShell terminals:

```powershell
# Terminal 1 — backend
cd D:\Map\Moniq
powershell -ExecutionPolicy Bypass -File .\scripts\start-backend.ps1
```

```powershell
# Terminal 2 — frontend
cd D:\Map\Moniq
powershell -ExecutionPolicy Bypass -File .\scripts\start-frontend.ps1
```

Open **http://127.0.0.1:5173**. API health: http://127.0.0.1:8000/api/health. Interactive endpoint documentation: http://127.0.0.1:8000/docs. Startup creates SQLite tables, trains/loads the classifier, and seeds the demo once. Changes persist after restarting. Stop servers with Ctrl+C.

## Production demo on one local origin

```powershell
cd D:\Map\Moniq
powershell -ExecutionPolicy Bypass -File .\scripts\start-public-demo.ps1
```

Open **http://127.0.0.1:8080**. Each browser profile gets an isolated temporary synthetic session; personal uploads and free-form personal text are blocked. Separate private browser contexts can test independently. Reset and export affect only the current session. Public predictions use an immutable baseline. This preserves full custom input and retraining in local mode. Sessions expire or disappear after server restart. See [hosting preparation and limitations](docs/DEPLOYMENT.md).

## Fresh checkout installation

Prerequisites: Python 3.12–3.14, Node.js 22.12+ or 24 LTS, npm, and Git. Python 3.14.7 and Node 24.21.0 were used in this workspace. Node/Python binaries and installed dependencies are not part of the repository.

```powershell
cd Moniq
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements-lock.txt
cd frontend
npm ci
cd ..
```

Alternatively run `powershell -ExecutionPolicy Bypass -File .\scripts\setup.ps1` after installing Python and Node. Start using the commands above, substituting your checkout path. The Python lock file records the exact validated packages; `requirements.txt` records allowed dependency ranges.

On macOS/Linux:

```bash
cd Moniq
python3 -m venv .venv
.venv/bin/python -m pip install -r backend/requirements-lock.txt
npm --prefix frontend ci
# Run in one terminal, from the repository root:
.venv/bin/python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
# Run in another terminal:
npm --prefix frontend run dev
```

You may copy `.env.example` to `.env` for local overrides. No API credentials are needed. Paths in relative `DATABASE_URL` and `MODEL_DIR` settings are relative to the repository-root launch directory. Never put secrets in frontend variables or commit `.env`.

## Architecture

```text
frontend/                 React + TypeScript + Vite + Tailwind
  src/pages/              Nine working screens
  src/api.ts              API client and cancellable data fetching
  src/dialogs.tsx         Purchase confirmation and CSV mapping
  src/ScheduleManager.tsx Upcoming bills and income controls
  e2e/                    Browser acceptance tests
backend/
  app/main.py             FastAPI schemas, routes, lifecycle, privacy headers
  app/models.py           SQLAlchemy database models
  app/transactions.py     Exact-cent normalization, CSV parsing, deduplication
  app/ml.py               Synthetic data generator, model training/evaluation
  app/finance.py          Budgets, forecasts, subscriptions, deals, insights
  app/notifications.py    User-initiated purchase-alert extraction
  app/assistant.py        Local questions grounded in calculated evidence
  app/integrations.py     Provider boundaries; optional local Gmail integration
  app/seed.py             Reproducible rolling 90-day student history
data/                     Synthetic CSV, model evaluation, data-license notes
tests/                    Backend calculation, persistence, API/security tests
docs/                     Submission drafts, audit, demo, judging, QA, architecture
scripts/                  Setup, frontend/backend launch, checks
.runtime/                 Ignored SQLite databases and trained model artifacts
.tools/, .venv/           Ignored local tools/dependencies
```

The browser talks to `/api` through Vite's local proxy. FastAPI reads SQLite through SQLAlchemy and runs local ML/financial services. React refreshes dashboard and page data after successful writes. No paid service is required. Recharts supplies interactive chart tooltips; Lucide supplies icons.

## Financial conventions

Amounts are integer cents in the database. Expenses are negative; income and refunds are positive. API transaction input uses an explicit type and normalizes the magnitude accordingly, even when a supplied amount is negative. Refunds reduce spending in their original category; they are not treated as income. Current totals include posted records dated through today in America/New_York; future transactions do not inflate the current balance. Balances equal opening account balance plus stored cash flows.

Budgets are category limits, not bank balances. Weeks start Monday. Weekly and monthly limits are independent; only monthly limits contribute to the dashboard's monthly plan. The rolling seven-day chart is labeled separately from calendar-week spending. Savings goals track progress without reserving or moving funds.

The forecast uses up to 60 days of observed spending, net of refunds, excluding scheduled merchants so bills are not counted twice. It spreads estimated variable spending over 30 days and applies known income/bills on their dates. Monthly schedules follow calendar months with day clamping; other schedules use day intervals; one-time payments appear once. Candidate subscriptions are included until dismissed. Purchase scenarios change only estimates, never stored transactions. Spending reductions cannot exceed forecast variable spending; a purchase delayed beyond 30 days is deferred, not saved.

## Machine learning

`python -m backend.app.ml` generates 1,056 labeled synthetic English descriptions across 11 categories, trains on 792 rows, and evaluates on 264 rows. Six merchant families per category train; two separate families test. Formatting variants for a merchant stay together. TF-IDF word uni/bigrams feed logistic regression. The model is a local joblib artifact, regenerated from code when missing. Never load joblib files from an untrusted source.

The baseline measured **94.69697% raw held-out synthetic accuracy**. Full precision, recall, F1, confusion matrix, and representative errors are in `data/ml_evaluation.json` and the AI Insights screen. This is not measured real-bank performance. Formatting variants are correlated and the synthetic descriptions often contain useful semantic words. Confidence values are uncalibrated; under 45% the app assigns miscellaneous and asks for review. Raw evaluation accuracy describes the classifier before this fallback.

Corrections are saved in SQLite and can be included through **Retrain with corrections**. Corrections matching a held-out merchant family are excluded from evaluation training. Demo reset/data deletion clear correction influence by retraining the baseline. Representative failures include ambiguous streaming membership and unfamiliar postage descriptions.

To regenerate data and the report on Windows:

```powershell
.\.venv\Scripts\python.exe -m backend.app.ml
```

## Judge walkthrough

1. Open Moniq; click **Start Demo** for the eight-step tour.
2. Note the balance and month-to-date expenses.
3. **Try purchase alert → Simulate a purchase alert** extracts the Chick-fil-A $15.75 expense and classifies Food.
4. Review/edit the fields, then **Confirm & save transaction**. Overview and Budgets refresh.
5. Open AI Assistant and ask **How much did I spend this week?** Inspect the calculated evidence.
6. Open AI Insights and run the $150 purchase scenario. Its 30-day balance difference is exactly −$150.
7. Open Student Deals; explain why a ranked synthetic grocery/coffee/service offer fits a planned purchase and remaining budget.
8. Confirm/dismiss a detected subscription; use **Settings → Reset Demo** before another walkthrough.

Optional: import `data/sample_statement.csv` with the auto-suggested mapping. The file includes expense, income, and refund examples; a second import skips duplicates. For the most repeatable video, reset the demo first and avoid importing this CSV before the main walkthrough.

## Validation

```powershell
cd D:\Map\Moniq
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check backend tests
# With Node/npm on PATH:
npm --prefix frontend run typecheck
npm --prefix frontend run lint
npm --prefix frontend run build
```

`scripts/check.ps1` locates the project-local Node runtime when present and runs these checks. Browser tests start their own isolated synthetic database/backend (8001) and frontend (5174):

```powershell
# With Node/npm on PATH (Windows uses installed Edge by default):
npm --prefix frontend run test:e2e
```

Windows defaults to installed Microsoft Edge; other platforms and CI use Chromium. To run the CI browser locally, install Chromium with `npx playwright install chromium` from `frontend`, set `$env:MONIQ_BROWSER='chromium'`, and run the same test command. A custom `PLAYWRIGHT_BROWSERS_PATH` must match at installation and execution. Browser tests use synthetic services on 8001/5174. `scripts/check.ps1 -Browser` includes them and production public-session tests on port 8003. Run `npm --prefix frontend run test:public` after a production build to check that mode separately. See [QA report](docs/QA_REPORT.md) for actual results and limits.

`.github/workflows/ci.yml` runs these checks on pushes and pull requests with Python 3.14, Node 24, locked dependencies and Chromium. Official actions are pinned to verified commit IDs. actionlint passes locally; actual GitHub Actions execution is pending an approved push.

Independently verify the baseline from the saved CSV without importing the application model:

```powershell
.\.venv\Scripts\python.exe scripts\reproduce_ml.py --check
```

The independent fit reproduced **250/264 correct**, raw macro F1 **0.943244**. The review threshold flags **109/264** rows (automatic coverage **58.71%**); applying the app's miscellaneous fallback yields **63.64%** accuracy on this synthetic set. Accepted predictions were 155/155 correct on this set only. These separate figures describe a conservative review policy, not validated real-world accuracy. Full results are in [independent evaluation](data/ml_independent_evaluation.json).

## Privacy and limits

Default local mode is a **single-user, persistent prototype**. Public demo mode uses separate temporary synthetic databases and backend-enforced sample-only inputs. Keep the backend bound to `127.0.0.1`; do not expose real financial records through public unauthenticated endpoints. CORS is restricted to the local frontend; disallowed Origin headers are rejected on writes. Validation restricts amounts and text; CSV inputs are limited to 2 MB, 10,000 rows, and 50 columns; exported text is escaped against spreadsheet formulas. Queries use SQLAlchemy, not LLM-generated SQL. API responses are marked no-store. SQLite is not encrypted. Deletion is logical database deletion, not a promise of forensic disk erasure or removal from prior exports/backups. Routine logs show endpoint metadata, not transaction contents.

Plaid Sandbox and Gemini are **not implemented**; provider interfaces are documented for later use. No SMS/iMessage access, supported cancellation integration, live discount feed, real student verification, push notifications, account authentication, or an actual cloud deployment is included. The local assistant supports specified intents, not unrestricted conversation. Forecasting is a transparent spending-average baseline, not an ML time-series predictor; all money math is deterministic. Subscription detection focuses on monthly services with three charges and stable amounts. CSV currency inputs currently support dollar/decimal-dot formats, not international decimal-comma currencies.

The production build includes an installable web manifest, Android/iPhone icons, a static-only service worker and mobile installation instructions. Financial/API data is never cached by that worker; offline navigation shows a connection-required page. Chromium installability and mobile touch flows pass automated checks; installation on physical Android/iPhone devices remains a manual check. See [phone setup](docs/MOBILE_SETUP.md) and [native roadmap](docs/CAPACITOR_ROADMAP.md). Source API fixtures and browser tests use synthetic records only.

## Data, licenses, and disclosure

All student records, merchant-description training labels, and deal examples were generated for this project. No private coursework or unrelated business code was reused. See `data/LICENSE.md` and `docs/ATTRIBUTIONS.md`. Merchant names are descriptive references; no affiliation or discount validity is implied.

This project was generated and integrated with OpenAI Codex assistance in this workspace. The supplied requirements predated implementation; general-purpose libraries and installed tooling existed independently. Team names/contributions have not been provided. See `docs/WORK_DISCLOSURE.md` and confirm the official hacking start before making any claim about work completed during Hacklanta. No event eligibility certification is made by this repository.

## Submission state

Draft Devpost text, demo recordings, judging answers, an acceptance audit, API/integration documentation, and a manual submission checklist are in `docs/`. The Gmail, SmartApprove, Circles, PWA, presentation and final demo upgrades are published in commit [`7427f7e`](https://github.com/ReddyR1105/Moniq/commit/7427f7efb8e71210268fe77aa9462c5c8ff0c37d) on [ReddyR1105/Moniq](https://github.com/ReddyR1105/Moniq), with [passing hosted CI](https://github.com/ReddyR1105/Moniq/actions/runs/38109450542). See the [Render readiness audit](docs/RENDER_READINESS.md) for deployment checks and remaining container verification. Render deployment and Devpost submission have not occurred; both remain separate approval steps. Check the [official rules](https://hacklanta.devpost.com/rules) and [submission requirements](https://hacklanta.devpost.com/) before submitting.


## Submission artifacts

See [demo walkthrough](docs/DEMO_WALKTHROUGH.md), [screenshots](docs/screenshots/), [demo recording](docs/demo/moniq-demo.webm), [submission checklist](docs/SUBMISSION_CHECKLIST.md), and [publication commands](docs/GITHUB_PUBLICATION.md). The video is silent actual browser footage; add narration or use its captions before a public upload. Source and media are packaged at `D:\Map\Moniq-submission.zip`, excluding dependencies, private runtime data and credentials. `scripts/package_submission.py` validates source paths, credential patterns, ZIP CRCs and file hashes. The package can be extracted and installed using the fresh-checkout commands above.

## Final Hacklanta materials

[Final presentation](docs/demo/Moniq_Hacklanta_Final.mp4), [complete feature walkthrough](docs/demo/Moniq_All_Features.mp4), and matching narration scripts, SRT and VTT captions are in `docs/demo/`. These are actual Chromium recordings of isolated synthetic app workspaces, with local Windows narration and no music. Original WebM and screenshot assets are preserved.

[Current QA](docs/QA_REPORT.md), [Devpost description](docs/DEVPOST_SUBMISSION.md), [judges' pitch](docs/JUDGES_PITCH.md), [submission checklist](docs/SUBMISSION_CHECKLIST.md), and [recording instructions](docs/DEMO_SCRIPT.md). The final source/media package is `D:\Map\Moniq_Hacklanta_Final.zip`; `scripts/package_submission.py --output D:\Map\Moniq_Hacklanta_Final.zip` rebuilds it with source hashes and CRC verification.

The published baseline remains `8ac182f`. The final local release requires owner approval before push. Hosted CI for new changes cannot run until publication is approved. Render and Devpost submission remain separate actions.

The latest local production/mobile checks pass **112 backend tests, 16 local Chromium tests and 8 production Chromium tests**. The public service remains prepared locally, with no verified cloud URL or APK. [Public release status and costs](docs/PUBLIC_RELEASE_STATUS.md) explain the exact external actions still requiring approval. [Judging presentation and PDF](docs/presentation/README.md) are preserved.

[Premium 90-second product video](docs/demo/Moniq_Hacklanta_Premium_Final.mp4) has a new American neural voice, a rewritten script and matching regenerated captions. Earlier videos remain intact. See [premium verification](docs/demo/PREMIUM_VERIFICATION.md); the owner must listen and approve the cut before any public upload.
