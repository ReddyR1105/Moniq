# Moniq on your phone

Moniq now includes an installable web manifest, genuine PNG icons, a static-only service worker, and a mobile Settings installation panel. The production Chromium tests check installability metadata and touch interactions at 360, 390 and 428 pixels. Real Android and iPhone installation still needs an owner device check. iPhone instructions were checked using a simulated user agent in Chromium; this is not Safari certification.

## Android

After the approved HTTPS demo is actually deployed, open its verified URL in Chrome. In Moniq Settings, select **Install Moniq** when Chrome offers the installation prompt. Otherwise use Chrome's menu and **Install app** or **Add to Home screen**, as available. Launch the home-screen icon, check the standalone window and synthetic-session banner, and test navigation, a purchase, Circles, goals and reset.

## iPhone

Open the verified HTTPS URL in Safari. Choose **Share → Add to Home Screen**; enable **Open as Web App** if Safari offers it, then choose **Add**. Open the icon and repeat the synthetic walkthrough. Safari does not use Chromium's `beforeinstallprompt` event; Moniq provides manual instructions.

## Connectivity and privacy

Only versioned JavaScript/CSS, public icons and a static offline explanation are cached. No API responses, exported finances, Gmail data, session cookies or populated financial pages are stored in service-worker CacheStorage. Offline navigation shows **Moniq needs a connection**; financial operations require a connection. Existing session cookies follow the backend's expiry and privacy rules.

New workers wait for existing windows to close rather than reload an active financial edit. Reopen Moniq after closing all app/browser windows to activate an update. Removing the home-screen icon is not a guarantee that a browser clears cookies or all site storage; use the browser's site-data controls when needed.

## Local verification

```powershell
cd D:\Map\Moniq
powershell -ExecutionPolicy Bypass -File .\scripts\start-public-demo.ps1
```

Use `http://127.0.0.1:8080` on this computer. A phone's `127.0.0.1` refers to that phone, and arbitrary LAN HTTP is not a secure PWA origin. The intended phone test is the future approved HTTPS demo. No working public demo URL is claimed yet.

Desktop layouts remain available. Mobile controls provide at least 44-pixel button targets, 16-pixel input text, and safe-area padding. Touch tests cover confirmed synthetic paycheck/purchase alerts, exact balance updates, shared bills and repayments, savings plans, the record-based assistant, budgets and forecast charts.
