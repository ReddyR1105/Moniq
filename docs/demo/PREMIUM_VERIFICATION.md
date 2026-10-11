# Premium narration and final video

Output: `D:\Map\Moniq\docs\demo\Moniq_Hacklanta_Premium_Final.mp4`.

The edit uses entirely new `en-US-AndrewMultilingualNeural` speech generated through Microsoft's Edge online speech service with edge-tts 7.2.3. The service identifies this as an American English neural voice with confident, casual and warm personality metadata. Synthesis rate is **+15%**. The voice is not Zira, and the audio is not accelerated from an old recording. No paid service, subscription, API credentials or purchase was used. Only synthetic product narration is sent for synthesis.

The revised conversational script is in `premium-plan.json` and `Moniq_Hacklanta_Premium_Final_NARRATION.md`. Moniq is pronounced **moh-NEEK** using “Monique” in synthesis text; SmartApprove uses “Smart Approve,” and Gmail uses “G mail.” Displayed captions preserve the official names. Final pronunciation, perceived age, warmth and energy require the owner's listening review; automated checks do not replace listening.

## Actual media checks

- **90.00 seconds**, 1920×1080, H.264 at 30 fps, AAC mono at 48 kHz; fast-start MP4.
- Newly captured working React/FastAPI interface in isolated synthetic databases, with Gmail explicitly disabled. Browser assertions verify $10 → $410 → $395, the controlled $40 alert, $20 Circles debt, and a repayment resulting in $375 cash / $400 income / $35 personal spending.
- Review and automation actions are held to the neural sentence timestamps. Extracted purchase fields remain visible during narration of the review, then confirmation updates the balance. The repayment scene shows unchanged paycheck income.
- **37 regenerated sentence caption cues**, burned into a reserved area below the application, plus separate SRT and VTT files. Caption timings remain within their scenes, ordered and non-overlapping. Branding and synthetic-data disclosure have a separate header.
- All video/audio streams completely decode without errors. Chromium loads the video at readyState 4, decodes audio and frames, seeks across early/middle/ending frames of all 11 scenes (**33 seeks**), and reaches the ending without media/page errors.
- Two-pass volume normalization targets -16 LUFS with peak headroom. Final measured narration is approximately **-16.2 LUFS**, **-1.48 dB true peak**, with **3 LU** loudness range and no detected silence longer than **0.82 seconds** at the -45 dB threshold. Scene transitions use brief fades. No music was added.
- Representative frames were visually inspected for readable captions, correct figures and synchronization. Subjective voice quality remains an owner listening check.

Machine-readable evidence and 33 full-resolution checked frames are in ignored `.runtime/premium-recording/`: `verification.json`, `browser-playback.json`, `audio-caption-verification.json`, `edit-timeline.json`, `voice-metadata.json` and `verified-*.png`. Final hashes are also in the media verification JSON and submission package manifest.

## Preserved originals

`Moniq_Hacklanta_Premium_Final.mp4` did not exist when this task began. The prior recordings remain unchanged in this folder:

| Original | SHA-256 |
| --- | --- |
| Moniq_Hacklanta_Final.mp4 | `5fc65d3fa289f0aa7065d43db103a5320e96b3e3b65e63cec3b3308c5f3066a5` |
| Moniq_All_Features.mp4 | `bf04765f005c37c36cf0847a62d7bd7081df05bf830bd6b65c8f2ea5d2db243c` |

Original WebM recordings, screenshots, judging presentation and the previous `D:\Map\Moniq_Hacklanta_Final.zip` are preserved. Intermediate premium cuts and raw capture/audio remain local runtime assets, excluded from Git and submission packages.

## Reproduction in this prepared workspace

Use separate local recording servers on **8004/5175**. In the backend terminal set `MONIQ_GMAIL_DISABLED=true`, `MONIQ_PUBLIC_DEMO=false`, recording-only `DATABASE_URL`, `PERSONAL_DATABASE_URL`, `SCENARIO_DATABASE_URL`, model/token directories under `.runtime/premium-recording/`, and `CORS_ORIGINS=http://127.0.0.1:5175`. Start `.venv/Scripts/python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8004`. In a second terminal, set `MONIQ_API_TARGET=http://127.0.0.1:8004` and start the frontend on 5175. Never reuse the owner's personal databases or token directory. The recorder refuses a configured/connected Gmail environment.

After those isolated servers are ready:

```powershell
cd D:\Map\Moniq
$env:PYTHONPATH='D:\Map\Moniq\.tools\neural-tts'
$env:PLAYWRIGHT_BROWSERS_PATH='D:\Map\Moniq\.tools\playwright-browsers'
$env:MONIQ_PREMIUM_FAST='0'
.\.venv\Scripts\python.exe scripts\generate-premium-narration.py
.\.tools\node-v24.21.0-win-x64\node.exe scripts\record-premium-demo.mjs
$moniqFfmpeg='D:\Map\Moniq\.tools\video-python\imageio_ffmpeg\binaries\ffmpeg-win-x86_64-v7.1.exe'
.\.venv\Scripts\python.exe scripts\render-premium-demo.py --ffmpeg $moniqFfmpeg
.\.tools\node-v24.21.0-win-x64\node.exe scripts\verify-premium-playback.mjs
.\.venv\Scripts\python.exe scripts\verify-premium-audio.py --ffmpeg $moniqFfmpeg
```

Optional media tooling is separate from app runtime dependencies. `.tools/neural-tts` contains the installed free speech client; a fresh checkout would need an explicit `pip install --target .tools/neural-tts edge-tts==7.2.3`, FFmpeg and Playwright Chromium before reproducing media. Neural synthesis requires network access. Do not substitute Windows speech if the neural service is unavailable. A fast recorder preflight is not a final video and is rejected by the renderer.

No GitHub push, public video upload, Render deployment or Devpost submission has occurred for this work. Review and approve the premium cut locally before any external publication.
