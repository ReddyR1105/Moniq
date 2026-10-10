# Final Moniq demo scripts and media

The final presentation and full walkthrough are actual Playwright/Chromium recordings at 1920 x 1080, encoded as H.264 MP4 with AAC local Windows narration. Captions are burned into the recording and also available as SRT/VTT. No music or personal Gmail content is used.

- `docs/demo/Moniq_Hacklanta_Final.mp4`: concise Hacklanta presentation.
- `docs/demo/Moniq_All_Features.mp4`: complete feature walkthrough.
- Matching `_NARRATION.md`, `.srt` and `.vtt` files contain the actual timed scene text.
- `QA_REPORT.md` records measured media durations and full decoding checks.

## Story and operator cues

Start the explicitly isolated scenario with $10. Use the dashboard's synthetic $400 paycheck and $15 purchase buttons. Read extracted fields, verify posted status and confirm each; show $410 then $395. Open Settings to show trusted-sender restrictions and audit history. Process the controlled $40 dinner, link it to an equal two-person Circle, and record the $20 confirmed repayment. The resulting checking cash is $375, monthly personal spending $35 and paycheck income $400; debt is zero. The earlier $395 figure precedes the dinner and repayment.

The extended recording also demonstrates disconnected Gmail controls, savings account setup, a linked debit card, internal transfer/reconciliation, actual transactions, synthetic CSV preview/import, category correction, monthly/weekly budgets, forecasts/scenario assumptions, contribution plans, subscriptions, grounded questions, sample offers and safe reset. Returning to the ordinary synthetic demo loads its separate seeded student history; do not compare that balance to the controlled scenario.

## Reproducing media safely

Use `scripts/start-backend.ps1 -Port 8004` and `scripts/start-frontend.ps1 -Port 5175 -ApiTarget http://127.0.0.1:8004` with recording-specific database/model/token directories under `.runtime/final-recording*`, `CORS_ORIGINS=http://127.0.0.1:5175`, `GMAIL_FRONTEND_URL=http://127.0.0.1:5175` and **MONIQ_GMAIL_DISABLED=true**. Never reuse the owner's databases or token directory for recording. The recorder checks that Gmail is unconfigured and disconnected before resetting only its synthetic workspace.

`node scripts/record-final-demo.mjs presentation` or `walkthrough` captures real navigation and backend responses. `MONIQ_RECORD_FAST=1` is preflight only; the finishing scripts refuse to publish fast footage. `scripts/narrate-demo.ps1 -Mode presentation` creates local speech; `scripts/finish-demo-video.py presentation --ffmpeg <local-ffmpeg-path>` encodes and completely decodes the result. Repeat for walkthrough. Windows speech voices/FFmpeg are optional media tools, not application runtime dependencies. Raw browser footage and WAV intermediates remain ignored in `.runtime/`.

## Upload and Devpost instructions

1. Review both MP4s and their captions locally. Use the short presentation as the main Devpost demo; the longer walkthrough can be supplementary.
2. Sign into your own YouTube or another Devpost-supported video host. Upload the MP4 as Public or Unlisted, with title "Moniq - Spending, Made Smarter. | Hacklanta 2026 Fintech". Avoid Private visibility.
3. Add the supplied SRT captions if the host supports them. Description: actual prototype, synthetic data, estimated balances, no banking/payment service. Link the official repository.
4. Wait for processing. Open the video URL in a signed-out/private browser and verify playback, readability and audio. Confirm the repository's final approved source is accessible too.
5. Paste the actual video URL into Devpost. Keep media accessible through judging, complete all fields, and verify submission receipt before the deadline. No upload or submission has been performed by Codex.
