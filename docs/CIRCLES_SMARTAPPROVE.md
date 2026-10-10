# Moniq Circles and SmartApprove

Moniq — Spending, Made Smarter. These additions extend the existing application with original local expense sharing and optional Gmail approval rules. No external payments, invitations, bank verification, or account authentication are implied.

## Circles accounting

Create roommate, friend, trip, dining, shared-subscription, or one-time circles. Add further local participants without changing existing shares. Choose USD, EUR, GBP, or CAD and add local participants; **Me** is included. Participants are entries in your ledger, not real authenticated users.

Add an expense with a payer and included participants. Equal splits use integer-cent quotient/remainder allocation. Custom amounts must equal the original total. Percentages must total exactly 100; largest-remainder allocation distributes every cent, with stable member-ID ties. Excluded members have no share. Backend calculations use integers and Decimal, never binary float money arithmetic. API display amounts remain numbers for compatibility with existing charts; monetary form inputs are sent as decimal strings.

In Transactions, select **Split this expense**, or choose an existing transaction within Circles. Only an existing USD expense paid by Me may be linked, with its original amount and date unchanged. One transaction can have only one active allocation. Approved Gmail purchases use this same path. Nothing copies or repeats the original cash movement.

For a $60 checking purchase shared equally:

| Event | Bank cash change | Personal spending | Outstanding receivable | New income |
| --- | ---: | ---: | ---: | ---: |
| Original purchase, linked to circle | -$60 | $30 | $30 | $0 |
| Actual friend repayment | +$30 | $0 additional | $0 | $0 |

An unlinked expense adds personal spending and obligations without inventing a bank transaction. USD personal shares affect category budgets, seven-day charts, monthly expense totals, comparisons, and savings suggestions. Other currencies have separate debt totals and are excluded from USD account and budget aggregation. Currency conversion is not implemented.

Record full or partial repayments. **Bookkeeping only** clears recorded debt without changing bank cash. **Record an actual bank cash movement** adds one signed repayment to a chosen account. Alternatively, manually match an existing transaction with the exact amount, date, and direction: the existing cash entry is reused and reclassified as reimbursement/settlement, excluded from paycheck income and spending. A confirmation checkbox is mandatory; arbitrary incoming payments are never automatically matched. Stable request keys make retries idempotent and overpayments are rejected. Suggestions list actual expense-level debts; Moniq sends no payments.

Unsettled allocations may be edited or deleted without deleting the bank transaction. Settled expenses and linked settlement cash are protected audit history; settled-expense correction requires a future auditable workflow. The current MVP does not cancel settled repayments, reconcile a shared purchase's later refund automatically, or implement creditor-approved debt transfers. Reconcile these exceptional cases manually before using estimates. Linking protects financial transactions from generic edits/deletion that would invalidate their ledger. Full JSON data export includes allocations, settlements, and ledger audit. CSV preserves reimbursement/settlement types but is a cash-record export, not a restoration of shared allocations or audit history; authorized workspace deletion/reset clears all related tables in dependency order.

Forecasts continue to use full historical bank charges. Outstanding reimbursements are **never** assumed to arrive. The assistant explains ledger-derived shared meals, receivables, payables, marked recurring shared subscriptions, and next-month shared-rent reserves. Recurrence is a planning label; it does not create automatic charges or payments.

## SmartApprove policy

Settings → **SmartApprove · Trusted Senders** lets the local owner configure exact email addresses or exact domains, institution labels, one registered account, allowed events, per-transaction and daily caps, enabled state, suspension, and removal. Creation defaults **off**. Domains do not implicitly trust subdomains, wildcards, or display names. Removed rules retain audit history.

Gmail synchronization still requires the existing read-only OAuth authorization. SmartApprove reads only provider-delivered Gmail API responses; the browser cannot submit authentication evidence. It requires one unambiguous sender, one recognized Google receiving boundary ordered before that sender, one Google Authentication-Results header, SPF/DKIM/DMARC passes with **exact** domain alignment, and no contradictory or forwarded/ARC evidence. Missing evidence, duplicate headers, failed/misaligned authentication, uncertain provenance, or synthetic domains send messages to manual review. Explicit synthetic/simulated/demo/test markers in the subject, body or sender display name also require manual review.

This is deliberately narrower than DMARC's relaxed organizational-domain alignment and rejects legitimate forwarded messages and providers that omit these precise headers. It evaluates Gmail's reported results rather than independently verifying DNS records or DKIM signatures. A header alone cannot cryptographically establish its provenance, especially for imported mail. Google-reported receiver evidence is a conservative prototype signal, **not proof that a bank transaction occurred**; imported/ambiguous messages must be reviewed manually. Keep real-money automation local and opt-in; this is not production financial assurance.

