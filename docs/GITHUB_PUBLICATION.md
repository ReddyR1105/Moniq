# Moniq GitHub publication

The existing repository is `D:\Map\Moniq`, branch `main`, with origin **https://github.com/ReddyR1105/Moniq.git**. The approved baseline `8ac182f` was previously published with passing hosted CI. The local Gmail/SmartApprove/Circles finalization commit is `d2ad580`; subsequent presentation, PWA and premium-video changes are currently local working-tree updates. No newer push has occurred. No history was replaced or second repository initialized.

Source, tests, documentation, pinned-action CI, deployment configuration, ten screenshots and the actual synthetic demo recording belong in the commit. `.env.example` contains blank optional keys. `.env`, private databases, trained models, caches, tool binaries, virtual environments, dependencies, test traces and production build output are excluded. `scripts/package_submission.py` checks common credential patterns and verifies ZIP CRCs and every file hash. This scan is not a guarantee against every possible secret.

## Final owner approval required before push

First review the premium video, final source diff and secret-scan/package results. The following commands prepare the currently verified local updates as a commit; they do not publish:

```powershell
cd D:\Map\Moniq
git status --short
git diff --check
git add -- .dockerignore Dockerfile README.md backend docs frontend render.yaml scripts tests
git diff --cached --stat
git commit -m "Prepare Moniq PWA and neural Hacklanta demo"
git log --oneline -2
```

Review all commits that will be published, including the earlier local `d2ad580`. Only after explicit approval for those commits, run:

```powershell
cd D:\Map\Moniq
if (git status --porcelain) { throw 'Working tree is not clean' }
if ((git remote get-url origin) -ne 'https://github.com/ReddyR1105/Moniq.git') { throw 'Unexpected remote URL' }
git fetch origin
if ($LASTEXITCODE -ne 0) { throw 'Remote verification failed' }
if ((git rev-list --count HEAD..origin/main) -ne '0') { throw 'Unexpected remote commits; review and reconcile before pushing' }
git log --oneline origin/main..HEAD
git push -u origin main
```

The destination must still be `https://github.com/ReddyR1105/Moniq.git`. If someone added remote commits in the meantime, fetch/review/reconcile that history before pushing. Never force-push. Git Credential Manager may open GitHub authentication; use the owner's account and authorize this repository. No access token belongs in source or a frontend variable.

After the approved push, visit [Moniq Actions](https://github.com/ReddyR1105/Moniq/actions), inspect the first **Moniq CI** run, and verify actual Linux pytest/Ruff/ML/types/ESLint/build/local Chromium/public-production Chromium success. Local checks and actionlint do not count as a hosted Actions pass. Fix any real CI failures before claiming success.

Check [the repository](https://github.com/ReddyR1105/Moniq) from a signed-out browser. Confirm README, installation instructions and source are public. Upload the video to an accessible player, verify it, and add the exact links to Devpost. Cloud deployment is a separate approval/account step described in [DEPLOYMENT.md](DEPLOYMENT.md).

These publication commands were prepared, not executed for the current working-tree changes. Current local checks pass 112 backend tests and 24 browser tests; hosted CI for the new release remains pending an approved push. The preserved original ZIP is `Moniq_Hacklanta_Final.zip`; the latest verified source, presentation and premium media are packaged separately as `Moniq_Hacklanta_Premium.zip`.
