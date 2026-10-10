# Moniq judge walkthrough

Run both servers using the README; open http://127.0.0.1:5173. No external keys, bank login, or judge credentials are required. Use synthetic records only. For a repeatable presentation, use **Settings → Reset Demo** before starting (this replaces local demo records).

1. Overview: read Alex Morgan's current balance and month-to-date net expenses. Describe the synthetic GSU profile and upcoming rent/pay schedules; actual values change with the date.
2. **Try purchase alert → Simulate a purchase alert**: observe Chick-fil-A, $15.75, Food, and confidence. Change a field if demonstrating corrections. Nothing is saved until confirmation.
3. **Confirm & save transaction**: month-to-date net expenses rise by $15.75 and balance falls by $15.75. Open Transactions to see the persisted record. Repeat alerts produce a clear duplicate warning.
4. Budgets: observe the increased food spending. Edit Food monthly limit and click its Save button. Weekly/monthly plans are independent.
5. AI Insights: use the default $150 purchase and **Run scenario**. The ending-balance difference is exactly −$150. Expand the assumptions. Schedules can represent bills, pay, tuition and aid; estimates do not move money.
6. Student Deals: inspect the first match, savings, eligibility, remaining-budget explanation, and explicit synthetic disclosure. Bookmark it and try Saved. No live redemption link is claimed.
7. AI Assistant: click **Can I afford a $150 purchase?**, then **See the calculated values**. The answer uses the same forecast and stored data; no Gemini call occurs.
8. Subscriptions: review three inferred monthly services and costs; confirm or dismiss a candidate. Settings provides profile/goals/allowance, export, deletion and Reset Demo.

The prominent **Start Demo** button walks through eight steps. Each Open step button uses the real page/dialog; Next moves through the guide. Step two extracts, reviews and saves, and step three opens the stored transaction for review.

## Capture and assets

`frontend/e2e/recording.spec.ts` drives the actual application on isolated synthetic services at ports 8001/5174. It asserts classification, updated financial figures, scenario arithmetic, assistant evidence, reset, and absence of JavaScript crashes or server errors. It writes page screenshots under `docs/screenshots/`.

With Python/Node dependencies installed and Chromium installed:

```powershell
cd D:\Map\Moniq
# Put your Node/npm installation on PATH (launch/check scripts locate .tools automatically).
cd frontend
npx playwright install chromium
cd ..
$env:MONIQ_BROWSER = 'chromium'
$env:MONIQ_RECORD_DEMO = '1'
npm --prefix frontend run demo:capture
Remove-Item Env:MONIQ_RECORD_DEMO
```

Set `PLAYWRIGHT_BROWSERS_PATH` consistently for installation and capture if using a custom browser cache. On this workspace it is `D:\Map\Moniq\.tools\playwright-browsers`. Windows defaults to installed Edge when MONIQ_BROWSER is absent; CI defaults to Chromium. `demo:capture` without the recording flag creates screenshots quickly, including the mobile Overview. Normal browser tests exclude the slow `@demo` recording.

The included WebM recording is silent actual UI footage. Use `DEMO_SCRIPT.md` or the caption text for narration and upload a playable, accessible version manually. GitHub/Devpost links and submission have not been published automatically.

For the single-origin session-isolated demo use scripts/start-public-demo.ps1 and http://127.0.0.1:8080. A separate browser profile/private context starts another visitor. Personal CSV/message input and model retraining remain local-only; the built-in synthetic CSV works in public mode. See DEPLOYMENT.md.
