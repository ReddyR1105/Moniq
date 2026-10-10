# Moniq judges' pitch

## 15-second introduction

Moniq, Spending, Made Smarter, helps college students turn confirmed financial alerts into a clear spending plan. It combines email review, ML categorization, forecasts and roommate bookkeeping, while keeping estimated money separate from actual records.

## 60-second demonstration

0-10 seconds: Show the isolated synthetic checking account at $10.

10-25 seconds: Simulate the $400 paycheck email, inspect extracted fields and confirm it. The stored balance becomes $410. Confirm the $15 restaurant purchase and show $395.

25-45 seconds: Show SmartApprove's exact-sender/account/limit policy and controlled $40 dinner. Link that transaction to a two-person Circle. The bank charge remains $40; your share and Jordan's debt are $20 each.

45-60 seconds: Record the confirmed $20 repayment; remaining debt becomes zero without adding paycheck income. Show budgets, the $100 purchase forecast and a grounded assistant response.

## 2-3 minute presentation

Use `docs/demo/Moniq_Hacklanta_Final.mp4` and its timed narration script. Open with the student problem, then demonstrate $10 -> $410 -> $395 through actual saved records. Explain why ambiguous emails require review and why trusted visible sender text is insufficient. Show the controlled approval and shared dinner: $40 cash payment, $20 personal spending, $20 receivable, then $20 repayment and zero debt. Close with weekly/monthly budgets, explicit forecast assumptions, a savings contribution plan, a database-grounded assistant answer and fictional offers. Finish: "Your money. Your goals. Your financial future."

## Explain the engineering

**ML:** Local TF-IDF text vectors and logistic regression. The independently reproduced raw synthetic held-out score is 250/264, or 94.70%, with disjoint merchant families. The review threshold yields 58.71% automatic coverage. Synthetic accuracy is not real-bank email accuracy.

**Balances:** Integer cents; opening cash plus posted signed transactions. Linked debit cards reference checking instead of adding a second balance. Credit debt is separate. Paired internal movements are excluded from income/spending; manual reconciliation preserves history. Forecasts and goal plans never become deposits.

**Gmail:** Backend OAuth authorization code with PKCE, expiring one-use state, exact configured callback and Gmail read-only scope. Official API reads happen after consent. Tokens are encrypted on the backend; personal/public/scenario data stores are isolated. We did not record personal email contents.

**SmartApprove:** Default off, exact policy, aligned provider authentication evidence, posted status/date, registered account, amount/daily caps, confidence and duplicate checks. Failures remain manual. Audit history and compensating reversals preserve prior records. This is a conservative prototype, not certified bank verification.

**Circles:** Exact-cent equal/custom/percentage allocations. A linked expense preserves the actual charge and substitutes only the owner's share for budgeting. Confirmed reimbursement settles a debt without becoming wages. No real money transfers or live collaboration.

## Likely questions

**How does this differ from conventional budgeting apps?** The tested workflow connects financial-event review, ML categorization, the cash ledger, personal-share budgeting, forecasts and grounded questions in one student-focused interface. We do not claim market exclusivity.

**What if an email is spoofed or uncertain?** Visible sender text alone is insufficient. Authentication and posted-event checks fail closed into manual review. Conservative rules can also reject legitimate bank formats; broader coverage requires consented evaluation.

**Can it move money?** No. Transactions, transfers, goals and settlements are bookkeeping of confirmed events. Bank APIs and payment processing are future work.

**Why not use a language model for financial arithmetic?** Money uses validated integer cents and deterministic calculations. ML supplies editable categories. Assistant answers use stored evidence.

**Does Gmail read everything?** The authorized scope permits read-only mailbox access. Moniq requests a bounded recent financial-message query, processes text without fetching attachments, and stores extracted fields. Local users control consent, sync, review and disconnect.

**What works offline?** Local ML and calculations need no paid API; the app needs its local backend. Gmail synchronization needs Google connectivity. Full offline sync is not implemented.

**Is this production ready?** No. Private mode must remain loopback-only. Persistent authenticated cloud identity, encrypted databases, independent security/accessibility review and real-bank evaluation remain future work.

**How did you use AI, and when was this built?** Codex assisted implementation, testing, docs and media. Answer timing from the team's verified work-window disclosure, not assumptions. The finalization extends an existing repository baseline.
