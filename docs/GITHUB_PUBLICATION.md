# Moniq GitHub publication

The existing repository is `D:\Map\Moniq`, branch `main`, with origin **https://github.com/ReddyR1105/Moniq.git**. `git ls-remote --heads --tags` confirmed no remote refs before preparing publication. No history was replaced, no second repository was initialized, and nothing has been pushed. A reviewed local commit is prepared by the finalization task using the configured real Git author.

Source, tests, documentation, pinned-action CI, deployment configuration, ten screenshots and the actual synthetic demo recording belong in the commit. `.env.example` contains blank optional keys. `.env`, private databases, trained models, caches, tool binaries, virtual environments, dependencies, test traces and production build output are excluded. `scripts/package_submission.py` checks common credential patterns and verifies ZIP CRCs and every file hash. This scan is not a guarantee against every possible secret.

## Final owner approval required before push

After approving publication, run these exact PowerShell commands:

```powershell
cd D:\Map\Moniq
git status --short
git log -1 --oneline
git remote -v
git ls-remote --heads --tags origin
git push -u origin main
```

The destination must still be `https://github.com/ReddyR1105/Moniq.git`. If someone added remote commits in the meantime, fetch/review/reconcile that history before pushing. Never force-push. Git Credential Manager may open GitHub authentication; use the owner's account and authorize this repository. No access token belongs in source or a frontend variable.

After the approved push, visit [Moniq Actions](https://github.com/ReddyR1105/Moniq/actions), inspect the first **Moniq CI** run, and verify actual Linux pytest/Ruff/ML/types/ESLint/build/local Chromium/public-production Chromium success. Local checks and actionlint do not count as a hosted Actions pass. Fix any real CI failures before claiming success.

Check [the repository](https://github.com/ReddyR1105/Moniq) from a signed-out browser. Confirm README, installation instructions and source are public. Upload the video to an accessible player, verify it, and add the exact links to Devpost. Cloud deployment is a separate approval/account step described in [DEPLOYMENT.md](DEPLOYMENT.md).
