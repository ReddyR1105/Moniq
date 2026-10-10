# Moniq final QA report

Verified October 10, 2026 on Windows with Python 3.14.7, Node 24.21.0, Vite 6.4.4 and Playwright Chromium. This report is the current final-master-prompt verification; older QA files retain previous milestones. The existing application was extended, not rebuilt. No final release push, cloud deployment or Devpost submission has occurred.

## Actual current results

| Check | Result |
| --- | --- |
| Complete backend suite | **109 passed**, 34.10 seconds; two upstream httpx compatibility deprecation warnings |
| Local Chromium | **16 passed**, 101.98 seconds; 0 failures, skips or flaky cases |
| Production public Chromium | **3 passed**, 28.76 seconds; actual FastAPI-served frontend/dist |
| TypeScript, ESLint, Ruff | **Passed** |
| Production frontend build | **Passed**, 2,184 modules; CSS 50.96 kB, app JS 362.42 kB, charts 438.11 kB |
| Independent classifier evaluation | **Passed**, 250/264 raw correct and saved baseline reproduced |
| Python dependency consistency | **Passed**, pip check |
| npm vulnerability audit, production and all dependencies | **0 known vulnerabilities**; all-dependency report covers 301 packages |
| Locked Python vulnerability audit | **0 known vulnerabilities**, 43 packages via pip-audit |
| GitHub Actions configuration | **Passed** actionlint; pinned actions, read-only permissions, locked installs, all application checks |
| Original database rows | **Preserved**, each original row in both moniq.db and personal.db matched the pre-upgrade backups across 11 tables each |
| Original media | **Preserved**, all 12 baseline PNG/WebM files byte-identical to published HEAD |
| Secret/generated file exclusions | **Passed**, Git-visible source/media scan; .env, tokens, private databases, tools, caches, dependencies and dist excluded |
| Owner app servers | **HTTP 200**, frontend 5173 and backend 8000 |
| Owner Gmail connection | **configured=true, connected=true**; no personal email synchronization or content inspection performed |
| Recording Gmail configuration | **configured=false, connected=false**, separate databases and MONIQ_GMAIL_DISABLED=true |
| Hosted CI baseline | **success** at 8ac182fc7e024305c80fbf4f242cb22a8a4b09dd |
| Hosted CI final release | **Pending approved push**, not represented as run |

## Application coverage

Existing tests cover exact financial calculations, posted dates, imports and malformed CSVs, signed amounts/refunds, deduplication, corrections, subscriptions, calendar schedules, forecasts/scenarios, budgets, assistant evidence, profile/goals, persistent deletion/reset, mobile layouts, keyboard dialogs and all pages. Gmail uses synthetic messages and mocked official Google responses to test authorization code/PKCE/state, encrypted tokens, refresh/disconnect, bounded synchronization, financial extraction, account matching and review. SmartApprove tests reject spoofed/conflicting/missing sender authentication, uncertain posted/date/account/category evidence, duplicate events and cap violations; audit correction/reversal paths are exercised. Circles tests exact equal/custom/percentage splits, linked charge preservation, personal-share budgets, partial cash/bookkeeping/matched settlements and repayment deduplication.

Final additions verify dashboard confirmation of parsed synthetic emails and **10 -> 410 -> 395**, isolation from private Gmail, linked debit aliases without extra balances, checking/savings transfers with zero extra income/spending, separate credit debt and card payments, immutable reconciliation history, contributions and estimated completion dates without cash creation, grounded last-paycheck/goal answers, and responsive account forms. Public-mode tests verify visitor-owned records, reset/export isolation, synthetic-only input/import policy, denied Gmail/private access/retraining, request/origin/cookie restrictions, session expiry and independent Circles ledgers.

## Tailwind production assets

`frontend/src/styles.css` retains `@import "tailwindcss" source(none)` and `@source "./"`, scanning only frontend source. The compiled CSS is `index-yf3jHBzc.css`, 50,961 bytes, SHA-256 **3619a51d9d2afee9550eeff01a86dbde7e57590645c9fb1a68c6e9ea07634959**. Source directives are compiled away; used screen-reader and custom financial/Circles/Gmail styles are present. Unused utilities and ignored runtime/dependency content are excluded. Actual production desktop/mobile browser tests pass.

## ML reproduction and limits

