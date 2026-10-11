# Moniq judging presentation — verification

Verified **October 10, 2026** in `D:\Map\Moniq`. The existing application commit is `d2ad5807e41e5533c6d4180ea1f1b1bed17e11e1`; presentation files and a work-disclosure addition are subsequent local changes. No push, deployment or Devpost submission occurred.

| Check | Actual result |
| --- | --- |
| Editable main deck | **8 slides**, 16:9; native PowerPoint text/shapes and raster app screenshots |
| Separate technical backup | **2 slides**, separate editable deck and PDF |
| Native rendering/export | **Microsoft PowerPoint 16.0** exported both PDFs and all ten 1920×1080 PNG previews |
| PowerPoint text bounds | **No overflowing text boxes** in either final deck; initial layout issues corrected and re-exported |
| PDF | 8 main pages / 2 backup pages; widescreen, extractable text, embedded fonts |
| Structural checks | PPTX ZIP integrity, slide dimensions, notes, on-canvas shapes, full-HD previews and local links verified |
| Visual review | All 8 main slides and both backup slides inspected; final screenshot crops inspected again |
| Branding | Moniq, “Spending, Made Smarter.”; existing app cream/green palette and Segoe UI |
| Script timing | **373 spoken words**, about 149 s at 150 wpm or 172 s at 130 wpm; target **2:40** with transitions at the intended pace |
| Quick pitch | **143 spoken words**, about **57.2 seconds at 150 wpm**, leaving a brief transition pause |
| Sensitive information | XML/Markdown credential-pattern checks pass; pictures are visibly synthetic, including reserved `.test` sender and dummy last four 1234 |
| Existing media | Both MP4 files exist and match previously verified SHA-256; 2:21.32 presentation / 6:38.64 walkthrough preserved |
| Backend rerun | **109 passed**, 32.90 s; two existing upstream Starlette/Authlib compatibility deprecation warnings |
| Local Chromium rerun | **16 passed**, 104.02 s; 0 failed / flaky / skipped |
| Production Chromium rerun | **3 passed**, 32.45 s; 0 failed / flaky / skipped |
| Independent ML rerun | **250/264 correct**, 94.69697% raw synthetic accuracy; saved baseline matches; no app classifier/cache reused |
| Working source | No application-code changes; only presentation material and `docs/WORK_DISCLOSURE.md` added/updated |

The slide-four amounts are backed by the existing tested synthetic parser/confirmation/ledger workflow; recording frames show the actual purchase review and $395 result. The slide-five $40/$20/$20 split is an actual synthetic Circles UI capture. Screenshots may contain small secondary labels; editable slide text repeats the key amounts and conclusions at projector-readable sizes. No live Gmail messages or authoritative bank balances are displayed.

The raw ML score describes held-out synthetic descriptions before the uncertainty fallback. It is not real-world email accuracy. Automatic coverage is 58.71% on this set, confidence is uncalibrated and formatting variants are correlated; the technical backup and judges' Q&A explain these limits. The 19 browser tests are local verified results, not a claim of hosted CI for the unpublished final application commit.

## Official requirements reviewed

The [Devpost overview](https://hacklanta.devpost.com/) and [rules](https://hacklanta.devpost.com/rules) establish the deadline, registration, work/disclosure and required submission artifacts. The [organizer website](https://hacklanta.dev/) explicitly lists Fintech and in-person participation. Devpost's exact judging criteria remain marked **TBA at Opening Ceremony**; general considerations appear in the rules. No scoring percentages or official pitch length were invented.

Technical preparation passes; eligibility and submission completion cannot be certified from local files. See [manual checklist](MANUAL_SUBMISSION_CHECKLIST.md). The team must verify work within the official hacking period, replace presenter placeholders, approve source publication, upload the required video and complete Devpost. A deck is additional judging material and does not replace the demo video.

## Reproduce checks

```powershell
cd D:\Map\Moniq
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe scripts\reproduce_ml.py --check
$env:PATH='D:\Map\Moniq\.tools\node-v24.21.0-win-x64;'+$env:PATH
$env:PLAYWRIGHT_BROWSERS_PATH='D:\Map\Moniq\.tools\playwright-browsers'
$env:MONIQ_BROWSER='chromium'
$env:MONIQ_GMAIL_DISABLED='true'
npm.cmd --prefix frontend run test:e2e
npm.cmd --prefix frontend run test:public
$env:PYTHONPATH='D:\Map\Moniq\.tools\presentation-python'
.\.venv\Scripts\python.exe docs\presentation\verify_presentation.py
```

Tests use isolated stores; the owner Gmail connection and databases were not reset or synchronized. `MONIQ_GMAIL_DISABLED` above affects child processes of this terminal, not already running owner servers. PowerPoint's native bound reports, generated-file hashes, browser result timestamps and estimated pitch times are in [`verification.json`](verification.json). The verifier is designed for this uncommitted presentation handoff; after committing, its expected tracked-diff assertion must be updated.

The previous `D:\Map\Moniq_Hacklanta_Final.zip` remains intact and does not contain these later presentation additions. Rebuild it after approving the final presenter details if desired.
