# Moniq hosted private test release

This branch adds a welcome page, explicitly started anonymous demos, invitation-only private accounts, PostgreSQL financial workspaces and per-user Gmail OAuth. It has not been pushed or deployed. The existing `render.yaml` stays synthetic-only. Changing `MONIQ_GMAIL_DISABLED` does not enable hosted Gmail.

## Architecture

Fresh visitors see Create Account, Log In and Try Demo. Demo financial databases remain temporary, bounded and synthetic. Private identities, Argon2id password hashes, hashed opaque sessions, single-use email grants, rate counters, encrypted Gmail credentials and OAuth attempts live in PostgreSQL.

An emailed invitation verifies ownership of an explicitly allowed address before account creation. There is no open signup switch. Every invited user receives an empty PostgreSQL schema named from a server-generated UUID. SQLAlchemy `schema_translate_map` selects it from the authenticated session. Client IDs and workspace cookies cannot select another user's schema. Financial IDs are local to their owning schema.

Sessions expire after 12 hours or 30 idle minutes. Cookies use `__Host-`, Secure, HttpOnly, SameSite=Lax and Path=/. Recovery revokes all sessions and pending OAuth attempts. Writes require exact Origin and session-bound CSRF. Rate counters persist. Private workspaces cannot run demo resets/simulations; demo sessions cannot call real Gmail. Legacy owner database helpers reject hosted mode.

The PWA caches static assets only. APIs use `no-store`; Docker disables access logs to protect OAuth codes. Validation errors omit inputs. Frontend configuration never contains credentials or Gmail tokens.

Hosted Gmail uses an independent stable encryption key. Authenticated ciphertext includes the owning user ID. Hashed OAuth state expires after ten minutes, binds user/session/browser, and is consumed before PKCE code exchange. Google mailbox identity must match the verified login and test-user allowlist. Existing parsing, classification, matching, approvals, forecasts, SmartApprove and audit code runs within that user's schema.

Immutable Alembic revisions live in `backend/migrations/identity` and `backend/migrations/workspace`. PostgreSQL advisory locks serialize migrations and financial writes. Keep one instance and worker because anonymous demos are process-local.

## Safe preview and costs

After approval to publish, create a separate preview from `render.private-preview.yaml`. It creates only a free web service: no accounts, Gmail credentials, database or paid resources. Its trusted HTTPS origin comes from `RENDER_EXTERNAL_URL`; do not override it with the live app's URL. Preserve the existing live service, Blueprint and secrets.

**Try Gmail Transaction Demo** starts with $10, queues a synthetic $400 paycheck for approval ($410), then a $15 purchase ($395). Receiving/dismissing alerts does not change the balance. Repeated alerts cannot duplicate transactions. Emails and accounts are labeled synthetic.

No cloud database or paid resource was created. Disposable local PostgreSQL 17 validates migrations/isolation. Render's [free PostgreSQL expires after 30 days and has no backups](https://render.com/docs/free), so it is unsuitable for durable private financial records. [Render pricing](https://render.com/pricing) separates compute/storage: Basic-256mb is about $6/month plus $0.30/GB/month storage; an always-on web service costs extra. Confirm the Dashboard estimate and obtain approval before purchases. An existing durable PostgreSQL provider can be used after reviewing TLS, retention and recovery.

Use a separate database, dedicated app role and restricted external access. Render internal URLs need services in the same region/private network. External URLs require TLS (`sslmode=require`, preferably provider-supported verified TLS). Keep URLs in private backend environment fields.