An independent fit from the saved synthetic CSV, without the application classifier/joblib cache, reproduces 792 training / 264 held-out descriptions with disjoint merchant families: **250 correct, 94.6969697% raw accuracy, macro F1 0.9432442630**. Confidence threshold .45 flags 109 descriptions for review; automatic coverage is 58.71212%, and miscellaneous fallback accuracy is 63.63636%. Accepted predictions are 155/155 correct on this synthetic set only. Formatting variants are correlated, probabilities are uncalibrated, and real-bank/email accuracy has not been measured.

## Media and package verification

The final presentation is H.264 MP4, **141.32 seconds (2:21.32), 1920 x 1080, 25 fps**, with AAC Microsoft Zira narration, burned-in captions and separate SRT/VTT. The entire video/audio stream decodes successfully; representative dashboard, settlement and goal frames were inspected. No music or private Gmail content is used. The full walkthrough and final ZIP verification are recorded in the final media/package addendum below when their checks complete.

Raw footage, speech WAVs, traces, intermediate frames and encoder tools remain ignored. Original recordings/screenshots remain unchanged. The final ZIP uses current Git-visible source, not the older baseline archive; every source hash and archive CRC is checked and clean extracted source is validated.

## Security findings and remaining limitations

No known dependency vulnerability or credential pattern was found in the publication set. This is not production security certification. The actual OAuth connection is preserved, while tests/recordings operate in separate synthetic databases. Personal Gmail, arbitrary personal input and tokens are unavailable in anonymous public mode. Money uses integer cents; estimates and goal progress never fabricate bank deposits.

Private mode remains loopback-only and has no production identity system; SQLite/OS backups are not encrypted by Moniq. Gmail parsing supports conservative English/USD financial patterns, not universal bank coverage. Provider-reported authentication is not cryptographic proof of a financial transaction. Synthetic sender approval exists only in an explicit server-owned test scenario. Transfers must not be separately imported as new income/purchases. Circles has local participants, no live collaboration/payment processing, and no automatic settled-expense cancellation/shared-refund workflow. Forecast/goal dates assume the stated spending/income/contribution plans. No live banking/Plaid/Gemini, verified deals, enrollment verification, subscription cancellation, independent WCAG audit, Docker/Render deployment or Devpost receipt is claimed.

Remote history was fetched read-only and matched the published baseline with no unexpected commits. Baseline Actions success was checked through the public GitHub API: https://github.com/ReddyR1105/Moniq/actions/runs/38068681424. The final local release still requires push approval before its hosted CI can start.

## Final media addendum

| Final file | Measured duration | Encoding | Checks |
| --- | --- | --- | --- |
| Moniq_Hacklanta_Final.mp4 | **141.32 s (2:21.32)** | H.264 High, 1920x1080, 25 fps; AAC mono | Full decode, Chromium play/seek, representative frames inspected |
| Moniq_All_Features.mp4 | **398.64 s (6:38.64)** | H.264 High, 1920x1080, 25 fps; AAC mono | Full decode, Chromium play/seek, representative frames inspected |

Both have local Microsoft Zira narration with non-silent PCM, readable burned-in feature captions and separate SRT/VTT/narration scripts. Chromium reported readyState 4, expected dimensions/durations and no media error after playback and repeated seeking. Intro, accounts, $395 dashboard, repayment, goal, forecast and closing frames were inspected. The recordings include actual UI actions and backend ledger updates in separate synthetic databases. Original media is preserved; public uploads remain manual.

A final financial review also caught a reversed-paycheck assistant edge case: an auditable reversal must remove that deposit from the last-confirmed-paycheck answer. The existing authenticated payroll test now verifies this behavior through actual approval, reversal, dashboard and assistant routes. The complete backend suite still passes all 109 tests.

## Clean extracted source verification

The final archive's 149 safe source/media files passed CRC and per-file SHA-256 checks and were extracted into a new ignored validation directory with path traversal checks and no .env. The extracted module path was verified, then **all 109 backend tests passed again (46.08 seconds)** using the existing locked Python environment; Ruff and independent ML reproduction also passed. A **fresh npm ci** installed the frontend lockfile in the extraction, with zero reported vulnerabilities; TypeScript, ESLint and production build passed. Every generated production file hash matched the workspace exactly. npm emitted only upstream ESLint deprecation/install-script policy notices; the build completed successfully.

The delivery archive is rebuilt after this documentation update/local commit, and every archived source hash is checked against the final clean committed tree. Final ZIP hash/size and the local commit are provided in the handoff, avoiding self-referential archive hashes inside the package. No private runtime data, dependency directory or raw capture is included.
