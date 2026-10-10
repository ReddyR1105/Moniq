**Current finalization supersedes these historical upgrade counts:** see [QA_REPORT.md](QA_REPORT.md) for 109 backend, 16 local and 3 production browser tests, account/goals/dashboard additions, vulnerability checks and final media.

# SmartApprove + Circles verification

Executed locally on October 10, 2026 in the existing `D:\Map\Moniq` project. This is a local working-tree upgrade over published commit `8ac182f`; no new commit has been pushed, deployed, or submitted.

| Check | Result |
| --- | --- |
| Backend pytest, existing + new tests | **103 passed**; two upstream Starlette/Authlib httpx compatibility deprecation warnings |
| Chromium local journeys | **13 passed**, including the three new Circles/SmartApprove journeys and all 10 existing journeys |
| Production public-demo Chromium journeys | **3 passed**, including public Circles visitor isolation and mobile navigation |
| TypeScript | Passed (`tsc -b`, also enforced in production build) |
| ESLint | Passed |
| Ruff | Passed for backend, tests and scripts |
| Production build | Passed; application and chart code split, source scanning verified |
| GitHub Actions YAML | Passed actionlint; existing workflow automatically discovers added pytest and Playwright cases |
| Dependency consistency | `pip check` passed; no new dependencies for the sharing/approval upgrade |
| Independent original ML baseline | Passed; 250/264 raw synthetic classifications, macro F1 0.943244; no claim of real-bank accuracy |
| Live existing local servers | Backend 127.0.0.1:8000 and frontend 127.0.0.1:5173 returned HTTP 200 |
| Original data preservation | All original rows in both original databases matched pre-upgrade SQLite backups across all 11 existing tables |
| Original media preservation | All 12 original PNG/WebM assets matched published HEAD byte-for-byte |

## Financial evidence

The real backend tests and UI journey verify $100 starting cash, one $40 controlled purchase, a $20/$20 split, and a $20 actual repayment. Result: **$80 cash, $20 personal spending, $40 gross cash out, $0 new income, $0 receivable**. The original purchase is stored once. The prior $10 + $400 confirmed paycheck − $15 purchase example remains verified, including SmartApprove's exact-domain rule path.

Tests cover equal rounding through 19 participants, one-cent remainders, custom amounts, percentage splits, exclusions, member additions without changing prior allocations, editing/deleting unsettled expenses, cross-circle validation, non-USD isolation, partial/full repayments, idempotent retries, overpayment rejection, paid-by-other obligations, outgoing settlements, reuse of manually confirmed incoming Gmail cash, linked transaction protection, repayment CSV type preservation, shared-rent/subscription insight evidence, and complete export/reset/deletion coverage.

Approval tests cover defaults off, CRUD/suspension/removal, exact address/domain rules, spoofed or missing receiving evidence, duplicate headers, SPF/DKIM/DMARC failures and alignment, forwarded ARC evidence, synthetic senders, disallowed subdomains, per-event/per-account restrictions, transaction and exact daily limits, repeated sync and duplicate receipts, future/pending/order/pay-stub/transfer/uncertain messages, audit corrections and single-use reversals. The explicit scenario preserves personal data and the Gmail connection and makes no Google API calls.

Public tests exercise the actual cookie middleware, session databases and production frontend. One visitor's scenario, rules and shared expenses never appear in another visitor's session; neither visitor can reach Gmail/private workspaces. The nine-page navigation fits mobile.

## Assets and execution

- [New Circles screenshot](screenshots/11-circles-upgrade.png).
- [Short additional actual-browser recording](demo/moniq-circles-demo.webm), silent supplemental evidence.
- [Original demo recording](demo/moniq-demo.webm), preserved with original captions.
- [Feature decisions and working walkthrough](CIRCLES_SMARTAPPROVE.md).

Start the app in separate PowerShell terminals:

```powershell
cd D:\Map\Moniq
.\scripts\start-backend.ps1
```

```powershell
cd D:\Map\Moniq
.\scripts\start-frontend.ps1
```

Open `http://127.0.0.1:5173/#circles` and choose **Start isolated walkthrough**. Existing servers may already be running; open the URL directly in that case. Use **Return to synthetic demo** afterward. Real Gmail setup is unchanged; see [GMAIL_SETUP.md](GMAIL_SETUP.md). The existing connection was observed as configured and connected; this upgrade validation used synthetic emails and mocked Google responses, not live mailbox synchronization.

Full local checks with the installed portable Chromium:

```powershell
cd D:\Map\Moniq
$env:MONIQ_BROWSER = 'chromium'
$env:PLAYWRIGHT_BROWSERS_PATH = 'D:\Map\Moniq\.tools\playwright-browsers'
.\scripts\check.ps1 -Browser
```

## Material limitations and remaining steps

Local participants are not authenticated collaborators; there are no invites, permissions between external accounts, payment sending, automatic bank verification, currency conversion, background Gmail polling, repayment cancellation, or automatic shared-refund reconciliation. Settled allocations stay protected rather than permitting destructive edits. Imported-message provenance and differing email dates/descriptions can require manual reconciliation; Gmail balances remain estimates. Two upstream deprecation warnings remain, with no failed checks. Details are in the feature documentation.

The original published baseline's hosted CI passed. These local upgrades need review and explicit publication approval before a new hosted workflow can run. No claim is made that the upgraded source has already passed hosted Linux CI.

Prepare the latest archive without replacing the previous submission ZIP:

```powershell
.\.venv\Scripts\python.exe scripts\package_submission.py --output D:\Map\Moniq-upgrade-submission.zip
```

The packager includes Git-visible tracked and untracked source/docs/media, rejects sensitive/generated paths and credential patterns, and verifies archive CRCs plus each source file's SHA-256. `.env`, encrypted tokens, all databases/backups/scenario data, tools, dependencies and production build outputs stay excluded. Keep the local ZIP private until the team approves sharing. Review [SUBMISSION_CHECKLIST.md](SUBMISSION_CHECKLIST.md) for roster/work-window disclosure, Fintech track, public media links, optional hosting and Devpost confirmation.
