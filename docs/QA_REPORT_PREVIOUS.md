# Moniq previous validation report (before public-session finalization)

Initial validation: October 9, 2026; final resumed checks: October 10, 2026 (America/New_York), Windows, Python 3.14.7, Node 24.21.0, Vite 6.4.4, Playwright-managed Chromium. Automated financial records are synthetic. Existing source/functionality and Git history were preserved; no push or Devpost submission occurred.

| Check | Actual result |
| --- | --- |
| Backend pytest | **30 passed**, 3.93 seconds (October 10 rerun) |
| Ruff: backend, tests, scripts | **Passed** |
| Independent ML fit/check | **Passed**, saved baseline and confusion matrix reproduced |
| TypeScript | **Passed** |
| ESLint | **Passed** |
| Production build | **Passed**, 2,179 modules; CSS 49.33 kB, app JS 306.60 kB, charts 438.11 kB |
| Chromium browser acceptance | **8 passed**, 51.2 seconds (final source after Tailwind fix) |
| CI actionlint 1.7.12 | **Passed**, shellcheck/pyflakes integrations disabled |
| Normal launch scripts | **Passed**, frontend HTTP 200, backend/proxy health ok, model loaded |
| Actual GitHub Actions/Linux run | **Pending approved push**, not represented as passed |

## Connected features and regressions

Backend tests verify exact income/expense/refund semantics, CSV signs/mapping/dates/atomic validation/deduplication, CRUD/corrections, classifier reload/confidence/fallback, notifications/confirmation, weekly/monthly limits, scenario deltas/caps/delay, bill double-count prevention, one-time/monthly/income schedules, month-end dates, subscriptions, deal ranking/eligibility, assistant evidence, profile/allowance/goals, engine-restart persistence, export/deletion/reset, foreign-Origin rejection and formula-safe CSV.

The eight browser cases cover: the complete eight-step guide including budget edits and reset; every mobile page and saved-offer filtering/persistence; alert ? ML ? confirmation ? exact $18.75 update ? assistant ? forecast ? deals; CSV import/correction/delete; all-page navigation and profile/budget persistence; subscriptions/downloads/persistent deletion/reset; keyboard dialogs/screenshots; and bill creation/edit/deletion. Actual FastAPI/Vite services run on 8001/5174 with isolated synthetic SQLite. Real defects were fixed while preserving assertions.

Audited fixes: malformed CSV sniffer exceptions return validation errors; month-end renewals retain the observed anchor; deal interests tolerate spaces; affordability rejects ambiguous/negative/zero/over-precision amounts; investment requests do not become purchase estimates; new schedules default to tomorrow; production preview port 4173 is accepted locally; donut totals distinguish net refunds; and an accessible table heading no longer causes mobile overflow. The guided purchase step saves once, then opens Transactions for review.

Normal launch observation: balance **$4,943.03** and four upcoming bills on the validation date, read from SQLite. The actual main frontend was opened in Chromium and all pages inspected at 390 ? 844; final acceptance found no page crashes or blocking API errors. Desktop capture is 1440 ? 1000.

## Independent ML reproduction

`scripts/reproduce_ml.py` fits a separate pipeline from the saved synthetic CSV without importing the application classifier or loading joblib. It checks merchant-family/description disjointness and compares the full confusion matrix and macro F1 to the baseline.

- 1,056 descriptions, 11 categories; **792 training / 264 held-out** rows.
- Raw correct **250/264**, errors **14**, accuracy **94.69697%**, macro F1 **0.9432442630**.
- Threshold 0.45 flags **109/264** for review; automatic coverage **58.71212%**.
- Miscellaneous fallback accuracy **63.63636%**; accepted predictions **155/155** correct on this set only.
- Synthetic English formatting variants are correlated; this is not measured real-bank accuracy. Confidence is uncalibrated. Corrections are excluded from this baseline. Full reports are in `data/`.

## CI and repository

Push/PR/manual CI uses Python 3.14, Node 24, pinned official action commits, exact pip/npm lockfiles, pytest/Ruff/independent ML/types/ESLint/build and Chromium. Playwright manages synthetic services with correct CORS/proxy ports. Diagnostics exclude private application databases. No API secrets are required. Local Windows/actionlint checks do not certify the first Linux runner execution.

Tracked files, untracked source and staging were inspected. Existing main has no prior commits, staged files or remote. `.env.example` has blank optional keys. Generated dependencies/models/SQLite/caches/tools are ignored. The package script refuses sensitive paths and common credential patterns, then verifies each ZIP entry's SHA-256 and CRC. No `.git`, dependencies or private runtime databases are included.

One upstream Starlette warning deprecates TestClient's httpx compatibility path; tests pass. Browser output notes overlapping NO_COLOR/FORCE_COLOR settings. Neither is an application failure.

## Limits

No paid API, live bank, actual enrollment verification, SMS/iMessage synchronization, live offer redemption, actual cancellation, public deployment, authentication, encrypted SQLite, full offline service worker, complete assistive-technology/WCAG audit, GitHub publication or Devpost receipt is claimed. This is a single-user local prototype. Team eligibility, work-window disclosure, accessible public links and submission receipt require owner/team actions.

## Actual media capture

The separate real-UI recording test passed (about 2.3 minutes for the test, 2.5 minutes including service startup). It verified a complete purchase/ML/save/budget/scenario/deal/assistant/subscription/reset journey, without page crashes or server errors. Ten actual screenshots are under `docs/screenshots/`; silent WebM footage and timestamped caption text are under `docs/demo/`. The video is actual Chromium footage, not fabricated UI, and has not been uploaded.

## Final package and asset verification ? October 10

Tailwind explicitly scans only frontend/src (`source(none)` plus `@source "./"`), preventing unrelated runtime/dependency files from changing generated CSS. Fresh-extraction and workspace production assets have identical names and SHA-256 hashes: index-GzzSnFv5.css, index-DIdMBXGj.js and charts-BF22aakd.js. The final frontend build passed in 3.50 seconds.

The ZIP was extracted into an isolated directory, its locked Python/npm dependencies installed anew, and backend tests (30 passed), independent ML, Ruff, frontend types/ESLint/build and Chromium tests (8 passed) all passed. After the Tailwind adjustment the extracted production build was rebuilt and matched the workspace byte for byte. The actual production preview on 4173 with backend 8002 saved a classified purchase, changed expenses by exactly $18.75, returned a ?$150 scenario difference, and rendered all eight mobile pages without overflow, page errors or blocking API responses.

Final media checks used Chromium to decode all ten PNGs and open/seek the WebM: 136.16 seconds, 1440 ? 1000, no media error. Assets are accessible locally and included in the archive; public upload/access has not been verified. The refreshed ZIP contains the latest verified source and final documentation; entry CRCs and SHA-256 hashes match source files. Generated runtime/dependency/build files are excluded by Git and packaging.

Dependency consistency checks passed (`pip check`); npm reported zero vulnerabilities. Fresh npm installation emitted an ESLint 9 support/deprecation notice and an esbuild install-script notice. They did not prevent installation, lint or either production build. These notices, the upstream TestClient warning, and pending Linux CI execution remain disclosed.
