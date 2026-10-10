# Moniq

**Spending, Made Smarter.**

**Track:** Fintech. AI/ML is our secondary technology focus. No additional track or sponsor challenge is claimed.

## Problem and inspiration

College students juggle rent, tuition, family support, part-time pay, and everyday purchases on irregular schedules. Spreadsheet upkeep is tedious, and an account balance alone does not explain what will be left after upcoming bills. Moniq makes that picture easier to understand and maintain.

## What we built

A working React/TypeScript financial companion backed by FastAPI and local persistent SQLite, with an optional isolated temporary synthetic session per public visitor. A synthetic Georgia State student demo opens without bank signup. Students import CSV statements, paste purchase alerts, review actual scikit-learn classifications, set spending limits, inspect subscription patterns, and compare 30-day cash-flow scenarios. The local assistant answers supported financial questions using backend values. The savings engine ranks clearly labeled sample offers that fit spending patterns and remaining budgets.

## How it works

Transactions are normalized to signed integer cents. SQLAlchemy stores profiles, accounts, transactions, budgets, schedules, goals, deals, imported messages, and corrections. TF-IDF and logistic regression categorize descriptions and return confidence. Low-confidence descriptions require review; corrections can retrain the model. Deterministic calculations combine historical variable spending with scheduled income and expenses; scenario controls show numerical differences without changing actual records.

## Challenges encountered

Refunds, statement sign conventions, and duplicate transactions required explicit financial semantics. An early test caught subscription detection counting regular shopping and movie visits; we added service/category evidence. Forecast tests verify that known recurring bills are excluded from the daily spending average and charged once on their scheduled dates. Additional audits fixed malformed CSV validation, month-end renewal anchors, ambiguous assistant purchase amounts, and mobile table overflow. Local Windows tooling required isolated Python dependencies and a project-local Node runtime.

## Technologies used

React, TypeScript, Vite, Tailwind CSS, Recharts, Lucide React, Python, FastAPI, SQLAlchemy, SQLite, pandas, scikit-learn, joblib, pytest, Ruff, ESLint, and Playwright. No live paid APIs are required. Plaid/Gemini integrations are future interfaces, not active integrations.

## What we learned

Measured synthetic classifier accuracy is useful for a baseline but does not establish real-world reliability. A confident category can still be wrong, so editable predictions and stored corrections are part of the product. Predictive financial features benefit from transparent assumptions and exact deterministic arithmetic.

## Accomplishments

The purchase-alert flow saves a reviewed transaction, changes the database-derived balance and budget, and makes the new information available to the assistant and forecast. The same prototype supports statement imports, schedule editing, recurring-service review, export/deletion, and reproducible reset. Actual validation results are in `QA_REPORT.md`; baseline held-out synthetic accuracy is independently reproduced at 250/264 (94.70%) raw accuracy and macro F1 0.943244 with disjoint merchant families. The confidence policy flags 109/264 descriptions for review; automatic coverage is 58.71%, and fallback accuracy is 63.64%. These are synthetic results, not measured real-bank performance.

## Future development

Permission-based Plaid Sandbox linking and incremental transaction reconciliation; legitimate student-offer providers; optional Gemini explanations over calculated evidence; real account identity and encrypted persistent hosting; consent-based message sharing; international statements; and evaluation using appropriately licensed real descriptions.

## Honest work and AI disclosure

OpenAI Codex assisted implementation, design, debugging, tests, and documentation. Libraries/tools and the requirements existed before this implementation session. All student/offer/training data is synthetic. No unrelated private project was reused. **Do not paste a claim that all work occurred during the hacking window until the team verifies the official start and fills in `WORK_DISCLOSURE.md`.** Team roster and individual contributions remain to be supplied by the team.

Repository link, video link, and any hosted demo link: **not published**. Judges can use the README's local executable instructions. This draft does not constitute a Devpost submission.

Actual screenshots and a silent browser recording are included in docs/screenshots/ and docs/demo/. The team must upload accessible media and supply genuine roster/contribution/work-window details. CI is configured and locally validated; a real GitHub Actions run awaits approved publication.

Public testing configuration is prepared for a single-origin free Render service. The public mode blocks personal uploads and free-form personal text, keeps visitor edits/reset/export isolated, and expires synthetic sessions. No public URL is claimed until deployment is approved and verified. Local mode preserves custom imports/messages and model retraining.
