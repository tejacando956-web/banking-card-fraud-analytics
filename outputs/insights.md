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
- Largest fraud-loss category: **e-commerce** ($14,864.56).
- Precision is deliberately reported alongside recall: every false positive is a good customer interrupted, so a high-recall rule with poor precision is not automatically a win.
- Card-testing probes (sub-$3 online transactions before large fraud) are visible in the data and are a classic pre-fraud signal a velocity/amount-sequence rule can exploit.

## Honest limitations
- Rule-based detection is transparent and explainable to investigators, but it cannot learn new patterns, scores no risk gradient, and fraudsters adapt to fixed thresholds. Production issuers layer ML models on top of rules.
- Labels here are planted in synthetic data; real-world fraud labels arrive weeks later via chargebacks and are noisy.
