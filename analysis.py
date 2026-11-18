"""Rule-based card fraud detection and KPI analysis.

Portfolio project — synthetic data only.
Run: python3 analysis.py  ->  writes outputs/*.csv and outputs/insights.md

Detection is deliberately transparent rules, not ML, and is evaluated
honestly: precision and recall are both reported, including the
false-positive cost of each rule.
"""
import pandas as pd

CHARGEBACK_RATE = 0.65  # proxy: 65% of confirmed fraud becomes a chargeback

AMOUNT_THRESHOLD = {  # per-category flag threshold (USD)
    "electronics": 400, "travel": 600, "e-commerce": 300, "ATM": 400,
    "grocery": 250, "dining": 250, "gas": 150, "pharmacy": 200,
}


def load():
    df = pd.read_csv("data/transactions.csv", parse_dates=["txn_datetime"])
    df["hour"] = df["txn_datetime"].dt.hour
    return df.sort_values(["card_id", "txn_datetime"]).reset_index(drop=True)


def apply_rules(df):
    df = df.copy()
    # R1: amount above the category threshold
    df["r1_amount"] = df.apply(
        lambda r: r["amount"] > AMOUNT_THRESHOLD[r["merchant_category"]],
        axis=1)
    # R2: card-not-present AND foreign
    df["r2_online_foreign"] = (~df["card_present"].astype(bool)) & \
        df["foreign"].astype(bool)
    # R3: night window 00:00-04:59 on a non-ATM transaction above $100
    df["r3_night"] = df["hour"].between(0, 4) & (df["amount"] > 100) & \
        (df["channel"] != "ATM")
    # R4: velocity — 3rd (or later) txn on the same card within 10 minutes
    df["prev2_time"] = df.groupby("card_id")["txn_datetime"].shift(2)
    df["r4_velocity"] = (
        (df["txn_datetime"] - df["prev2_time"]).dt.total_seconds() <= 600
    ).fillna(False)
    rule_cols = ["r1_amount", "r2_online_foreign", "r3_night", "r4_velocity"]
    df["flagged"] = df[rule_cols].any(axis=1)
    df["rules_fired"] = df[rule_cols].sum(axis=1)
    return df, rule_cols


def evaluate(df, mask, label):
    tp = int((mask & (df["is_fraud"] == 1)).sum())
    fp = int((mask & (df["is_fraud"] == 0)).sum())
    fn = int(((~mask) & (df["is_fraud"] == 1)).sum())
    precision = 100 * tp / (tp + fp) if tp + fp else 0.0
    recall = 100 * tp / (tp + fn) if tp + fn else 0.0
    return {"rule": label, "flagged": tp + fp, "true_positives": tp,
            "false_positives": fp, "missed_fraud": fn,
            "precision_pct": round(precision, 2),
            "recall_pct": round(recall, 2)}


