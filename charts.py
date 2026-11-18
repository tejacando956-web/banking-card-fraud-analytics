"""Generate the 4 dashboard charts. Run: python3 charts.py"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

plt.rcParams.update({"figure.dpi": 150, "font.size": 10})
TEAL, NAVY, RED, GREY = "#0e7c7b", "#1f3a5f", "#c0392b", "#95a5a6"


def main():
    df = pd.read_csv("data/transactions.csv", parse_dates=["txn_datetime"])
    df["hour"] = df["txn_datetime"].dt.hour
    fraud = df[df["is_fraud"] == 1]

    # 1) Fraud rate by channel
    g = df.groupby("channel").agg(n=("txn_id", "count"),
                                  f=("is_fraud", "sum")).reset_index()
    g["rate"] = 100 * g["f"] / g["n"]
    color_map = {"online": RED, "ATM": NAVY, "POS": TEAL}
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.bar(g["channel"], g["rate"],
           color=[color_map[c] for c in g["channel"]])
    for _, r in g.iterrows():
        ax.text(r["channel"], r["rate"] + 0.15,
                f"{r['rate']:.2f}%  ({int(r['f'])}/{int(r['n'])})",
                ha="center", fontsize=9)
    ax.set_ylabel("Fraud rate (% of transactions)")
    ax.set_title("Fraud Rate by Channel — Card-Not-Present Is the Risk")
    fig.tight_layout(); fig.savefig("images/fraud_by_channel.png")
    plt.close(fig)

    # 2) Fraud vs legit share by hour
    h = df.groupby("hour").agg(n=("txn_id", "count"),
                               f=("is_fraud", "sum")).reindex(range(24))
    h["rate"] = 100 * h["f"] / h["n"]
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.bar(h.index, h["rate"], color=[RED if 0 <= x <= 4 else TEAL
                                      for x in h.index])
    ax.axvspan(-0.5, 4.5, color=RED, alpha=0.07)
    ax.text(2, h["rate"].max() * 0.92, "Night window\n00:00–04:59",
            ha="center", color=RED, fontsize=9)
    ax.set_xlabel("Hour of day"); ax.set_ylabel("Fraud rate (%)")
    ax.set_title("Fraud Rate by Hour — Attacks Cluster Overnight")
    ax.set_xticks(range(24))
    fig.tight_layout(); fig.savefig("images/fraud_by_hour.png")
    plt.close(fig)

    # 3) Fraud vs legit ticket sizes
    fig, ax = plt.subplots(figsize=(7, 4))
    bins = [0, 25, 50, 100, 200, 400, 700, 1200]
    ax.hist(df[df.is_fraud == 0]["amount"], bins=bins, density=True,
            alpha=0.65, color=TEAL, label="Legitimate")
    ax.hist(fraud["amount"], bins=bins, density=True, alpha=0.75,
            color=RED, label="Fraud")
    ax.axvline(fraud["amount"].mean(), color=RED, ls="--",
               label=f"Fraud avg ${fraud['amount'].mean():,.0f}")
    ax.axvline(df[df.is_fraud == 0]["amount"].mean(), color=NAVY, ls="--",
               label=f"Legit avg ${df[df.is_fraud == 0]['amount'].mean():,.0f}")
    ax.set_xlabel("Transaction amount (USD, binned)")
    ax.set_ylabel("Density")
    ax.set_title("Fraud Tickets Are Far Larger Than Legitimate Tickets")
    ax.legend(fontsize=8)
    fig.tight_layout(); fig.savefig("images/fraud_vs_legit_amounts.png")
    plt.close(fig)

    # 4) Fraud loss by merchant category
    cat = fraud.groupby("merchant_category")["amount"].sum() \
               .sort_values(ascending=True)
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.barh(cat.index, cat.values, color=NAVY)
    for i, v in enumerate(cat.values):
        ax.text(v + 400, i, f"${v:,.0f}", va="center", fontsize=9)
    ax.set_xlabel("Fraud loss (USD)")
    ax.set_title("Fraud Loss by Merchant Category")
    ax.set_xlim(0, cat.max() * 1.22)
    fig.tight_layout(); fig.savefig("images/fraud_by_category.png")
    plt.close(fig)
    print("Wrote 4 charts to images/")


if __name__ == "__main__":
    main()
