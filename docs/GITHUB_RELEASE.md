# Moniq final local release

Official origin: `https://github.com/ReddyR1105/Moniq.git`.

The published baseline is `8ac182fc7e024305c80fbf4f242cb22a8a4b09dd`. Remote history was fetched and contained no unexpected commits. The final release preserves that history; its new local commit/hash is reported in the final handoff. Secrets, tokens, private databases, dependencies, build output and raw footage are excluded. Every new publication still requires owner approval.

## After explicit push approval

```powershell
cd D:\Map\Moniq
git status --short
git remote get-url origin
git fetch origin
git log --oneline --left-right HEAD...origin/main
# Proceed only if the tree is clean and origin/main is the expected baseline.
git push origin main
```

Use a normal fast-forward push only. If the remote has changed, inspect and resolve it before pushing; do not force-push or overwrite history.

Open https://github.com/ReddyR1105/Moniq/actions after pushing. The pinned CI workflow runs locked dependency installation, backend tests, Ruff, independent ML reproduction, TypeScript, ESLint, production build and both Chromium suites. Verify that the workflow's head SHA matches the approved local commit. If CI fails, diagnose, make local fixes and run affected checks; request approval before another push.

The currently hosted baseline CI passed: https://github.com/ReddyR1105/Moniq/actions/runs/38068681424. Final-release hosted CI has not started because no new push has been approved or executed. Render deployment and Devpost submission are separate approvals.
