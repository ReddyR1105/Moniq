# Moniq — 2–3 minute demonstration

Use the actual local app, with **Settings → Reset Demo** completed before recording. Keep both servers running. A silent recording of the actual app is included at `docs/demo/moniq-demo.webm`, with caption text in `moniq-demo.vtt`. Its actions run in about 2 minutes 15 seconds; this table is a longer narration alternative. Add narration or captions before uploading. Values depend on the current date; read them from the screen. No bank account, API key, or judge credentials are required.

| Time | Screen and action | Suggested narration |
| --- | --- | --- |
| 0:00–0:20 | Overview; point to balance and budget | “This is Moniq: Spending, Made Smarter. We help college students understand their money without maintaining a spreadsheet. Here’s our synthetic Georgia State student. Every total is calculated from stored records.” |
| 0:20–0:55 | Try purchase alert → Simulate a purchase alert | “Students already receive purchase notifications. This demo accepts user-pasted alerts; it does not access texts. Moniq extracts Chick-fil-A and $15.75, and our trained scikit-learn model suggests Food with visible confidence. The student can correct any field.” |
| 0:55–1:10 | Confirm & save; show Overview and Budgets | “Once confirmed, the transaction is persisted in SQLite. Spending rises by $15.75 and the food budget updates. Repeating the same alert is safely detected as a duplicate.” |
| 1:10–1:30 | AI Assistant → How much did I spend this week? | “The local assistant retrieves calculated financial values rather than asking a language model to invent numbers. Here’s the spending total and the supporting evidence.” |
| 1:30–1:55 | AI Insights → $150 purchase → Run scenario | “The next 30 days combine historical variable spending, scheduled pay, and upcoming bills. A $150 purchase lowers the projected ending balance by exactly $150. These are estimates with assumptions, not promises.” |
| 1:55–2:15 | Student Deals; inspect top match | “Sample student offers are ranked by spending, interests, eligibility, and remaining budget. We avoid unaffordable offers and unnecessary purchases. These are synthetic examples, not live discounts.” |
| 2:15–2:35 | Subscriptions; confirm Spotify | “Repeated service charges reveal possible subscriptions, renewal dates, and annualized cost. Students confirm or dismiss patterns. Moniq does not claim to cancel services.” |
| 2:35–2:50 | AI Insights ML evaluation; closing | “We trained a real TF-IDF/logistic regression pipeline and measured about 94.7% accuracy on synthetic held-out merchant families. Corrections are saved for retraining. Moniq makes student spending easier to understand and plan.” |

For a short alternative, omit subscription review and use the in-app guided tour. Use actual screen recordings; don't portray Plaid, Gemini, real offers, message synchronization, or production authentication as available. Mention that optional integrations are future work if asked.
