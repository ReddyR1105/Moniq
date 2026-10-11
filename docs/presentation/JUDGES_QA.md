# Moniq — judges' questions

Use the main eight-slide deck for the timed pitch. The separate `Moniq_Technical_Backup.pptx` contains two optional engineering slides. Answers below describe the existing prototype, not a promised production service.

## 1. Why did you build Moniq?

The product addresses a concrete student workflow: income alerts, purchases, bills, savings goals and roommate expenses live in different places. Moniq brings confirmed activity into a shared financial picture. This is our problem framing; we have not conducted a user survey or measured adoption or financial impact. See [README](../../README.md).

## 2. What makes it different from budgeting apps?

The tested experience connects financial-email review, editable ML categorization, account estimates, personal-share budgeting, transparent forecasts and roommate bookkeeping. A shared dinner keeps its full cash charge while only your share drives spending budgets. We claim a coherent working workflow, not market exclusivity. See [feature audit](../FEATURE_AUDIT.md) and [Circles accounting](../CIRCLES_SMARTAPPROVE.md).

## 3. Why does it need machine learning?

Merchant descriptions contain useful words in varying formats. A trained text classifier supplies a reusable category suggestion with a confidence score. Rules still identify financial events, and validated deterministic code calculates money. ML does not prove a paycheck arrived or decide bank balances. See [classifier](../../backend/app/ml.py) and [finance](../../backend/app/finance.py).

## 4. How is the classifier trained?

The baseline uses 1,056 labeled synthetic English descriptions across 11 categories. Six merchant families per category provide 792 training examples; two separate merchant families provide 264 held-out examples. Word unigram/bigram TF-IDF feeds logistic regression with fixed parameters. Corrections are stored and can inform retraining; held-out-family corrections are excluded from evaluation training. Formatting variants remain correlated, so this is a limited synthetic evaluation. See [training source](../../backend/app/ml.py).

## 5. How accurate is it?

An independent fit reproduced **250/264 correct, 94.69697% raw synthetic accuracy**, macro F1 **0.943244**. This score precedes the app's uncertainty fallback. Below 45% confidence, the app assigns miscellaneous and asks for review. On this set, automatic coverage is **58.71%** and fallback-adjusted overall accuracy is **63.64%**. Accepted predictions were 155/155 correct only on this synthetic set. Confidence is uncalibrated; real-bank/email accuracy has not been measured. See [independent evaluation](../../data/ml_independent_evaluation.json) and [reproduction script](../../scripts/reproduce_ml.py).

## 6. How do you prevent duplicate transactions?

Gmail items are tracked by provider message ID, and confirmation checks for existing transaction evidence. Imports use normalized transaction fingerprints; ledger operations and repayments also use request keys/idempotency checks. A repeated identical request returns the existing result, while conflicting reuse is rejected. Different alerts describing one event may still require user review when evidence is ambiguous; this is not universal cross-bank deduplication. See [transaction service](../../backend/app/transactions.py), [Gmail routes](../../backend/app/gmail_routes.py), [account tools](../../backend/app/account_tools.py) and [Circles](../../backend/app/circles.py).

## 7. How does Gmail access work?

The owner authorizes Google OAuth's backend authorization-code flow with PKCE and expiring one-use state. The scope is `https://www.googleapis.com/auth/gmail.readonly`. Official Gmail API reads occur after consent; a bounded financial-message query processes text, not attachments. Connect, sync and disconnect are user controls. The scope permits mailbox reading; it is not limited by Google to financial emails even though Moniq's queries target them. Tests mock Google, and recorded demos use synthetic messages with Gmail disabled. See [setup](../GMAIL_SETUP.md), [OAuth/token service](../../backend/app/gmail_service.py) and [parser](../../backend/app/gmail_parser.py).

## 8. Can it access actual bank balances?

No bank API is connected. The app calculates an estimate from an entered opening balance and posted confirmed activity. Gmail-derived estimates can differ from a bank's authoritative balance if alerts are missing or incorrect. Manual reconciliation records an auditable adjustment when a user supplies an observed balance; it does not verify that balance. See [account tools](../../backend/app/account_tools.py).

## 9. How do SmartApprove security checks work?

Automation is off by default. Enabled policies specify a sender/address or domain, registered account, allowed event types and transaction/daily limits. Google-reported, aligned authentication evidence, posted-event/date checks, account matching, ML confidence, duplicates and caps must pass; uncertainty remains manual. Visible sender text alone is insufficient. Synthetic authentication is accepted only for explicit server-owned test fixtures. These checks reduce risk but are not cryptographic bank verification or a security certification. See [policy source](../../backend/app/smartapprove.py) and [Gmail regression tests](../../tests/test_gmail.py).

