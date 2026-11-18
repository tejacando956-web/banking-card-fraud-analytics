# KPI Dictionary — Card Fraud Analytics

The project's 15 headline KPIs, defined in plain words: what each one means, exactly how it is calculated, and where it comes from. All 15 are produced by `analysis.py` from `data/transactions.csv` and written to `outputs/kpi_summary.csv`. Values in brackets are the results on the current synthetic dataset (6,135 transactions, Q1 2024).

**Words used below, in plain words:** a *ticket* is one transaction amount. A transaction is *flagged* when a detection rule marks it as suspicious. *Foreign* means the transaction came from outside the cardholder's home country; *home* means inside it. *Card-not-present* means the physical card was not there — online shopping.

## The 15 headline KPIs

| KPI | What it means, in plain words | How it is calculated | Where it comes from |
|---|---|---|---|
| `total_transactions` [6,135] | Every card transaction in the dataset. | Count of all rows in the data file. | `data/transactions.csv` |
| `total_fraud_transactions` [135] | How many of those transactions were fraud. | Count of rows labelled `is_fraud = 1`. | `data/transactions.csv` |
| `fraud_rate_pct` [2.20] / `fraud_rate_basis_points` [220.0] | The share of all transactions that were fraud — quoted two ways as one KPI: as a percentage, and in basis points, the unit fraud teams use because the rates are small (100 basis points = 1%). | Percentage: 100 × fraud transactions ÷ total transactions. Basis points: 10,000 × fraud transactions ÷ total transactions. | `data/transactions.csv` |
| `fraud_loss_usd` [$44,690.44] | Total dollars lost to fraud. | Sum of `amount` over all fraud transactions. | `data/transactions.csv` |
| `avg_fraud_ticket_usd` [$331.04] | The typical size of one fraud transaction. | Average of `amount` over fraud transactions. | `data/transactions.csv` |
| `avg_legit_ticket_usd` [$89.80] | The typical size of one genuine transaction — the comparison that shows fraud tickets are unusually big. | Average of `amount` over non-fraud transactions. | `data/transactions.csv` |
| `online_fraud_share_pct` [92.59] | What share of all fraud happened online (card-not-present) rather than in a shop or at an ATM. | 100 × fraud transactions on the `online` channel ÷ all fraud transactions. | `outputs/fraud_by_channel.csv` |
| `rule_flagged_transactions` [237] | How many transactions the four detection rules flagged as suspicious, in total. | Count of transactions where at least one of rules R1–R4 fired. | `outputs/rule_performance.csv` (row "ANY rule (combined)") |
| `rule_precision_pct` [44.73] | Of everything the rules flagged, the share that really was fraud. The rest were good customers interrupted. | 100 × true positives ÷ (true positives + false positives) for the combined rules — see "How the rule scores are calculated" below. | `outputs/rule_performance.csv` |
| `rule_recall_pct` [78.52] | Of all the fraud that happened, the share the rules caught. | 100 × true positives ÷ (true positives + missed fraud) for the combined rules. | `outputs/rule_performance.csv` |
| `est_loss_prevented_usd` [$41,916.02] | Fraud dollars the rules would have stopped — the amounts of the fraud transactions they flagged. It is an estimate: it assumes a flagged fraud transaction is stopped before the money is lost. | Sum of `amount` over fraud transactions that were flagged by at least one rule. | Calculated in `analysis.py` |
| `est_loss_prevented_pct_of_fraud_loss` [93.79] | The prevented dollars as a share of all fraud dollars. It is higher than recall because the rules catch the big tickets. | 100 × estimated loss prevented ÷ total fraud loss. | Calculated in `analysis.py` |
| `overnight_fraud_share_pct` [83.7] | What share of fraud happened between midnight and 4:59am, while cardholders are asleep. | 100 × fraud transactions with hour 0–4 ÷ all fraud transactions. | `data/transactions.csv` (hour taken from the timestamp) |
| `peak_hour_channel_fraud_count` [36] | The single worst hour-and-channel combination (2am, online) — the hottest square on the heatmap. | The largest single cell in the hour × channel fraud-count table. | `outputs/fraud_by_hour_channel.csv` |
| `foreign_fraud_rate_pct` [49.31] | Of transactions that came from abroad, the share that were fraud — roughly one in two. The comparison that makes it meaningful: the home fraud rate is just 1.07% (supporting detail, in the breakdown file). | 100 × fraud transactions with `foreign = True` ÷ all transactions with `foreign = True` (71 of 144). | `outputs/fraud_by_origin.csv` |

