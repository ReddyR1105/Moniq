**Current final verification:** [QA_REPORT.md](QA_REPORT.md) supersedes the earlier counts below. The existing secondary account remains connected; no personal emails were opened or recorded.

# Moniq Gmail integration verification

Verified locally October 10, 2026. This records the Gmail working-tree changes after the published `8ac182f` baseline. No additional commit was pushed and no deployment occurred.

| Check | Actual result |
| --- | --- |
| Full backend suite | **63 passed**, final run 10.23 seconds; all 35 original tests retained |
| Local Chromium journeys | **10 passed**, 57.4 seconds; original eight plus private accounts and connected Gmail controls |
| Production public demo Chromium | **2 passed**, 21.1 seconds; Gmail hidden and API access forbidden |
| Production frontend build | **Passed**, 2,181 modules; CSS 49.55 kB, app JS 325.43 kB, charts 438.11 kB |
| TypeScript / ESLint / Ruff | **Passed**, including the new key setup script |
| Dependency consistency | **Passed** (`pip check`); five OAuth/encryption dependencies added to the lockfile without changing previous pins |
| Independent ML reproduction | **Passed**; baseline remains 250/264 correct, raw accuracy 94.69697%, macro F1 0.943244 |
| GitHub Actions configuration | **Passed** actionlint 1.7.12, shellcheck/pyflakes disabled locally; workflow runs new tests through existing commands |
| Actual local frontend / backend | **HTTP 200** at 127.0.0.1:5173 and backend health on 8000; actual Gmail status reports the documented callback/scope |
| Secret exclusion | Generated key absent from every tracked/candidate source file; `.env`, tokens, runtime databases, builds and model files ignored |
| Original financial data | All 97 transactions, 1 account, 1 profile, 11 budgets and 1 goal preserved; only additive Gmail tables introduced |
| Existing video / screenshots | All 12 existing media files remain accessible and byte-identical to the published baseline |
| Real Google mailbox authorization | **Pending local OAuth client ID/secret configuration and test-user consent**; no real emails fetched |
| Hosted CI for Gmail changes | **Not run**; these changes have not been pushed |

Backend tests execute the production OAuth factory against mocked official Google endpoints, exercising PKCE S256, read-only/offline access, redirect matching, encrypted tokens, no reads before consent, browser-bound expiring one-use state, cancellation, wrong scopes, token refresh/revocation failures, unreadable-store deletion, loopback/Origin restrictions, pagination, quota errors, MIME/HTML/attachment handling, financial event extraction, ambiguity, account matching, date bounds, credit-account validation, message and transaction deduplication, private model isolation, and export/deletion behavior. Public-mode tests reject Gmail/personal access before reading credentials or creating a private database.

Synthetic paycheck and purchase tests confirm **$10 + $400 = $410; $410 − $15 = $395**, with dashboard, per-account balances, budgets and forecast current balance agreeing. Sync alone leaves balances unchanged. The connected browser test mocks Gmail connection/email responses and writes confirmed transactions through the actual local backend; it is not a claim of live Google authorization.

The browser suite also uncovered and fixed the pre-existing optional blank-merchant save error. Test screenshots now go into ignored runtime storage instead of overwriting the existing submission screenshot.

Two upstream deprecation warnings remain for the installed HTTPX compatibility paths in Starlette and Authlib. There were no test failures. Actual Gmail consent, Google quota behavior and real-bank email formats require local testing after setup; extraction is conservative and all cash flows require explicit posted confirmation.

Follow [GMAIL_SETUP.md](GMAIL_SETUP.md) for the exact Cloud client configuration, local environment variables, start commands and test-user walkthrough. The encryption key is already generated in this workstation's ignored `.env`; OAuth client ID and secret remain blank. Do not upload that file or any real financial exports when reviewing or publishing source changes.
