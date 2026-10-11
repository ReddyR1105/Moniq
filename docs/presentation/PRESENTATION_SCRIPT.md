# Moniq judging pitch

Eight slides; target **2:40** including brief slide transitions. Speaker notes in the PowerPoint contain the same script.

Rehearse at about 150 words per minute. Do not read the fine print aloud. The slide-four workflow is illustrated with real synthetic recording frames; a live click-through is optional and replaces that section rather than extending the pitch.

Presenter/team: **[edit name / team]**. Never use the synthetic Alex profile as the team roster.

## Slide 1 — 10 seconds (0:00–0:10)

Meet Moniq: Spending, Made Smarter. It helps college students track spending, manage shared expenses, and understand their financial future.

## Slide 2 — 18 seconds (0:10–0:28)

Student money lives in fragments: bank alerts, spreadsheets, and separate apps. A paycheck lands, dinner gets split, and rent is coming. The challenge is connecting those events into a clear picture of what you can spend and what you need to save.

## Slide 3 — 18 seconds (0:28–0:46)

Moniq brings that picture together. Import transactions or connect Gmail with permission. Review the extracted activity, let machine learning suggest categories, and see confirmed records update your account estimates, budgets, and forecasts. Circles adds your personal share of group spending.

## Slide 4 — 30 seconds (0:46–1:16)

Here is the working flow, using synthetic data. Start with ten dollars. Moniq detects a four-hundred-dollar paycheck alert. After confirmation, the estimate becomes four hundred ten. A fifteen-dollar restaurant alert is extracted, categorized, and matched to checking. Confirm it, and the estimate becomes three hundred ninety-five. These are actual saved records and calculations, not numbers placed on a mockup. Gmail-derived balances remain estimates, not verified bank balances.

## Slide 5 — 26 seconds (1:16–1:42)

SmartApprove is optional. You control trusted sender rules; authentication, account, date, confidence, and amount checks decide whether an alert can skip review. Uncertain messages stay manual. Circles handles everyday roommate bookkeeping: pay forty dollars for dinner, keep the full charge in your cash ledger, and count twenty dollars as your share. A confirmed twenty-dollar repayment clears the debt without becoming paycheck income. Moniq never sends payments.

## Slide 6 — 25 seconds (1:42–2:07)

The system uses React and TypeScript over a Python FastAPI backend and SQLite. A local TF-IDF and logistic-regression model suggests categories. Deterministic code handles integer-cent balances, splits, and forecasts. An independent evaluation reproduced ninety-four point seven percent raw accuracy on held-out synthetic examples. That is evidence of the ML pipeline, not measured real-bank accuracy. Low-confidence descriptions still need review.

## Slide 7 — 18 seconds (2:07–2:25)

The prototype passed one hundred nine backend tests and nineteen Chromium browser tests, including production pages and isolated financial workflows. It includes responsive budgets, goals, subscriptions, and record-grounded answers. Wider real-email coverage, live bank verification, and production identity remain future work. Sample deals are fictional.

## Slide 8 — 15 seconds (2:25–2:40)

The goal is practical: less bookkeeping, clearer decisions, and easier roommate expenses. Codex assisted development; the work-history and dependency disclosures are in the repository. Moniq: your money, your goals, your financial future. Spending, Made Smarter.

## Rehearsal and demo

- Open slide show at 1920×1080; check the projector before judging.
- Keep `../demo/Moniq_Hacklanta_Final.mp4` (2:21) available as the separate required demo video; do not play the whole video inside this 2:40 pitch.
- For live demonstration, use a dedicated isolated synthetic workspace with Gmail disabled. Follow `../DEMO_SCRIPT.md`; never reset the real owner workspace or open personal Gmail.
- Confirm the official judging slot with organizers; no official pitch duration was established from the published pages.
- Complete `MANUAL_SUBMISSION_CHECKLIST.md` and verified work/contribution disclosures before submission.
