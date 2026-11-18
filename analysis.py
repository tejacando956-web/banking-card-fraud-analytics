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

    # Fraud count by hour x channel (heatmap source table)
    hour_channel = (fraud.groupby(["hour", "channel"]).size()
                    .unstack(fill_value=0)
                    .reindex(index=range(24),
                             columns=["online", "POS", "ATM"], fill_value=0))
    hour_channel.index.name = "hour"
    hour_channel.to_csv("outputs/fraud_by_hour_channel.csv")

    # Cumulative rule trade-off: switch the rules on one at a time, in the
    # order they appear in rule_performance, and track the running union.
    cumulative_rows = [{"step": 0, "rules_active": "none", "flagged": 0,
                        "true_positives": 0, "false_positives": 0,
                        "precision_pct": 0.0, "recall_pct": 0.0}]
    running_mask = pd.Series(False, index=df.index)
    for i, col in enumerate(rule_cols, start=1):
        running_mask = running_mask | df[col]
        ev = evaluate(df, running_mask, "+".join(rule_cols[:i]))
        cumulative_rows.append({
            "step": i, "rules_active": "+".join(rule_cols[:i]),
            "flagged": ev["flagged"],
            "true_positives": ev["true_positives"],
            "false_positives": ev["false_positives"],
            "precision_pct": ev["precision_pct"],
            "recall_pct": ev["recall_pct"]})
    pd.DataFrame(cumulative_rows).to_csv(
        "outputs/rule_cumulative.csv", index=False)

    # Fraud by calendar month
    df["month"] = df["txn_datetime"].dt.strftime("%Y-%m")
    by_month = df.groupby("month").agg(
        transactions=("txn_id", "count"), fraud_txns=("is_fraud", "sum"),
        fraud_loss_usd=("fraud_amount", "sum")).reset_index()
    by_month["fraud_loss_usd"] = by_month["fraud_loss_usd"].round(2)
    by_month["fraud_rate_pct"] = (
        100 * by_month["fraud_txns"] / by_month["transactions"]).round(2)
    by_month.to_csv("outputs/fraud_by_month.csv", index=False)

    # Fraud rate by transaction amount band — tiny card-testing probes at
    # the bottom, big-ticket fraud at the top, everyday spending in between.
    band_edges = [0, 10, 50, 100, 250, 500, float("inf")]
    band_labels = ["$0-10", "$10-50", "$50-100", "$100-250", "$250-500",
                   "$500+"]
    df["amount_band"] = pd.cut(df["amount"], bins=band_edges,
                               labels=band_labels, right=False)
    by_band = df.groupby("amount_band", observed=True).agg(
        transactions=("txn_id", "count"), fraud_txns=("is_fraud", "sum"),
        fraud_loss_usd=("fraud_amount", "sum")).reset_index()
    by_band["fraud_loss_usd"] = by_band["fraud_loss_usd"].round(2)
    by_band["fraud_rate_pct"] = (
        100 * by_band["fraud_txns"] / by_band["transactions"]).round(2)
    by_band.to_csv("outputs/fraud_by_amount_band.csv", index=False)
    band_rate = {r.amount_band: float(r.fraud_rate_pct)
                 for r in by_band.itertuples()}

    # Fraud rate for foreign vs home transactions — foreign is a small
    # slice of volume but carries an outsized share of the fraud.
    by_origin = df.groupby("foreign").agg(
        transactions=("txn_id", "count"), fraud_txns=("is_fraud", "sum"),
        fraud_loss_usd=("fraud_amount", "sum")).reset_index()
    by_origin["origin"] = by_origin["foreign"].map(
        {True: "foreign", False: "home"})
    by_origin["fraud_loss_usd"] = by_origin["fraud_loss_usd"].round(2)
    by_origin["fraud_rate_pct"] = (
        100 * by_origin["fraud_txns"] / by_origin["transactions"]).round(2)
    by_origin["fraud_share_pct"] = (
        100 * by_origin["fraud_txns"] / len(fraud)).round(2)
    by_origin = by_origin[["origin", "transactions", "fraud_txns",
                           "fraud_loss_usd", "fraud_rate_pct",
                           "fraud_share_pct"]]
    by_origin.to_csv("outputs/fraud_by_origin.csv", index=False)
    origin_rate = {r.origin: float(r.fraud_rate_pct)
                   for r in by_origin.itertuples()}
    foreign_share = float(by_origin.loc[
        by_origin["origin"] == "foreign", "fraud_share_pct"].iloc[0])

    overnight_share = round(
        100 * float(fraud["hour"].between(0, 4).mean()), 2)
    fraud_by_hour = fraud.groupby("hour").size()
    peak_hour = int(fraud_by_hour.idxmax())
    peak_hour_count = int(fraud_by_hour.max())
    peak_cell = int(hour_channel.values.max())
    cat_loss = fraud.groupby("merchant_category")["amount"].sum()
    top_loss_share = round(100 * float(cat_loss.max()) / fraud_loss, 2)
    # The 15 headline KPIs. The fraud rate is one KPI quoted two ways
    # (percent and basis points: bps = 10,000 x fraud / total = 220.0).
    # Supporting detail (per-rule scores, the chargeback estimate,
    # home fraud rate, foreign share of fraud, amount-band rates,
    # peak-hour counts, category shares) lives in the breakdown CSVs
    # and insights.md, not in this summary table.
    kpis = [
        ("total_transactions", total),
        ("total_fraud_transactions", len(fraud)),
        ("fraud_rate_pct", round(100 * len(fraud) / total, 2)),
        ("fraud_loss_usd", round(fraud_loss, 2)),
        ("avg_fraud_ticket_usd", round(float(fraud["amount"].mean()), 2)),
        ("avg_legit_ticket_usd", round(float(legit["amount"].mean()), 2)),
        ("online_fraud_share_pct", online_share),
        ("rule_flagged_transactions", int(df["flagged"].sum())),
        ("rule_precision_pct", overall["precision_pct"]),
        ("rule_recall_pct", overall["recall_pct"]),
        ("est_loss_prevented_usd", round(loss_prevented, 2)),
        ("est_loss_prevented_pct_of_fraud_loss",
         round(100 * loss_prevented / fraud_loss, 2)),
        ("overnight_fraud_share_pct", overnight_share),
        ("peak_hour_channel_fraud_count", peak_cell),
        ("foreign_fraud_rate_pct", origin_rate["foreign"]),
    ]
    pd.DataFrame(kpis, columns=["kpi", "value"]).to_csv(
        "outputs/kpi_summary.csv", index=False)

    top_cat = (fraud.groupby("merchant_category")["amount"].sum()
               .sort_values(ascending=False))
    band_row = {r.amount_band: r for r in by_band.itertuples()}
    foreign_row = by_origin[by_origin["origin"] == "foreign"].iloc[0]
    home_row = by_origin[by_origin["origin"] == "home"].iloc[0]
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
- Largest fraud-loss category: **{top_cat.index[0]}** (${top_cat.iloc[0]:,.2f}, {top_loss_share:.1f}% of all fraud loss).
- **Overnight concentration:** {overnight_share:.1f}% of fraud occurs 00:00–04:59; the single busiest hour is {peak_hour:02d}:00 with {peak_hour_count} frauds, and the hottest hour x channel cell holds {peak_cell} frauds.
- **Rule trade-off curve:** switching rules on in order (R1 → R4), cumulative recall climbs {cumulative_rows[1]['recall_pct']:.2f}% → {cumulative_rows[2]['recall_pct']:.2f}% → {cumulative_rows[3]['recall_pct']:.2f}% → {overall['recall_pct']:.2f}% while cumulative flags grow {cumulative_rows[1]['flagged']} → {cumulative_rows[2]['flagged']} → {cumulative_rows[3]['flagged']} → {overall['flagged']} (outputs/rule_cumulative.csv).
- **Monthly trend:** """ + "; ".join(
        f"{r.month} {r.fraud_rate_pct:.2f}% ({int(r.fraud_txns)} frauds)"
        for r in by_month.itertuples()) + f""" (outputs/fraud_by_month.csv).