Render Free [blocks outbound SMTP on ports 25, 465 and 587](https://render.com/docs/free). The backend also supports the fixed official [Resend HTTPS email endpoint](https://resend.com/docs/api-reference/emails/send-email). Set `MONIQ_MAIL_TRANSPORT=resend`, `MONIQ_MAIL_API_KEY` privately and a verified `MONIQ_MAIL_FROM`. Resend offers a [free tier](https://resend.com/pricing); review quotas and sender/domain verification before choosing it. No email provider account or key was created, purchased or requested here. SMTP requires a hosting plan/network where those ports are allowed. Email delivery and recovery must pass on the intended deployment whichever transport you select.

Apply migrations without enabling accounts:

```powershell
cd D:\Map\Moniq
.\.venv\Scripts\python.exe scripts\hosted-admin.py migrate
```

This reads private `HOSTED_DATABASE_URL`, migrates identity/existing user schemas and never prints the URL. Startup also migrates/checks private schemas. Administrative scripts require a trusted checkout: the runtime Docker image contains backend/data/static assets, without admin scripts.

## Backend configuration

Keep `MONIQ_PUBLIC_DEMO=true`, `MONIQ_GMAIL_DISABLED=true`, `MONIQ_SERVE_FRONTEND=true`, `MONIQ_COOKIE_SECURE=true`, one instance/worker. Independent hosted routing selects authenticated private workspaces while retaining safe legacy defaults.

| Variable | Setting |
| --- | --- |
| `MONIQ_HOSTED_APP` | `true` |
| `MONIQ_PUBLIC_ORIGIN` | Exact service HTTPS origin, no trailing slash; current app `https://moniq-80su.onrender.com` |
| `MONIQ_PRIVATE_ACCOUNTS_ENABLED` | `false` until persistence/recovery drills pass; then invited testers only |
| `HOSTED_DATABASE_URL` | Secret persistent PostgreSQL URL |
| `MONIQ_SESSION_SIGNING_KEY` | Independently generated random secret, at least 43 characters, stable across restarts |
| `MONIQ_TEST_USER_EMAILS` | Only approved Gmail test addresses, comma-separated |
| `MONIQ_PERSISTENCE_VERIFIED` | `true` after restart and backup/restore drills on intended database |
| `MONIQ_RECOVERY_VERIFIED` | `true` after real invitation delivery, verification, recovery and session revocation tests |
| `MONIQ_SMTP_HOST` / `MONIQ_SMTP_PORT` | Authenticated email; TLS 465 or STARTTLS 587 |
| `MONIQ_SMTP_USER` / `MONIQ_SMTP_PASSWORD` / `MONIQ_MAIL_FROM` | Backend-only credentials and verified sender |
| `MONIQ_MAIL_TRANSPORT` / `MONIQ_MAIL_API_KEY` | `resend` + private HTTPS provider key on Render Free; or `smtp` with TLS credentials on a permitted network |
| `MONIQ_HOSTED_GMAIL_ENABLED` | `false` until private account/OAuth validation |
| `HOSTED_GMAIL_CLIENT_ID` / `HOSTED_GMAIL_CLIENT_SECRET` | Backend-only Google Web application credentials |
| `HOSTED_GMAIL_TOKEN_ENCRYPTION_KEY` | New stable Fernet key, securely backed up separately from database |

Private startup fails closed without HTTPS, PostgreSQL, key material, TLS mail, allowlist and both gates. Gates are operational attestations, not proof established by flipping a flag. Validate a separate test environment first. Public financial signup remains closed.

Store keys directly in private environment fields or a secrets manager. Never show them in chat, screenshots, CI artifacts or Git. Existing `.env`/local encryption key were not modified. Do not replace the local key with the hosted key. Get approval for paid database/email resources.

After persistence/recovery validation, send a test invitation from an authorized admin checkout:

```powershell
.\.venv\Scripts\python.exe scripts\hosted-admin.py invite your-authorized-test-address@example.com
```

Invitation expires after an hour and is emailed, never printed. Redemption verifies email before login. Recovery links expire after twenty minutes and use URL fragments to avoid access logs; responses are generic and delivery runs after the response.

## Exact Google Cloud settings

Use a **Web application** OAuth client in `Moniq-Test` (`moniq-test-511217`). Authorized JavaScript origins are not required. For the current app add:

```text
https://moniq-80su.onrender.com/api/gmail/callback
```

Keep local development:

```text
http://127.0.0.1:8000/api/gmail/callback
```

A separate test service needs its own exact HTTPS origin plus `/api/gmail/callback`. The backend uses the fixed validated origin, never an incoming Host header. No wildcards. Under Data Access configure only:

```text
https://www.googleapis.com/auth/gmail.readonly
```

Keep External and Testing. Add identical approved addresses to Google Test users and the backend allowlist. Selected Google mailbox must match Moniq login. Hosted credentials use `HOSTED_GMAIL_CLIENT_ID`/`HOSTED_GMAIL_CLIENT_SECRET`; localhost retains existing `GMAIL_*` variables/callback.

Google [External Testing allows at most 100 explicit test users](https://developers.google.com/identity/protocols/oauth2/production-readiness/overview). [Testing refresh tokens normally expire after seven days](https://developers.google.com/identity/protocols/oauth2), requiring reconnection. [Gmail read-only is restricted](https://developers.google.com/workspace/gmail/api/auth/scopes): public access needs brand/scope verification; server-side restricted-data storage/transmission needs a security assessment unless Google grants an exception. Prepare a verified domain, privacy policy, terms, retention/deletion policy and verification demonstration before general public access. No verification was submitted or claimed.

## Existing records and recovery

Local databases, balances and encrypted local Gmail tokens remain untouched. New users start empty. Personal data migration is explicit, never automatic.

Back up local SQLite while Moniq is stopped and back up PostgreSQL. Verify destination ownership, create the invited account, and keep its private site unavailable during the copy. Review a read-only dry run:

```powershell
.\.venv\Scripts\python.exe scripts\import-private-workspace.py --source D:\Map\Moniq\.runtime\personal.db --email your-authorized-test-address@example.com
```

The tool refuses synthetic sources and destinations with financial records. It prints counts only. Add `--copy` after reviewing backups/ownership: copying is transactional, preserves cents/IDs/dates/fingerprints/audit rows and adjusts serial sequences. Source opens read-only. Gmail token files are never copied; reconnect in the verified hosted account. Compare balances privately. No real-data copy was executed.

Required rollout drills:

1. Check cross-user read/write/export/delete/approval isolation, demo isolation, invitations, login/logout, idle/absolute expiry, Origin/CSRF, rate limits, recovery and session/OAuth revocation using synthetic testers.
2. Write synthetic accounts, approvals, Circles and SmartApprove into intended PostgreSQL. Restart app and test database; verify balances/vault decryption without printing credentials.
3. Encrypt a `pg_dump` backup containing identity/all schemas; retain keys separately. Restore into a new isolated database, verify migrations, synthetic balances and vault decryption. Never overwrite live database for a drill. Establish scheduled backups, retention and monitoring before real data.
4. Validate real TLS email delivery/recovery using an approved address. After readiness gates, invite only approved users. Register starting balances/dates, complete Google consent with matching mailbox, sync and review Overview approvals. Check forecasts, deduplication and audit.
5. Disconnect deletes only owning user's token and requests Google revocation; check remote revocation if Google is unavailable. `hosted-admin.py revoke-sessions EMAIL` revokes sessions while retaining history. Preserve stable keys; unplanned replacement makes tokens unreadable.
6. Review source, secrets, tests and costs. Obtain push/deployment approval. Keep Hacklanta demo until preview passes; retain previous commit/configuration for rollback. Never destructively downgrade migrations.

## Local validation

```powershell
cd D:\Map\Moniq
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check backend tests scripts
npm --prefix frontend run typecheck
npm --prefix frontend run lint
npm --prefix frontend run build
npm --prefix frontend run test:e2e
npm --prefix frontend run test:public
npm --prefix frontend run test:hosted
```

PostgreSQL fixture requires a disposable loopback admin URL to `postgres`, creates unique `moniq_test_*` databases and removes them afterward:

```powershell
$env:MONIQ_TEST_POSTGRES_URL='postgresql+psycopg://TEST_USER:TEST_PASSWORD@127.0.0.1:5432/postgres'
.\.venv\Scripts\python.exe -m pytest -q tests/test_hosted_accounts.py
Remove-Item Env:MONIQ_TEST_POSTGRES_URL
```

`test:hosted` starts/stops `serve-hosted-test.py`, a localhost-only self-signed HTTPS fixture with synthetic identities. It never enables real Gmail/owner records, requires an explicit test flag and must never be deployed. Existing local development/Gmail commands are unchanged.

Real hosted Gmail is **not yet validated**: staging approval, durable cloud PostgreSQL, real SMTP recovery, stable keys, Google redirect configuration and human consent remain necessary. Mocked OAuth cannot establish a real inbox connection.