## 10. What happens if the AI makes a mistake?

Categories remain editable. Low-confidence results require review, and Gmail-derived transactions normally require confirmation unless an enabled SmartApprove policy passes. Approved records support audited corrections and compensating reversals. Reversed paychecks are excluded from the assistant's last-confirmed-paycheck answer. Forecasts refresh from the stored records. See [SmartApprove](../../backend/app/smartapprove.py), [assistant](../../backend/app/assistant.py), and [QA](../QA_REPORT.md).

## 11. How do you handle user privacy?

OAuth secrets and encrypted tokens stay on the backend in ignored local files. Public visitors receive isolated temporary synthetic databases and cannot connect Gmail or reach the owner's personal store. Recordings contain synthetic data. Private mode is restricted to the local owner and loopback; SQLite and OS backups are not encrypted by Moniq. A production cloud identity system and independent security review remain future work. Do not describe the current app as end-to-end encrypted. See [privacy/limits](../../README.md) and [OAuth vault](../../backend/app/gmail_service.py).

## 12. Why would college students use it?

The interface brings budgets, upcoming bills, savings goals, supported financial questions and shared expenses into one place. Those workflows fit student use cases without requiring a paid ML API. Usefulness and reduced bookkeeping are product hypotheses; validated demand, customer interviews and measured savings are still needed. Sample student deals are fictional examples, not live verified discounts. See [README](../../README.md).

## 13. How does Moniq Circles handle repayments?

For a $40 linked dinner, the cash ledger retains −$40, your spending share becomes $20 and the roommate owes $20. Confirmed partial repayments reduce that debt. Cash settlement can create a reimbursement record; bookkeeping-only settlement leaves cash unchanged, and matching an existing record avoids adding cash twice. Reimbursements are excluded from paycheck income. Multi-currency debts remain separate; cash matching is USD-only. The app neither sends payments nor provides live multi-user collaboration. See [Circles service](../../backend/app/circles.py).

## 14. What did you actually build during Hacklanta?

**Presenter must complete this answer from verified history.** An existing repository baseline `8ac182f` was extended by local release `d2ad580`. The recorded finalization added dashboard approvals, account movements/debit aliases, savings contributions/projections, supported assistant intents, regression tests and narrated demos while preserving Gmail, SmartApprove and Circles work. This presentation is a subsequent artifact. Commit timestamps alone do not establish work inside the official hacking window. Fill in **[verified work before start]**, **[verified work during event]** and **[each teammate's contributions]** before judging. If eligibility is uncertain, ask organizers; do not claim an existing completed project is newly built. See [work disclosure](../WORK_DISCLOSURE.md).

## 15. How did you use Codex or other AI coding tools?

OpenAI Codex assisted application implementation, debugging, tests, synthetic data, documentation, recordings and this presentation. The deck was generated with python-pptx and rendered/exported using installed Microsoft PowerPoint; screenshots are actual synthetic app captures. No separate development agents or additional sponsor AI APIs are established in the record. The team must state its own verified design decisions, review and contributions. This does not make the in-app assistant a generative LLM; its supported answers use stored evidence. See [work disclosure](../WORK_DISCLOSURE.md) and [attributions](../ATTRIBUTIONS.md).

## 16. What are the current limitations?

Balances are estimates; forecasts assume current plans. Gmail parsing is conservative English/USD coverage, without broad real-bank validation. Private mode is local-only, and persistent cloud authentication is absent. Circles has no payment rails/live collaboration or automatic settled-expense cancellation/shared-refund handling. Offers are fictional. No live banking/Plaid/Gemini, enrollment verification, subscription cancellation, push notifications, independent accessibility/security audit or approved deployment is claimed. See [QA limitations](../QA_REPORT.md).

## 17. What would you build next?

First test real financial-email coverage with explicit participant consent, measure parsing and category error rates, and improve review usability. Then add authenticated cloud identity, encrypted storage, security/accessibility reviews and safe synchronization. A later consented banking integration and collaboration could extend account verification and shared expenses. These are proposed next steps, not implemented features.

## 18. How could this become a real consumer product?

Validate student demand, establish privacy and deletion controls, obtain required Google/provider approvals, operate authenticated infrastructure and evaluate financial-data quality. Keep estimates separate from authoritative bank balances and use appropriate reviews before adding payment capabilities. Pricing, adoption and business outcomes are not yet validated. The prototype demonstrates the workflow and engineering foundation; it does not establish production readiness.
