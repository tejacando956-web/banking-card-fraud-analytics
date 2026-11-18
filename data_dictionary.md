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
| kpi_summary.csv | Headline KPIs: volume, fraud rate (% and basis points), fraud loss $, average fraud vs legit ticket, online fraud share, chargeback proxy (count and $ at a 65% conversion assumption), rule-set flags / precision / recall, estimated loss prevented ($ and % of fraud loss). |
| rule_performance.csv | Per-rule and combined flagged count, true positives, false positives, missed fraud, precision % and recall %. |
| fraud_by_channel.csv | Transactions, fraud count, fraud loss $, fraud rate % and fraud share % per channel. |
| insights.md | Narrative findings and honest limitations. |

## Rule definitions (analysis.py)

| Rule | Logic |
|---|---|
| R1 amount | Amount above a per-category threshold (e.g. electronics > $400, travel > $600, e-commerce > $300). |
| R2 online + foreign | card_present = False AND foreign = True. |
| R3 night | Hour 00–04 AND amount > $100 AND channel ≠ ATM. |
| R4 velocity | 3rd-or-later transaction on the same card within a rolling 10-minute window. |
| Combined | Flagged if ANY rule fires. Precision = TP/(TP+FP); recall = TP/(TP+FN). |
