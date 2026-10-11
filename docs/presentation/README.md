# Moniq — Hacklanta 2026 judging presentation

- [Main editable PowerPoint](Moniq_Hacklanta_2026_Pitch.pptx) — **8 slides, 16:9**.
- [Main PDF](Moniq_Hacklanta_2026_Pitch.pdf) — native Microsoft PowerPoint export.
- [Slide-by-slide speaking script](PRESENTATION_SCRIPT.md) — target **2:40**.
- [60-second pitch](QUICK_PITCH.md).
- [18 judges' questions](JUDGES_QA.md).
- [Separate engineering backup PowerPoint](Moniq_Technical_Backup.pptx) and [PDF](Moniq_Technical_Backup.pdf) — **2 optional slides**, outside the main pitch.
- [Manual submission checklist](MANUAL_SUBMISSION_CHECKLIST.md).
- [Verification evidence](PRESENTATION_VERIFICATION.md).
- [Slide preview contact sheet](slide-previews/contact-sheet.png); every main slide has a full-HD PNG in `slide-previews/`.

All primary text, shapes, architecture nodes, money labels and hyperlinks are editable PowerPoint objects. Screenshots remain raster pictures of the actual app. Presenter/team names are deliberately marked placeholders. Segoe UI matches the app; PowerPoint may substitute a font on other platforms, so use the exported PDF for fixed-layout viewing. Speaker notes include evidence and limitations.

The screenshots use synthetic app data only: dashboard from `../screenshots/12-final-dashboard.png`, review/balance/SmartApprove/Circles frames from `../demo/Moniq_Hacklanta_Final.mp4` at 00:29 / 00:41 / 00:50 / 01:15. Full frames and cropped assets are retained in `assets/`. Cropping removes unrelated page areas and recording captions; it does not change financial values. Merchant words are synthetic text labels, not sponsor endorsements or licensed logo assets.

Codex assisted the deck, scripts and visual verification. Generation tools are python-pptx (MIT), Pillow (HPND), Microsoft PowerPoint (installed local renderer); isolated tool dependencies live in ignored `.tools/presentation-python`, not application requirements. No additional AI-generated images, external photographs, trademarks or music were added. Ownership/work-window eligibility still requires team verification in the checklist.

## Rebuild locally

```powershell
cd D:\Map\Moniq
$env:PYTHONPATH='D:\Map\Moniq\.tools\presentation-python'
.\.venv\Scripts\python.exe docs\presentation\build_presentation.py
powershell -ExecutionPolicy Bypass -File docs\presentation\export_presentation.ps1
```

For a fresh machine, install python-pptx and Pillow in a separate tools environment, regenerate, then export with PowerPoint or another compatible renderer. The checked PDF and previews were produced by PowerPoint 16.0 on Windows. The exported text-bound JSON files are verification outputs, not app runtime data.

This folder was added after local application commit `d2ad580`; application source, databases, credentials and existing demos were preserved. Nothing is pushed, deployed or submitted automatically. The older final ZIP excludes this subsequent presentation until explicitly rebuilt.