def main():
    df, rule_cols = apply_rules(load())
    total = len(df)
    fraud = df[df["is_fraud"] == 1]
    legit = df[df["is_fraud"] == 0]
    fraud_loss = float(fraud["amount"].sum())
    caught = df[(df["flagged"]) & (df["is_fraud"] == 1)]
    loss_prevented = float(caught["amount"].sum())
    chargebacks = CHARGEBACK_RATE * len(fraud)
    chargeback_usd = CHARGEBACK_RATE * fraud_loss

    overall = evaluate(df, df["flagged"], "ANY rule (combined)")
    per_rule = [evaluate(df, df[c], c) for c in rule_cols]
    rule_perf = pd.DataFrame(per_rule + [overall])
    rule_perf.to_csv("outputs/rule_performance.csv", index=False)

    df["fraud_amount"] = df["amount"].where(df["is_fraud"] == 1, 0.0)
    by_channel = df.groupby("channel").agg(
        transactions=("txn_id", "count"), fraud_txns=("is_fraud", "sum"),
        fraud_loss_usd=("fraud_amount", "sum"),
    ).reset_index()
    by_channel["fraud_loss_usd"] = by_channel["fraud_loss_usd"].round(2)
    by_channel["fraud_rate_pct"] = (
        100 * by_channel["fraud_txns"] / by_channel["transactions"]).round(2)
    by_channel["fraud_share_pct"] = (
        100 * by_channel["fraud_txns"] / len(fraud)).round(2)
    by_channel.to_csv("outputs/fraud_by_channel.csv", index=False)

    online_share = float(by_channel.loc[
        by_channel["channel"] == "online", "fraud_share_pct"].iloc[0])
    kpis = [
        ("total_transactions", total),
        ("total_fraud_transactions", len(fraud)),
        ("fraud_rate_pct", round(100 * len(fraud) / total, 2)),
        ("fraud_rate_basis_points", round(10000 * len(fraud) / total, 1)),
        ("fraud_loss_usd", round(fraud_loss, 2)),
        ("avg_fraud_ticket_usd", round(float(fraud["amount"].mean()), 2)),
        ("avg_legit_ticket_usd", round(float(legit["amount"].mean()), 2)),
        ("online_fraud_share_pct", online_share),
        ("chargeback_rate_assumption_pct", int(CHARGEBACK_RATE * 100)),
        ("est_chargeback_count", round(chargebacks, 1)),
        ("est_chargeback_usd", round(chargeback_usd, 2)),
        ("rule_flagged_transactions", int(df["flagged"].sum())),
        ("rule_precision_pct", overall["precision_pct"]),
        ("rule_recall_pct", overall["recall_pct"]),
        ("est_loss_prevented_usd", round(loss_prevented, 2)),
        ("est_loss_prevented_pct_of_fraud_loss",
         round(100 * loss_prevented / fraud_loss, 2)),
    ]
    pd.DataFrame(kpis, columns=["kpi", "value"]).to_csv(
        "outputs/kpi_summary.csv", index=False)

    top_cat = (fraud.groupby("merchant_category")["amount"].sum()
               .sort_values(ascending=False))
    insights = f"""# Insights — Card Fraud Analytics (Portfolio Project, synthetic data)

> Portfolio project — not paid work experience. Synthetic data only.
> Detection below is a transparent rule set, NOT a machine-learning model.

## Headline KPIs
- **Transactions:** {total:,} | **Fraud:** {len(fraud)} ({100 * len(fraud) / total:.2f}% = {10000 * len(fraud) / total:.0f} basis points)
- **Fraud loss:** ${fraud_loss:,.2f} | **Avg fraud ticket:** ${fraud['amount'].mean():,.2f} vs legit ${legit['amount'].mean():,.2f}
- **Fraud share via online (card-not-present):** {online_share:.1f}%
- **Chargeback proxy ({int(CHARGEBACK_RATE * 100)}% of fraud):** ~{chargebacks:.0f} chargebacks, ${chargeback_usd:,.2f}
- **Rule set:** precision {overall['precision_pct']:.2f}% | recall {overall['recall_pct']:.2f}% | estimated loss prevented ${loss_prevented:,.2f} ({100 * loss_prevented / fraud_loss:.1f}% of fraud loss)

## Findings
- Fraud concentrates in card-not-present, foreign and night-hour (00:00–04:59) activity — the planted pattern the rules are built to catch.
- Largest fraud-loss category: **{top_cat.index[0]}** (${top_cat.iloc[0]:,.2f}).
- Precision is deliberately reported alongside recall: every false positive is a good customer interrupted, so a high-recall rule with poor precision is not automatically a win.
- Card-testing probes (sub-$3 online transactions before large fraud) are visible in the data and are a classic pre-fraud signal a velocity/amount-sequence rule can exploit.

## Honest limitations
- Rule-based detection is transparent and explainable to investigators, but it cannot learn new patterns, scores no risk gradient, and fraudsters adapt to fixed thresholds. Production issuers layer ML models on top of rules.
- Labels here are planted in synthetic data; real-world fraud labels arrive weeks later via chargebacks and are noisy.
"""
    with open("outputs/insights.md", "w") as f:
        f.write(insights)
    print("Wrote outputs/kpi_summary.csv, outputs/rule_performance.csv, "
          "outputs/fraud_by_channel.csv, outputs/insights.md")
    print(f"Fraud rate: {100 * len(fraud) / total:.2f}% | "
          f"Precision: {overall['precision_pct']:.2f}% | "
          f"Recall: {overall['recall_pct']:.2f}% | "
          f"Loss prevented: ${loss_prevented:,.2f}")


if __name__ == "__main__":
    main()
