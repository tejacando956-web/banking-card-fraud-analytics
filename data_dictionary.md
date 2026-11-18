# Data Dictionary — Card Fraud Analytics (synthetic data)

## data/transactions.csv — one row per card transaction

| Column | Type | Description |
|---|---|---|
| txn_id | string | Unique transaction ID (`TXN-000001`…). |
| card_id | string | Anonymised card identifier (`CARD-0001`…`CARD-0600`). |
| txn_datetime | datetime | Timestamp of the transaction (Q1 2024). |
| amount | float | Transaction amount in USD, always > 0. |
| merchant_category | string | MCC-style category: grocery, gas, e-commerce, travel, dining, ATM, electronics, pharmacy. |
| channel | string | `online` (card-not-present), `POS` (point of sale), `ATM`. |
| card_present | bool | True for POS/ATM, False for online. Derived from channel. |
| foreign | bool | True if the transaction originated outside the cardholder's home country. |
| is_fraud | int (0/1) | Ground-truth fraud label. In the real world this arrives late and noisy via chargebacks and investigator confirmations; here it is planted at generation time. |

## Planted fraud patterns (by design, so the analysis has something real to find)

- Fraud concentrated in **online (card-not-present)**, **foreign**, and **night hours (00:00–04:59)**.
- **Higher average ticket** for fraud in electronics / travel / e-commerce.
- **Card-testing probes**: sub-$3 online transactions on a card shortly before large fraudulent transactions.
- **Velocity bursts**: a few compromised cards firing 3 transactions within ~9 minutes.

## outputs/

| File | Contents |
|---|---|
| kpi_summary.csv | The 15 headline KPIs: transaction and fraud counts, fraud rate % (the same KPI is also quoted in basis points — 220 bps — in the README and dictionary), fraud loss $, average fraud vs legit ticket, online fraud share %, rule-set flags / precision / recall, estimated loss prevented ($ and % of fraud loss), overnight fraud share %, peak hour × channel fraud count, and foreign fraud rate %. Every KPI is defined, with its exact formula, in `KPI_DICTIONARY.md`. Supporting detail (home fraud rate, foreign share of fraud, amount-band rates, chargeback proxy at a 65% conversion assumption) lives in the breakdown CSVs below and `insights.md`. |
| rule_performance.csv | Per-rule and combined flagged count, true positives, false positives, missed fraud, precision % and recall %. |
| fraud_by_channel.csv | Transactions, fraud count, fraud loss $, fraud rate % and fraud share % per channel. |
| fraud_by_hour_channel.csv | Fraud count for every hour of day (0–23) × channel (online, POS, ATM) — the source table behind the fraud heatmap. |
| rule_cumulative.csv | Cumulative flagged count, true/false positives, precision % and recall % as the four rules are switched on one at a time in order (R1, +R2, +R3, +R4) — the source table behind the rule trade-off curve. The final row equals the combined rule set. |
| fraud_by_month.csv | Transactions, fraud count, fraud rate % and fraud loss $ per calendar month (Q1 2024) — the source table behind the monthly trend chart. |
| fraud_by_amount_band.csv | Transactions, fraud count, fraud loss $ and fraud rate % per transaction amount band ($0–10, $10–50, $50–100, $100–250, $250–500, $500+) — the source table behind the fraud-rate-by-amount chart. Bands are lower-bound inclusive: $0–10 means $0 up to but not including $10. |
| fraud_by_origin.csv | Transactions, fraud count, fraud loss $, fraud rate % and fraud share % for foreign vs home transactions — the source table behind the foreign-vs-home chart. |
| insights.md | Narrative findings and honest limitations. |

## Rule definitions (analysis.py)

| Rule | Logic |
|---|---|
| R1 amount | Amount above a per-category threshold (e.g. electronics > $400, travel > $600, e-commerce > $300). |
| R2 online + foreign | card_present = False AND foreign = True. |
| R3 night | Hour 00–04 AND amount > $100 AND channel ≠ ATM. |
| R4 velocity | 3rd-or-later transaction on the same card within a rolling 10-minute window. |
| Combined | Flagged if ANY rule fires. Precision = TP/(TP+FP); recall = TP/(TP+FN). |
