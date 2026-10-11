# Render readiness and privacy audit

Verified locally on October 11, 2026. No GitHub push or Render deployment was performed during this audit. Application features, existing databases, credentials, encryption keys, and financial records were preserved.

## Source and secret scan

The starting commit was `7427f7efb8e71210268fe77aa9462c5c8ff0c37d`, already published on `origin/main`. A fresh fetch verified the official remote, `https://github.com/ReddyR1105/Moniq.git`, with no unexpected remote commits.

Gitleaks 8.30.1 was downloaded from its official release and verified against the published SHA-256 checksum. Scans used full redaction, default detection rules, recursive archive/encoding inspection, and no inline suppressions. Coverage included all three existing commits across refs and reflogs, every local Git blob (319 objects, including 31 unreachable objects), all 213 current tracked files, the complete filtered Docker build context, and the rebuilt production frontend assets. A separate private-key/provider-token pattern scan checked every blob, including binary content. The final deployment changes are scanned again before and after the local readiness commit.

No confirmed credentials were found. Gitleaks reported one false positive in `docs/CIRCLES_SMARTAPPROVE.md`, line 49: prose about local workspace restrictions and future authentication requirements. The history, object, and current-source reports all refer to that same harmless sentence. The Docker context and production frontend assets had zero findings. No detection rule was disabled to conceal this result.

Historical file trees contain no private environment files, databases, token vaults, private keys, or runtime directories. Local private files were checked for exclusion without opening their contents. The filtered build context contained 104 files, all tracked source. Audit tools, raw reports, isolated test databases, and downloaded Linux wheels remain Git-ignored under `.tools` and `.runtime`.

## Public demo isolation

The Render Blueprint and Docker defaults enable public demo mode, disable Gmail, use secure cookies, and serve the frontend with the API on one origin. No Gmail credentials, financial database URLs, encrypted tokens, or secret environment variables are defined in the Blueprint.

Public mode ignores Gmail credentials even if they are accidentally supplied as environment variables. Gmail authorization, callback, sync, account, and disconnect routes are blocked. Private workspace selection is blocked, and database helpers reject private access. Visitors receive separate temporary synthetic databases; owner workspace cookies cannot switch a public visitor to an owner's data. The public classifier uses a separate immutable synthetic model, and uploads/shared retraining are disabled. The service worker caches static assets only.

A fresh process was tested against a clean image-equivalent copy containing only the runtime backend, synthetic dataset, and built frontend. Synthetic Gmail credentials and private database paths were injected deliberately. Startup and requests made zero private database connections and zero Gmail manager calls. HTTPS cookies were Secure, HttpOnly, and SameSite=Lax. Private source/environment/database paths returned HTTP 404; Gmail/private workspace routes returned HTTP 403. A purchase changed only its own visitor's balance.

## Deployment configuration and tests

- `render.yaml` passes Render's official JSON Schema. It specifies a Free Docker web service, one instance, manual deployments, `/api/health`, and public-demo-only environment settings.
- Dockerfile lint passes Hadolint 2.15.1 with zero findings. The existing non-root account is selected by UID 10001, and the health check uses JSON command syntax. The multi-stage build, locked dependencies, runtime file copies, dynamic port, and single worker are preserved.
- `.dockerignore` now also excludes nested environment files, logs, and stale pytest temporary directories. Private databases, encrypted tokens, keys, runtime directories, Git metadata, and local tools remain excluded.
- All 43 locked backend dependencies have downloadable Linux x86-64 CPython 3.14-compatible wheels. This checks package availability, not actual Linux installation or execution.
- Backend: **112 passed**, with two upstream deprecation warnings.
- Frontend: type checking, lint, and production build passed.
- Production Chromium: **8 passed**, covering visitor isolation, public policy, mobile interactions, PWA installability, and static-only offline caching.
- Python lint, GitHub Actions syntax validation, and Git whitespace checks passed.

## Remaining deployment gate

Docker is not installed on this machine. An actual container build, non-root Linux startup, Render resource usage, and the assigned public HTTPS URL have therefore **not** been verified. This audit is readiness evidence, not a claim that deployment has succeeded.

On a machine with Docker, after reviewing the local deployment commit:

```powershell
cd D:\Map\Moniq
docker build -t moniq-demo .
docker run --rm -p 127.0.0.1:8080:8080 -e MONIQ_COOKIE_SECURE=false -e MONIQ_PUBLIC_ORIGIN=http://127.0.0.1:8080 moniq-demo
```

Check `http://127.0.0.1:8080/api/health`, then exercise two independent browser profiles. Render creation/deployment still requires owner approval. Use the existing [deployment instructions](DEPLOYMENT.md); do not upload `.env`, Gmail secrets/tokens, or private databases. Keep one worker and one instance. Public demo storage is temporary and synthetic; Gmail remains available only in the existing private local application.

References: [Render Blueprint specification](https://render.com/docs/blueprint-spec), [Render Docker hosting](https://render.com/docs/docker), [Gitleaks](https://github.com/gitleaks/gitleaks), [Hadolint](https://github.com/hadolint/hadolint).
