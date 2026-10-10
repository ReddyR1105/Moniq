# Moniq final QA report

Verified October 10, 2026, America/New_York. Windows, Python 3.14.7, Node 24.21.0, Vite 6.4.4, Playwright Chromium. This report supersedes the earlier local-only report retained as QA_REPORT_PREVIOUS.md. Existing functionality and local data were preserved. No GitHub push, cloud deployment, or Devpost submission occurred.

| Check | Actual result |
| --- | --- |
| Backend pytest | **35 passed**, including five public-session tests; final measured run 5.40 seconds |
| Ruff: backend, tests, scripts | **Passed** |
| Independent ML fit/check | **Passed**, saved confusion matrix and raw macro F1 reproduced |
| TypeScript | **Passed** (`tsc -b` included in production build) |
| ESLint | **Passed** |
| Production frontend build | **Passed**, 2,180 modules; CSS 49.33 kB, app JS 311.29 kB, charts 438.11 kB |
| Local Chromium acceptance | **8 passed**, 51.6 seconds |
| Production Chromium acceptance | **2 passed**, 17.0 seconds; visitor isolation, synthetic import, all mobile pages |
| GitHub Actions actionlint 1.7.12 | **Passed** locally, shellcheck/pyflakes disabled because unavailable |
| Dependency consistency | `pip check` passed; offline npm audit reported zero vulnerabilities |
| Hosted GitHub Actions | **Not run**, awaits approved push |
| Docker build / Render deployment | **Not run**, Docker unavailable and cloud account/deployment approval pending |

## Coverage and public boundaries

Original backend coverage includes malformed/inconsistent CSVs, atomic imports, sign conventions and refunds, duplicates, invalid financial amounts, transaction corrections, exact budget and forecast calculations, subscriptions, month-end scheduling, deletion/reset, local restart persistence, assistant ambiguity/fallback and API validation. The eight local browser cases exercise the complete guided demo, $15.75 alert extraction/classification/confirmation and refreshed budgets, imports/corrections/deletion, profile/budget persistence, all eight desktop/mobile pages, saved deals, subscriptions, exports, deletion/reset, keyboard dialogs and editable schedules.

Five added backend tests exercise independent visitor databases, purchase/reset/deletion/export isolation, duplicate rejection, upload/custom-text policy, immutable model/retraining rejection, synthetic CSV import/deduplication, supported assistant questions, HttpOnly/SameSite/Secure cookies, foreign origins, request limits, expiry/capacity, concurrent session creation, active-session cleanup protection, restart invalidation, and independent profile/goal/schedule/correction changes. Public sessions are temporary, single-process synthetic sandboxes, not authenticated financial accounts or persistent cloud storage.

Production browser tests run the actual frontend/dist served by FastAPI on port 8003. Separate browser contexts demonstrate an exact $15.75 change for visitor A with visitor B unchanged, a -$150 scenario, ranked sample deals, grounded assistant answers, reset isolation, disabled uploads/retraining, sample imports, read-only identity and all eight pages at 390 x 844. Direct SPA routes and unknown API route behavior are checked. UI values come from the backend, not replacement test mocks.

An initial simultaneous local/public browser invocation collided in Playwright's output directory and failed two local cases. Separate output directories were configured and all eight local tests passed on the isolated rerun. Assertions were retained; the new expense assertion was corrected to match the API's established negative signed-expense convention. An upstream Starlette warning deprecates TestClient's httpx compatibility; color-environment notices also appear. Neither is an application failure.

## ML reproduction

Independent fitting uses the saved synthetic CSV, not the application classifier or joblib cache: 1,056 descriptions across 11 categories; 792 training / 264 held-out rows with disjoint merchant families. Raw correct **250/264**, accuracy **94.69697%**, macro F1 **0.9432442630**. Confidence threshold .45 flags **109/264**, automatic coverage **58.71212%**; miscellaneous fallback accuracy **63.63636%**. Accepted predictions are 155/155 correct on this synthetic set only. Descriptions and formatting variants are synthetic/correlated, probabilities uncalibrated; no real-bank accuracy claim is made.

## Assets, package and publication

Tailwind scans only frontend/src with `source(none)` and `@source "./"`, keeping ignored runtime/dependency files out of generated CSS. Source/media ZIP CRCs and every included file SHA-256 are verified by scripts/package_submission.py. Dependencies, private databases, model caches, traces, secrets and build artifacts are ignored/excluded. The existing repository's correct origin is https://github.com/ReddyR1105/Moniq.git; remote refs were empty before publication preparation. A local reviewed commit is prepared; final push approval remains required.

The separate recording test captures actual React/FastAPI/ML UI using synthetic data, asserts the $15.75 purchase, budget/scenario/assistant/reset flow and checks page/server errors. Ten screenshots and a silent WebM with captions are prepared; media accessibility and final duration are recorded in docs/demo/README.md. Earlier recording/screenshots are preserved in an ignored runtime backup.

## Remaining limitations

No live bank/Plaid/Gemini integration, automatic SMS/iMessage synchronization, verified live offers, actual subscription cancellation, real student verification, production authentication, encrypted SQLite, full offline financial service worker, independent WCAG audit, hosted deployment/CI success or Devpost receipt is claimed. Public mode intentionally permits only built-in synthetic text and blocks uploads/shared retraining; local custom functionality remains. Docker/Render verification, public video access, participant/registration/work-window disclosure and actual submission require the owner/team.

Final extracted-source check: the ZIP source was extracted into a separate validation directory and built using its previously fresh-installed locked dependencies. All three generated asset SHA-256 hashes match the workspace exactly: index-GzzSnFv5.css, index-CnHNDI9q.js, charts-BF22aakd.js. This rerun reused installed validation dependencies; it did not reinstall them.

The refreshed recording is 134.16 seconds (2:14.16), VP9, 1440 x 1000, 25 fps, silent. Chromium decoded all ten PNGs and loaded/sought the WebM without errors; FFmpeg decoded a frame at 60 seconds. The mobile screenshot now waits for sidebar animation completion. A production route test found and fixed a Windows path separator issue that could serve HTML for unknown API URLs; API 404 assertions are preserved.

Exact Windows launch scripts were executed successfully for backend 8000, frontend 5173 and production demo 8080. Chromium opened both application URLs, loaded database-derived balances and confirmed the correct local/public configuration and healthy loaded models without page errors. These owned test servers are stopped after verification. Git text line endings are normalized to LF through .gitattributes; staged whitespace checks pass.
