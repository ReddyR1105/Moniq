# Run and submit Moniq

**Name:** Moniq. **Tagline:** Spending, Made Smarter. **Main track:** Fintech.

## Exact commands in the current workspace

Backend, PowerShell terminal 1:

```powershell
cd D:\Map\Moniq
powershell -ExecutionPolicy Bypass -File .\scripts\start-backend.ps1
```

Frontend, PowerShell terminal 2:

```powershell
cd D:\Map\Moniq
powershell -ExecutionPolicy Bypass -File .\scripts\start-frontend.ps1
```

Open http://127.0.0.1:5173 . No signup or credentials. Backend health: http://127.0.0.1:8000/api/health . Use Settings → Reset Demo before the guided walkthrough. The README documents clean-checkout setup and direct cross-platform commands.

Run all non-browser checks:

```powershell
cd D:\Map\Moniq
powershell -ExecutionPolicy Bypass -File .\scripts\check.ps1
```

Run the actual browser acceptance suite (Edge installed):

```powershell
cd D:\Map\Moniq
$env:PATH = 'D:\Map\Moniq\.tools\node-v24.21.0-win-x64;' + $env:PATH
& '.\.tools\node-v24.21.0-win-x64\npm.cmd' --prefix frontend run test:e2e
```

Browser tests manage their own local test servers; leave ports 8001/5174 free. Test databases and trained models are ignored runtime files. Stop interactive servers with Ctrl+C. Never use real banking passwords or actual bank statements for a public demo.

## Submission package

Use `DEVPOST_SUBMISSION.md` for the description, `DEMO_SCRIPT.md` for a short screen recording, `JUDGING_PREP.md` for live questions, `ARCHITECTURE.md` for APIs/providers, `FEATURE_AUDIT.md` for implemented/optional scope, and `QA_REPORT.md` for measured validation. `SUBMISSION_CHECKLIST.md` separates local deliverables from manual publishing/registration/media-upload/submission tasks.

Team roster, hacking-window verification, adding narration and uploading the included video, approving source publication, and confirming the Devpost submission remain manual. **No GitHub push is authorized by this run guide and no push has been performed.**

For Chromium validation and real UI media capture, see `DEMO_WALKTHROUGH.md`. Publication commands are in `GITHUB_PUBLICATION.md`; do not execute the push until the owner approves. Clean source/media ZIP: `D:\Map\Moniq-submission.zip`.

## One-service browser testing

```powershell
cd D:\Map\Moniq
powershell -ExecutionPolicy Bypass -File .\scripts\start-public-demo.ps1
```

Open http://127.0.0.1:8080. This uses temporary synthetic sessions per browser profile, blocks personal statements and free-form personal text, and does not change the persistent local database. Render account authentication, GitHub connection and deployment approval are still required for a public URL. See DEPLOYMENT.md.

Official origin: https://github.com/ReddyR1105/Moniq.git. The local commit is ready for review; only after final push approval run `git push -u origin main`. Inspect the real Actions run afterward.