## The four detection rules (exact logic, as implemented in `analysis.py`)

The rules are deliberately simple and transparent — no machine learning — so an investigator can always say exactly why a transaction was flagged. A transaction is **flagged** if *any* rule fires.

| Rule | Exact logic |
|---|---|
| **R1 — Amount** | The amount is **strictly greater than** a per-category limit: electronics > $400 · travel > $600 · e-commerce > $300 · ATM > $400 · grocery > $250 · dining > $250 · gas > $150 · pharmacy > $200. (Limits live in the `AMOUNT_THRESHOLD` table at the top of `analysis.py`.) |
| **R2 — Online + foreign** | The card was **not present** (`card_present = False`, i.e. an online purchase) **AND** the transaction was **foreign** (`foreign = True`). |
| **R3 — Night** | The hour is **00, 01, 02, 03 or 04** (midnight to 4:59am) **AND** the amount is **over $100** **AND** the channel is **not ATM**. |
| **R4 — Velocity** | Looking at one card's transactions in time order: the transaction is the **3rd or later within 10 minutes** — exactly, the gap between this transaction and the one two places before it on the same card is **600 seconds (10 minutes) or less**. |
| **Combined** | Flagged if R1, R2, R3 or R4 fired. A transaction caught by two rules is still flagged once. |

## How the rule scores are calculated

Each flagged transaction ends in one of three buckets, by comparing the flag with the true fraud label:

- **True positive (TP)** — flagged, and it really was fraud. The rules did their job.
- **False positive (FP)** — flagged, but it was a genuine transaction. A good customer was interrupted; this is the friction cost of the rules.
- **Missed fraud / false negative (FN)** — not flagged, but it really was fraud. Money lost that the rules never saw.

From those three counts (in `outputs/rule_performance.csv`, per rule and combined):

- **Precision** = 100 × TP ÷ (TP + FP). *"When the rules shout, how often are they right?"* Combined: 100 × 106 ÷ 237 = **44.73%**.
- **Recall** = 100 × TP ÷ (TP + FN). TP + FN is all the fraud there was (135). *"Of all the fraud, how much did the rules catch?"* Combined: 100 × 106 ÷ 135 = **78.52%**.
- **Estimated loss prevented** = the total amount of the true-positive transactions ($41,916.02). Recall counts *transactions*; loss prevented counts *dollars* — the rules catch 78.52% of frauds but 93.79% of fraud money, because they catch the big tickets and miss mostly small ones.

## Where each output file feeds from

- `outputs/kpi_summary.csv` — the 15 headline KPIs above, one row each.
- `outputs/rule_performance.csv` — flagged / TP / FP / missed / precision / recall for R1, R2, R3, R4 and the combined set.
- `outputs/rule_cumulative.csv` — the same scores rebuilt step by step as rules are switched on in order R1 → R2 → R3 → R4 (the trade-off curve).
- `outputs/fraud_by_channel.csv`, `outputs/fraud_by_hour_channel.csv`, `outputs/fraud_by_month.csv` — fraud counts, rates and loss by channel, by hour × channel, and by month.
- `outputs/fraud_by_amount_band.csv` — transactions, fraud count, fraud loss and fraud rate for each amount band ($0–10, $10–50, $50–100, $100–250, $250–500, $500+).
- `outputs/fraud_by_origin.csv` — the same breakdown for foreign vs home transactions.

**Supporting detail beyond the 15:** the headline table above is deliberately the learnable set. Everything else the analysis computes lives in the breakdown CSVs listed here, so any headline number can be traced back to its full detail — including the home fraud rate (1.07%, 64 of 5,991) and the foreign share of all fraud (52.59%, 71 of 135) in `outputs/fraud_by_origin.csv`; the amount-band fraud rates — $0–10 band 68.75% (33 of 48, mostly card-testing probes) and $500+ band 28.12% (27 of 96) — in `outputs/fraud_by_amount_band.csv`; the per-rule scorecard and the step-by-step trade-off table; the monthly and per-category breakdowns; and the chargeback estimate (at the stated 65% planning assumption, reported in `outputs/insights.md`).
