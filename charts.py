"""Generate the 10 dashboard charts. Run: python3 charts.py
(some charts read outputs/*.csv, so run analysis.py first.)

Colour discipline — the "serious risk" palette, applied on every chart:
crimson/burgundy always means fraud; steel/slate/grey-teal carry the
legitimate and context series, so "red = fraud" reads instantly.
No yellow/gold, no navy, no pale colours; lines are never black/grey.
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap

CRIMSON, BURGUNDY, STEEL, SLATE, GREYTEAL = \
    "#C0392B", "#922B21", "#2E86AB", "#5D6D7E", "#4E7A6B"

plt.rcParams.update({
    "figure.dpi": 150, "font.size": 10,
    "axes.titlesize": 12, "axes.titleweight": "bold",
    "axes.labelsize": 10, "figure.facecolor": "white",
    "axes.facecolor": "white", "savefig.facecolor": "white",
})


def main():
    df = pd.read_csv("data/transactions.csv", parse_dates=["txn_datetime"])
    df["hour"] = df["txn_datetime"].dt.hour
    fraud = df[df["is_fraud"] == 1]
    legit = df[df["is_fraud"] == 0]

    # 1) Fraud rate by hour — the overnight attack window
    h = df.groupby("hour").agg(n=("txn_id", "count"),
                               f=("is_fraud", "sum")).reindex(range(24))
    h["rate"] = 100 * h["f"] / h["n"]
    peak_hour = int(h["f"].idxmax())
    fig, ax = plt.subplots(figsize=(8, 4.4))
    ax.bar(h.index, h["rate"],
           color=[CRIMSON if 0 <= x <= 4 else STEEL for x in h.index])
    ax.annotate(f"Peak hour {peak_hour:02d}:00 — {int(h['f'].max())} frauds",
                (peak_hour, h.loc[peak_hour, "rate"]),
                textcoords="offset points", xytext=(12, 2),
                fontsize=9.5, color=BURGUNDY, fontweight="bold")
    ax.text(14, h["rate"].max() * 0.86, "Night window\n00:00–04:59 (red bars)",
            ha="center", fontsize=9.5, color=BURGUNDY)
    ax.set_xlabel("Hour of day")
    ax.set_ylabel("Fraud rate (% of transactions)")
    ax.set_title("Fraud Peaks Overnight — 83.7% of Fraud Lands "
                 "Between Midnight and 5am")
    ax.set_xticks(range(24))
    ax.set_ylim(0, h["rate"].max() * 1.18)
    fig.tight_layout(); fig.savefig("images/fraud_by_hour.png")
    plt.close(fig)

    # 2) Fraud vs legit ticket sizes — fraud lives at big amounts
    fig, ax = plt.subplots(figsize=(8, 4.4))
    bins = [0, 25, 50, 100, 200, 400, 700, 1200]
    ax.hist(legit["amount"], bins=bins, density=True, alpha=0.55,
            color=STEEL, label="Genuine transactions")
    ax.hist(fraud["amount"], bins=bins, density=True, alpha=0.85,
            color=CRIMSON, label="Fraud transactions")
    ax.axvline(fraud["amount"].mean(), color=BURGUNDY, ls="--", lw=1.8,
               label=f"Fraud average ${fraud['amount'].mean():,.0f}")
    ax.axvline(legit["amount"].mean(), color=SLATE, ls="--", lw=1.8,
               label=f"Genuine average ${legit['amount'].mean():,.0f}")
    ax.set_xlabel("Transaction amount (USD, binned)")
    ax.set_ylabel("Density (share of transactions per dollar)")
    ax.set_title("Fraud Tickets Are Far Bigger — \\$331 on Average "
                 "vs \\$90 Genuine")
    ax.legend(fontsize=9)
    fig.tight_layout(); fig.savefig("images/fraud_vs_legit_amounts.png")
    plt.close(fig)

    # 3) Heatmap: fraud count by hour of day x channel — single-hue red
    # ramp, white to deep burgundy, so the 2am online peak reads at once
    hc = pd.read_csv("outputs/fraud_by_hour_channel.csv", index_col="hour")
    cmap = LinearSegmentedColormap.from_list(
        "fraud_red", ["#FFFFFF", "#EFA9A0", "#D95F4E", CRIMSON, BURGUNDY])
    fig, ax = plt.subplots(figsize=(10, 3.8))
    im = ax.imshow(hc.values.T, aspect="auto", cmap=cmap, vmin=0,
                   vmax=float(hc.values.max()))
    ax.set_xticks(range(24)); ax.set_xticklabels(hc.index)
    ax.set_yticks(range(len(hc.columns)))
    ax.set_yticklabels(["Online (card-not-present)", "POS (card-present)",
                        "ATM"][:len(hc.columns)])
    for i in range(len(hc.columns)):
        for j in range(24):
            v = int(hc.values[j, i])
            ax.text(j, i, v, ha="center", va="center", fontsize=7.5,
                    color="white" if v >= 10 else BURGUNDY)
    ax.set_xlabel("Hour of day"); ax.set_ylabel("Channel")
    ax.set_title("The Attack Is Online and Overnight — "
                 "Hottest Cell: 2am Online, 36 Frauds")
    fig.colorbar(im, ax=ax, shrink=0.9, label="Fraud count")
    fig.tight_layout(); fig.savefig("images/fraud_heatmap.png")
    plt.close(fig)

    # 4) Rule trade-off curve: cumulative flags vs cumulative recall
    rc = pd.read_csv("outputs/rule_cumulative.csv")
    # Steps 0-3 get labels; step 4 (R4) lands on the exact same point as
    # step 3, so its story is folded into the step-3 label.
    labels = ["No rules", "+R1 Amount", "+R2 Online + Foreign",
              "+R3 Night"]
    offsets = [(8, 8), (8, 10), (8, -26), (-64, 12)]
    ha = ["left", "left", "left", "left"]
    fig, ax = plt.subplots(figsize=(8, 4.4))
    ax.plot(rc["flagged"], rc["recall_pct"], color=CRIMSON, lw=2.2,
            marker="o", markersize=7, markerfacecolor=BURGUNDY,
            markeredgecolor=CRIMSON, zorder=3)
    for k, ((_, r), lab) in enumerate(zip(rc.iterrows(), labels)):
        text = (f"{lab}\n{int(r['flagged'])} flagged · "
                f"{r['recall_pct']:.1f}% recall")
        if k == len(labels) - 1:
            # R4's point coincides with this one: its 2 catches were
            # already flagged by earlier rules, so it adds no new flags.
            text += "\n+R4 Velocity adds 0 new flags\n(same point)"
        ax.annotate(text, (r["flagged"], r["recall_pct"]),
                    textcoords="offset points", xytext=offsets[k],
                    fontsize=8.5, ha=ha[k])
    ax.set_xlabel("Cumulative transactions flagged")
    ax.set_ylabel("Cumulative fraud caught (recall %)")
    ax.set_title("Rule Trade-Off — Each Rule Buys Recall With Flags; "
                 "R4 Adds Nothing New")
    ax.set_xlim(-10, rc["flagged"].max() * 1.22)
    ax.set_ylim(0, 104)
    ax.grid(alpha=0.25)
    fig.tight_layout(); fig.savefig("images/rule_tradeoff.png")
    plt.close(fig)

    # 5) Donut: fraud loss share by merchant category
    loss = fraud.groupby("merchant_category")["amount"].sum() \
                .sort_values(ascending=False)
    donut_colors = [CRIMSON, STEEL, BURGUNDY, GREYTEAL][:len(loss)]
    fig, ax = plt.subplots(figsize=(8, 4.4))
    wedges, _ = ax.pie(
        loss.values, colors=donut_colors, startangle=90,
        wedgeprops=dict(width=0.42, edgecolor="white", linewidth=1.5))
    ax.text(0, 0, f"Total loss\n${loss.sum():,.0f}", ha="center",
            va="center", fontsize=10.5, color=BURGUNDY, fontweight="bold")
    legend_labels = [f"{c}: ${v:,.0f} ({100 * v / loss.sum():.1f}%)"
                     for c, v in loss.items()]
    ax.legend(wedges, legend_labels, fontsize=9, loc="center left",
              bbox_to_anchor=(0.90, 0.5))
    ax.set_title("Where the Fraud Money Went — "
                 "3 Categories Hold 92% of the Loss")
    fig.tight_layout()
    fig.savefig("images/fraud_loss_donut.png", bbox_inches="tight")
    plt.close(fig)

    # 6) Box plot: fraud ticket sizes by merchant category
    order = (fraud.groupby("merchant_category")["amount"].median()
             .sort_values(ascending=False).index.tolist())
    data = [fraud.loc[fraud["merchant_category"] == c, "amount"]
            for c in order]
    box_colors = [CRIMSON, STEEL, BURGUNDY, GREYTEAL]
    fig, ax = plt.subplots(figsize=(8, 4.4))
    bp = ax.boxplot(
        data, patch_artist=True, labels=order,
        medianprops=dict(color="white", linewidth=2),
        whiskerprops=dict(color=SLATE), capprops=dict(color=SLATE),
        flierprops=dict(markerfacecolor=CRIMSON, markeredgecolor=CRIMSON,
                        markersize=4))
    for patch, c in zip(bp["boxes"], box_colors):
        patch.set_facecolor(c)
    for i, s in enumerate(data, start=1):
        ax.annotate(f"median ${s.median():,.0f}",
                    (i, s.median()), textcoords="offset points",
                    xytext=(34, -4), ha="left", fontsize=8.5, color=SLATE)
    ax.set_ylabel("Fraud transaction amount (USD)")
    ax.set_title("Fraud Ticket Sizes — Travel Runs Big, "
                 "E-Commerce Runs Tiny (Probes)")
    fig.tight_layout(); fig.savefig("images/fraud_amount_by_category_box.png")
    plt.close(fig)

    # 7) Fraud rate by transaction amount band
    band = pd.read_csv("outputs/fraud_by_amount_band.csv")
    band_colors = [CRIMSON, GREYTEAL, GREYTEAL, STEEL, BURGUNDY, CRIMSON]
    fig, ax = plt.subplots(figsize=(8, 4.4))
    ax.bar(band["amount_band"], band["fraud_rate_pct"],
           color=band_colors[:len(band)])
    for _, r in band.iterrows():
        ax.text(r["amount_band"], r["fraud_rate_pct"] + 1.6,
                f"{r['fraud_rate_pct']:.2f}%\n({int(r['fraud_txns'])}/"
                f"{int(r['transactions'])})",
                ha="center", fontsize=8.5)
    ax.set_xlabel("Transaction amount band (USD)")
    ax.set_ylabel("Fraud rate (% of transactions in band)")
    ax.set_title("Tiny Charges Are Mostly Fraud (Card-Testing Probes)\n"
                 "Big Tickets Hold the Money")
    ax.set_ylim(0, band["fraud_rate_pct"].max() * 1.22)
    fig.tight_layout(); fig.savefig("images/fraud_rate_by_amount_band.png")
    plt.close(fig)

    # 8) Rule performance: precision vs recall per rule
    rp = pd.read_csv("outputs/rule_performance.csv")
    rule_labels = {"r1_amount": "R1\nAmount", "r2_online_foreign":
                   "R2\nOnline+Foreign", "r3_night": "R3\nNight",
                   "r4_velocity": "R4\nVelocity",
                   "ANY rule (combined)": "Combined\n(any rule)"}
    rp["label"] = rp["rule"].map(rule_labels)
    x = range(len(rp)); w = 0.38
    fig, ax = plt.subplots(figsize=(8, 4.4))
    b1 = ax.bar([i - w / 2 for i in x], rp["precision_pct"], width=w,
                color=STEEL, label="Precision % — of flags, share truly fraud")
    b2 = ax.bar([i + w / 2 for i in x], rp["recall_pct"], width=w,
                color=CRIMSON,
                label="Recall % — of all fraud, share caught")
    for bars in (b1, b2):
        for rect in bars:
            ax.text(rect.get_x() + rect.get_width() / 2,
                    rect.get_height() + 2, f"{rect.get_height():.1f}%",
                    ha="center", fontsize=8.5)
    ax.set_xticks(list(x)); ax.set_xticklabels(rp["label"], fontsize=8.5)
    ax.set_ylabel("%")
    ax.set_ylim(0, 112)
    ax.set_title("Rule Scorecard — Precision vs Recall, Rule by Rule")
    ax.legend(fontsize=8.5)
    fig.tight_layout(); fig.savefig("images/rule_performance_chart.png")
    plt.close(fig)

    # 9) Fraud rate: foreign vs home transactions
    fo = pd.read_csv("outputs/fraud_by_origin.csv")
    fo = fo.set_index("origin").reindex(["foreign", "home"]).reset_index()
    fig, ax = plt.subplots(figsize=(8, 4.4))
    ax.bar(["Foreign", "Home"], fo["fraud_rate_pct"],
           color=[CRIMSON, STEEL], width=0.55)
    for _, r in fo.iterrows():
        label = "Foreign" if r["origin"] == "foreign" else "Home"
        ax.text(label, r["fraud_rate_pct"] + 1.2,
                f"{r['fraud_rate_pct']:.2f}%\n({int(r['fraud_txns'])} fraud of "
                f"{int(r['transactions']):,} txns)",
                ha="center", fontsize=9.5)
    ax.set_ylabel("Fraud rate (% of transactions)")
    ax.set_title("Foreign Transactions Are ~46x Riskier Than Home Ones")
    ax.set_ylim(0, fo["fraud_rate_pct"].max() * 1.25)
    fig.tight_layout(); fig.savefig("images/foreign_vs_home.png")
    plt.close(fig)

    # 10) Cumulative fraud loss over Q1 2024 (daily)
    daily = (fraud.set_index("txn_datetime").resample("D")["amount"].sum()
             .reindex(pd.date_range(df["txn_datetime"].min().normalize(),
                                    df["txn_datetime"].max().normalize()),
                      fill_value=0.0))
    cum = daily.cumsum()
    fig, ax = plt.subplots(figsize=(8, 4.4))
    ax.fill_between(cum.index, cum.values, color=STEEL, alpha=0.30)
    ax.plot(cum.index, cum.values, color=CRIMSON, lw=2)
    month_end_dates = sorted(
        {ts for ts in (cum.index + pd.offsets.MonthEnd(0)).unique()
         if ts in cum.index})
    for ts in month_end_dates:
        lab = f"{ts.strftime('%b %d')}\n${cum.loc[ts]:,.0f}"
        ax.annotate(lab, (ts, cum.loc[ts]), fontsize=8.5,
                    ha="right", color=BURGUNDY,
                    xytext=(-4, 6), textcoords="offset points")
        ax.plot([ts], [cum.loc[ts]], marker="o", color=BURGUNDY,
                markersize=5)
    last_ts = cum.index[-1]
    ax.annotate(f"{last_ts.strftime('%b %d')}\n${cum.iloc[-1]:,.0f}",
                (last_ts, cum.iloc[-1]), fontsize=8.5, ha="right",
                color=BURGUNDY, xytext=(-4, -26),
                textcoords="offset points")
    ax.plot([last_ts], [cum.iloc[-1]], marker="o", color=BURGUNDY,
            markersize=5)
    ax.set_ylabel("Cumulative fraud loss (USD)")
    ax.set_title(f"Cumulative Fraud Loss — a Steady Drip All Quarter "
                 f"(${cum.iloc[-1]:,.0f} Total)")
    ax.set_ylim(0, float(cum.iloc[-1]) * 1.08)
    fig.tight_layout(); fig.savefig("images/monthly_fraud_loss_area.png")
    plt.close(fig)
    print("Wrote 10 charts to images/")


if __name__ == "__main__":
    main()
