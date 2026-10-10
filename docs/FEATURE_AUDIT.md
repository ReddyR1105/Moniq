# Moniq acceptance audit against the master prompt

Core scope is implemented locally and connected through FastAPI/SQLite. Optional/live integrations and publication tasks remain explicit limits. See QA report for measured checks; no acceptance claim implies real-bank accuracy or production security.

| Original feature area | Implemented evidence and UI connection | Boundary |
| --- | --- | --- |
| A. Student dashboard | Overview fetches database-derived balance/income/net expenses/budget, interactive category and weekly charts, bills, subscriptions, sample savings and insights | Synthetic account; no bank sync |
| B. Transaction tracking | Transactions CRUD, filters, search, pagination, CSV preview/mapping, currency/date handling, merchant cleaning, ML classification and deduplication | Dollar/decimal-dot formats; duplicate heuristic may merge identical purchases |
| C. Purchase notifications | Paste/simulator → extract merchant/amount/date/type → ML → editable confirmation → persisted transaction → updated budget | Manual import only, no SMS/iMessage synchronization |
| D. ML classification | Real saved scikit-learn pipeline, generated labeled data, merchant-disjoint held-out evaluation, confidence/fallback, correction storage/retraining and error reporting | Synthetic English evaluation; uncalibrated confidence |
| E. Smart budgeting | Monthly/weekly editable category limits, progress and alerts; stored income/expense schedules for allowance, jobs, rent, tuition, meal plans, aid; goal progress | Savings goals don't reserve funds |
| F. Predictive intelligence | 30-day history/balance/schedule forecast, projected spending/bills/overrun risks/shortfalls and assumptions; purchase/reduction/income/delay scenarios | Historical-average forecast, no trained time-series model; estimates |
| G. Student savings | Eight synthetic offer themes; ranked by history/interests/eligibility/budget/prices; eligibility and price/source/expiry/verification fields, saved bookmarks | No live discounts; expensive offers omitted; unknown source/expiry labeled |
| H. Subscription detection | Three stable monthly service charges, typical amount, renewal, monthly/annual costs, streaming overlap warning, persistent confirmation/dismissal | No cancellation, annual-charge or variable-bill detection |
| I. AI financial assistant | Local intent router retrieves actual financial calculations for supported questions and shows evidence | Optional Gemini absent; unrestricted chat not claimed |
| J. Profile/settings | Name, university, academic year, income preference, allowance, interests, eligibility demo toggle, goals, in-app alert preference, export/delete/reset | No actual student verification or push notifications |
| UX | All eight pages, mobile/sidebar navigation, interactive charts, dialogs, keyboard Escape/focus, reduced motion, loading/error/empty states | PWA-ready manifest; offline service worker absent |
| Banking | Honest synthetic demo mode, seed/simulated purchases, provider protocol and reconciliation design | Plaid Sandbox flow/sync not implemented |
| Privacy | Validation, bounded CSV, ORM queries, env secrets, local CORS/Origin writes, persistence, no-store, export/deletion | No production identity, encrypted SQLite, or compliance certification |
| Mandatory judge demo | Guided eight-step tour; sample student/income/rent/tuition/food/refund/subscription/offer/budget records; trained predictions; repeatable reset | Local executable instructions, no bank signup |
| Architecture | Separate frontend/backend, requested database entities and endpoints plus editable schedules | Local persistence plus one-process isolated public synthetic sessions |
| Testing | Meaningful backend math/import/ML/persistence/API tests; frontend types/lint/build; browser judge flow | See actual QA results, no invented pass counts |
| Repository | Required directories, manifests/locks, env example, ignore rules, scripts, README/data provenance/docs | Origin configured; reviewed local commit; approved push and hosted CI pending |
| Devpost materials | Description, 2–3 minute script, judging notes, official checklist and AI/work disclosure | Screenshots and actual silent recording are prepared; team, official window, narration/upload, publication and submission require manual completion |

The original 20 acceptance criteria map to the foundation, intelligence, UI, tests, and documentation rows above. Opening the frontend/backend, database persistence, imports, ML/corrections, budget/forecast updates, scenarios, ranked deals, subscriptions, local assistant, reset, setup, and submission draft files are implemented. Public publication and final competition submission are not represented as complete.

Finalization adds merchant-disjoint independent ML reproduction, portable Chromium tests, push/PR CI with lockfiles, eight-step guided UI acceptance, all-page mobile checks, actual screenshots/video, and source ZIP verification. Details and measured limitations are in QA_REPORT.md.

Final public-mode addition: backend-enforced synthetic-only text and sample CSV import, opaque per-visitor cookies/databases, expiry/capacity limits, separate immutable model, one-origin built frontend, Start Demo/Reset Demo, Docker/Render Free configuration and public browser tests. Local custom CSV, messages, profile and retraining remain available. See DEPLOYMENT.md and the current QA report.

## SmartApprove + Circles upgrade

The ninth navigation page is Moniq Circles. Local circles, multiple currencies, payer/subset selection, exact equal/custom/percentage allocations, transaction/Gmail purchase links, editable unsettled allocations, partial/full bookkeeping and actual cash repayments, manual incoming-transaction matching, per-currency receivables/payables, history and settlement suggestions are implemented. Personal allocations feed budgets/charts/insights; bank cash remains unchanged until actual cash is recorded. Optional trusted-sender rules support defaults-off automation, exact matching, authentication evidence, account/event restrictions, caps, suspension/removal and audit corrections/reversals. Overview and the assistant use stored results. An isolated $100/$40/$20 walkthrough exercises actual backend policy and accounting. See [upgrade QA](UPGRADE_QA.md) and [boundaries/decisions](CIRCLES_SMARTAPPROVE.md). Real multiuser collaboration, external payments, verified bank posting, automated shared-refund reconciliation, and repayment cancellation are outside this local MVP.

## Final master prompt acceptance, October 10

The current release adds actual dashboard email confirmation, parsed synthetic $10/$400/$15 scenarios, debit aliases, checking/savings cash versus credit debt, paired internal movements, reconciliation, multiple savings goals, contribution history, monthly plans and completion estimates. Dashboard savings progress and grounded last-paycheck/goal answers are connected to the active database. New backend and Chromium tests verify the additions; QA_REPORT.md supersedes older test counts.

The real Gmail connection is preserved; no personal emails were opened for recording. Both final MP4s use isolated synthetic records. Future-only items remain authenticated hosting, live bank APIs, collaborative Circles, settled-expense correction/shared-refund automation, verified offers, independent security/accessibility review and real-bank format evaluation. Imported transfers must be identified and reconciled rather than separately counted as income/purchases.
