# Browser testing and optional free hosting

The existing React and FastAPI app can run as one service: FastAPI serves the built frontend and `/api`. No API key or paid service is required. No cloud service has been created and no public demo URL exists yet.

## Test the production demo locally

From PowerShell on this prepared workspace:

```powershell
cd D:\Map\Moniq
powershell -ExecutionPolicy Bypass -File .\scripts\start-public-demo.ps1
```

Open **http://127.0.0.1:8080**. This builds the frontend, starts one FastAPI process, and uses HTTP localhost cookies. Stop with Ctrl+C. Use separate browser profiles or private windows to test independent visitors; tabs in one browser profile intentionally share one session. Personal CSV uploads and free-form personal fields are disabled. The built-in sample statement uses the original CSV pipeline. For local custom CSV/message/profile inputs and persistent data, use the two-server README instructions instead.

## Session behavior

`MONIQ_PUBLIC_DEMO=true` selects an isolated SQLite database per opaque 256-bit cookie. Cookies are HttpOnly and SameSite=Lax, and Secure on HTTPS hosting. All session-scoped endpoints, including export, edits, deletion and reset, use that visitor's database. No real identity or bank integration is implemented. This is suitable for fictional sample testing only, not personal financial accounts.

Names, descriptions, merchants, notification text, questions and other free-text writes are constrained to built-in synthetic examples by the backend as well as the UI. Numerical financial experiments and enumerated preferences remain editable. Upload routes reject personal files before CSV parsing. Public predictions use a separate immutable baseline; correction records remain in the visitor's database, and shared retraining is disabled. Local functionality is preserved.

Sessions last at most the cookie's two-hour lifetime; inactive server entries expire after two hours. Reloading an expired session bootstraps fresh sample data. A maximum of 100 sessions per process bounds resource usage; a full service returns an explicit retry message. Same-visitor requests are serialized. All data disappears after a process restart, deployment, or free-host storage reset. This is **temporary demo storage**, not persistent cloud storage. Existing local financial databases are never included in the image.

Use exactly **one process and one instance**: the registry is in memory. Do not add workers or horizontal replicas without redesigning session storage. The demo has no production authentication or anti-abuse service. Request bodies are bounded to 8 KB in public mode. Browser requests must use the same origin; `RENDER_EXTERNAL_URL` supplies the expected hosting origin automatically.

## Render deployment, pending owner approval

[Render Free services](https://render.com/docs/free) support Docker/Python web services. Free services sleep after 15 idle minutes, can take about a minute to wake, and lose local filesystem changes on restart/redeploy/spin-down. Free limits apply; do not enable a paid plan, paid disk, or paid overages. The free tier is suitable for a demonstration with a warm-up before judging, rather than guaranteed uptime.

The root `Dockerfile`, `.dockerignore`, and `render.yaml` prepare a single-origin service with a non-root runtime, one worker/instance, a free plan, manual deployments and `/api/health`. React is built from its lockfile in a Node 24 stage; the Python 3.14 stage installs locked dependencies and copies only backend, synthetic data and frontend assets. Container tooling is unavailable in this workspace, so an actual Docker build and Render startup still need verification. The equivalent production-serving path has automated local Chromium coverage.

After explicit GitHub push and deployment approval:

1. Sign in to or create a Render account and authorize access to `ReddyR1105/Moniq`.
2. Create a Blueprint from the approved `main` branch and root `render.yaml`. Check the proposed service is **Free**, one instance, with no persistent disk or paid resource.
3. Approve creation/deployment. Review the real build/start logs and `/api/health`; do not call deployment successful until they pass.
4. Open the assigned HTTPS URL in two separate browser contexts. Complete Start Demo, save $15.75, verify the other visitor is unchanged, run a $150 scenario, use deals/assistant, import the synthetic CSV, export and reset. Check mobile and session expiry.
5. Enter the real working URL into README/Devpost only after those checks. Wake the service shortly before judging. Keep local instructions available if free hosting sleeps or reaches quota.

The exact external step awaiting the owner is account authentication/authorization and approval to create the service. No paid resources, cloud deployment, public URL, or persistence guarantee have been claimed. See [Render's FastAPI guide](https://render.com/docs/deploy-fastapi) and [Blueprint specification](https://render.com/docs/blueprint-spec).

With Docker installed, a local image smoke check can use:

```powershell
docker build -t moniq-demo .
docker run --rm -p 127.0.0.1:8080:8080 -e MONIQ_COOKIE_SECURE=false -e MONIQ_PUBLIC_ORIGIN=http://127.0.0.1:8080 moniq-demo
```

These Docker commands are prepared instructions, not executed results.
