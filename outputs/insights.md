# Insights — Card Fraud Analytics (Portfolio Project, synthetic data)

> Portfolio project — not paid work experience. Synthetic data only.
> Detection below is a transparent rule set, NOT a machine-learning model.

## Headline KPIs
- **Transactions:** 6,135 | **Fraud:** 135 (2.20% = 220 basis points)
- **Fraud loss:** $44,690.44 | **Avg fraud ticket:** $331.04 vs legit $89.80
- **Fraud share via online (card-not-present):** 92.6%
- **Chargeback proxy (65% of fraud):** ~88 chargebacks, $29,048.79
- **Rule set:** precision 44.73% | recall 78.52% | estimated loss prevented $41,916.02 (93.8% of fraud loss)

## Findings
- Fraud concentrates in card-not-present, foreign and night-hour (00:00–04:59) activity — the planted pattern the rules are built to catch.
- Largest fraud-loss category: **e-commerce** ($14,864.56, 33.3% of all fraud loss).
- **Overnight concentration:** 83.7% of fraud occurs 00:00–04:59; the single busiest hour is 02:00 with 38 frauds, and the hottest hour x channel cell holds 36 frauds.
- **Rule trade-off curve:** switching rules on in order (R1 → R4), cumulative recall climbs 34.81% → 66.67% → 78.52% → 78.52% while cumulative flags grow 130 → 197 → 237 → 237 (outputs/rule_cumulative.csv).
- **Monthly trend:** 2024-01 2.10% (44 frauds); 2024-02 2.61% (52 frauds); 2024-03 1.91% (39 frauds) (outputs/fraud_by_month.csv).
- **Amount bands tell two stories:** the $0-10 band is 68.75% fraud (33 of 48 transactions) — those are card-testing probes, not shopping. Everyday bands are almost clean ($10-50: 0.00%, $50-100: 0.06%), then risk climbs with ticket size: $100-250 is 2.38%, $250-500 is 12.50% and $500+ is 28.12% (outputs/fraud_by_amount_band.csv).
- **Foreign transactions are the riskiest slice of the book:** only 144 of 6,135 transactions (2.3%) are foreign, yet their fraud rate is 49.31% versus 1.07% for home transactions, and they account for 52.6% of all fraud and $24,068.83 of the loss (outputs/fraud_by_origin.csv).
- Precision is deliberately reported alongside recall: every false positive is a good customer interrupted, so a high-recall rule with poor precision is not automatically a win.
- Card-testing probes (sub-$3 online transactions before large fraud) are visible in the data and are a classic pre-fraud signal a velocity/amount-sequence rule can exploit.

## Honest limitations
- Rule-based detection is transparent and explainable to investigators, but it cannot learn new patterns, scores no risk gradient, and fraudsters adapt to fixed thresholds. Production issuers layer ML models on top of rules.
- Labels here are planted in synthetic data; real-world fraud labels arrive weeks later via chargebacks and are noisy.