- **Amount bands tell two stories:** the $0-10 band is {band_rate['$0-10']:.2f}% fraud ({int(band_row['$0-10'].fraud_txns)} of {int(band_row['$0-10'].transactions)} transactions) — those are card-testing probes, not shopping. Everyday bands are almost clean ($10-50: {band_rate['$10-50']:.2f}%, $50-100: {band_rate['$50-100']:.2f}%), then risk climbs with ticket size: $100-250 is {band_rate['$100-250']:.2f}%, $250-500 is {band_rate['$250-500']:.2f}% and $500+ is {band_rate['$500+']:.2f}% (outputs/fraud_by_amount_band.csv).
- **Foreign transactions are the riskiest slice of the book:** only {int(foreign_row.transactions)} of {total:,} transactions ({100 * int(foreign_row.transactions) / total:.1f}%) are foreign, yet their fraud rate is {origin_rate['foreign']:.2f}% versus {origin_rate['home']:.2f}% for home transactions, and they account for {foreign_share:.1f}% of all fraud and ${float(foreign_row.fraud_loss_usd):,.2f} of the loss (outputs/fraud_by_origin.csv).
- Precision is deliberately reported alongside recall: every false positive is a good customer interrupted, so a high-recall rule with poor precision is not automatically a win.
- Card-testing probes (sub-$3 online transactions before large fraud) are visible in the data and are a classic pre-fraud signal a velocity/amount-sequence rule can exploit.

## Honest limitations
- Rule-based detection is transparent and explainable to investigators, but it cannot learn new patterns, scores no risk gradient, and fraudsters adapt to fixed thresholds. Production issuers layer ML models on top of rules.
- Labels here are planted in synthetic data; real-world fraud labels arrive weeks later via chargebacks and are noisy.
"""
    with open("outputs/insights.md", "w") as f:
        f.write(insights)
    print("Wrote outputs/kpi_summary.csv, outputs/rule_performance.csv, "
          "outputs/fraud_by_channel.csv, outputs/fraud_by_hour_channel.csv, "
          "outputs/rule_cumulative.csv, outputs/fraud_by_month.csv, "
          "outputs/fraud_by_amount_band.csv, outputs/fraud_by_origin.csv, "
          "outputs/insights.md")
    print(f"Fraud rate: {100 * len(fraud) / total:.2f}% | "
          f"Precision: {overall['precision_pct']:.2f}% | "
          f"Recall: {overall['recall_pct']:.2f}% | "
          f"Loss prevented: ${loss_prevented:,.2f}")


if __name__ == "__main__":
    main()