Approval also requires explicit posted-event language, one supported USD amount, a uniquely matched registered suffix and permitted account, a date between its balance date and today, an allowed event, confident categorization, and both caps. Orders, receipts, pay stubs, transfers, pending authorizations, future bills, uncertain deposits, and ambiguous messages are not auto-approved. Caps count gross approvals on Moniq's New York calendar day; reversals/corrections do not replenish that day's allowance. A sender's institution text is only your label, not a verified bank claim.

Automatic approval requires an explicit transaction date; received-date fallbacks remain manual. Message identity prevents repeated sync imports. Posted transaction fingerprints prevent account/date/merchant/signed-amount duplicates; original imported event fields also prevent duplicate receipts after corrections or reversals. This heuristic may combine two genuinely identical same-day purchases; possible same-merchant/amount events within three days with different dates remain manual. Different merchant descriptions still require manual reconciliation.

Automatically approved transactions retain their **Auto-approved** source label. Settings displays append-only approval/policy audit records. Editing an unlinked approval records before/after values; reversing it creates exactly one compensating cash adjustment and preserves the original entry. Repeated reversals, changes to already-reversed approvals, and deletion/editing of reversal adjustments are blocked. Ledger-linked approvals require their allocation to be resolved first. This is database-enforced application behavior, not a tamper-proof external audit service.

Overview shows pending/review counts, auto-approved count, active sender status and recent approval activity, plus personal spending versus cash out and Circles debt. All Gmail-derived account balances are labelled **estimates**. Manual review remains available. There is no unattended sync timer.

## Isolation and privacy

- Local Gmail and personal records stay in the existing personal database. Credentials and encrypted token vault remain backend-only and Git-ignored. Existing encryption keys are never replaced by this upgrade.
- Public visitors get independent synthetic databases, locks, and cookies. Public Circles names, participants, titles and sender settings accept sample values only. Public routes cannot read Gmail credentials or private data.
- The explicit local walkthrough uses `SCENARIO_DATABASE_URL`, a third database, separate from existing demo and personal records. It has no real Gmail access. In public mode the walkthrough resets only that visitor's already isolated synthetic session.
- Local personal/scenario mode remains loopback-only with origin checks. Real collaboration would require authenticated users, ownership/ACL checks, invitation permissions, CSRF/session controls and persistent encrypted hosting before public release.

## Working walkthrough

1. Run the existing backend/frontend and open `http://127.0.0.1:5173/#circles`.
2. Enter **100.00** in **Starting synthetic checking balance ($)**, choose **Start isolated walkthrough**, and confirm. The backend creates $100 synthetic checking, a food budget, and one enabled synthetic sender **only in this controlled scenario**.
3. Choose **Process controlled $40 alert**. The real policy/transaction code creates one posted Chick-fil-A purchase; estimated cash is $60. Repeated processing is blocked.
4. Create **Campus friends** with **Jordan**. Select the $40 Chick-fil-A transaction and choose **Split with Friends**.
5. Save equal shares. Me has $20 spending; Jordan owes $20. Cash remains $60.
6. Record Jordan's $20 repayment, select **Record an actual bank cash movement**, and confirm it happened.
7. Overview shows estimated cash **$80**, personal spending **$20**, cash out **$40**, income **$0**, and receivable **$0**. The original purchase is still one transaction.
8. Choose **Return to synthetic demo** to leave the local scenario; personal data and Gmail connection are untouched. In public mode use Reset Demo to restore only your session.

The scenario uses a server-owned synthetic fixture and bypasses neither real Gmail permission nor real-email authentication. Normal Gmail sync always rejects synthetic sender evidence.

## Original work and dependencies

Circles code, language and layouts were written specifically for Moniq. No competing application's source, screenshots, copy, branding, or artwork is used. It uses the project's existing React, Lucide, SQLAlchemy and Pydantic dependencies; no new expense-sharing dependency or payment SDK was introduced. See [ATTRIBUTIONS.md](ATTRIBUTIONS.md) for dependency notices and [UPGRADE_QA.md](UPGRADE_QA.md) for executed verification.

Primary authentication references: [Google Gmail authentication help](https://support.google.com/mail/answer/180707?hl=en) and [RFC 8601 authentication-results trust boundaries](https://www.rfc-editor.org/rfc/rfc8601.html). Authentication and financial posting are separate decisions.

## Final accounting extension

The account ledger now supports debit-card suffix aliases, separate credit debt, paired internal transfers/card payments and immutable manual reconciliation entries. Cash availability and forecasts exclude credit-account debt/charges; personal spending includes credit purchases once. Transfer and adjustment kinds are excluded from income, spending and historical discretionary forecasting. Imported statement transfer legs must not be separately mislabeled as new income/purchases. Paired movements and reconciliation history cannot be edited or deleted through generic transaction controls.

Savings goals have contributions and monthly plans in additive tables. Goal progress is separate bookkeeping; recording a contribution does not debit cash, and a projected completion date does not create deposits. The main dashboard has actual email approvals and savings progress. Every original database row was compared to the pre-upgrade backups and preserved. See QA_REPORT.md for current tests and final narrated media.
