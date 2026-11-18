-- Card Fraud Analytics — SQL analysis queries (SQLite/Postgres-compatible)
-- Portfolio project, synthetic data. Table: transactions
-- (txn_id, card_id, txn_datetime, amount, merchant_category, channel,
--  card_present, foreign, is_fraud)

-- Q1. Overall fraud rate, in percent and basis points (bps is the unit
--     fraud teams actually quote: 100 bps = 1.00%)
SELECT COUNT(*)                                        AS total_txns,
       SUM(is_fraud)                                   AS fraud_txns,
       ROUND(100.0 * SUM(is_fraud) / COUNT(*), 2)      AS fraud_rate_pct,
       ROUND(10000.0 * SUM(is_fraud) / COUNT(*), 1)    AS fraud_rate_bps,
       ROUND(SUM(CASE WHEN is_fraud = 1 THEN amount END), 2) AS fraud_loss_usd
FROM transactions;

-- Q2. Fraud rate and fraud share by channel (card-present vs not-present)
SELECT channel,
       COUNT(*)                                        AS txns,
       SUM(is_fraud)                                   AS fraud_txns,
       ROUND(100.0 * SUM(is_fraud) / COUNT(*), 2)      AS fraud_rate_pct,
       ROUND(100.0 * SUM(is_fraud) /
             SUM(SUM(is_fraud)) OVER (), 2)            AS fraud_share_pct
FROM transactions
GROUP BY channel
ORDER BY fraud_rate_pct DESC;

-- Q3. Fraud loss by merchant category with running share (window function)
SELECT merchant_category,
       SUM(amount)                                     AS fraud_loss_usd,
       ROUND(100.0 * SUM(amount) /
             SUM(SUM(amount)) OVER (), 2)              AS loss_share_pct,
       ROUND(100.0 * SUM(SUM(amount)) OVER (
             ORDER BY SUM(amount) DESC) /
             SUM(SUM(amount)) OVER (), 2)              AS cumulative_share_pct
FROM transactions
WHERE is_fraud = 1
GROUP BY merchant_category
ORDER BY fraud_loss_usd DESC;

-- Q4. Hourly fraud pattern — where does the night window stand out?
SELECT CAST(strftime('%H', txn_datetime) AS INTEGER)   AS hour_of_day,
       COUNT(*)                                        AS txns,
       SUM(is_fraud)                                   AS fraud_txns,
       ROUND(100.0 * SUM(is_fraud) / COUNT(*), 2)      AS fraud_rate_pct
FROM transactions
GROUP BY hour_of_day
ORDER BY hour_of_day;

-- Q5. Foreign + card-not-present cohort vs everyone else
SELECT CASE WHEN card_present = 0 AND foreign = 1
            THEN 'online_foreign' ELSE 'other' END     AS cohort,
       COUNT(*) AS txns, SUM(is_fraud) AS fraud_txns,
       ROUND(100.0 * SUM(is_fraud) / COUNT(*), 2)      AS fraud_rate_pct
FROM transactions
GROUP BY cohort;

-- Q6. Velocity detection with LAG: transactions whose previous txn on the
--     same card was < 10 minutes earlier (burst behaviour)
SELECT txn_id, card_id, txn_datetime, amount, is_fraud,
       LAG(txn_datetime) OVER (PARTITION BY card_id
                               ORDER BY txn_datetime)  AS prev_txn_time
FROM transactions
-- wrap in a CTE and filter on the time gap in production SQL:
-- WITH lagged AS ( ... ) SELECT * FROM lagged
-- WHERE (julianday(txn_datetime) - julianday(prev_txn_time)) * 1440 < 10;
;

-- Q7. Card-testing probe hunt: cards with a sub-$3 online txn followed by
--     a large (>$300) txn within 24 hours
WITH probes AS (
    SELECT card_id, txn_datetime AS probe_time
    FROM transactions
    WHERE amount < 3 AND channel = 'online'
)
SELECT DISTINCT t.card_id, t.txn_datetime, t.amount, t.is_fraud
FROM transactions t
JOIN probes p ON p.card_id = t.card_id
WHERE t.amount > 300
  AND t.txn_datetime > p.probe_time
  AND t.txn_datetime <= datetime(p.probe_time, '+24 hours')
ORDER BY t.card_id, t.txn_datetime;

-- Q8. Average ticket: fraud vs legitimate, by category
SELECT merchant_category,
       ROUND(AVG(CASE WHEN is_fraud = 1 THEN amount END), 2) AS avg_fraud_ticket,
       ROUND(AVG(CASE WHEN is_fraud = 0 THEN amount END), 2) AS avg_legit_ticket
FROM transactions
GROUP BY merchant_category
ORDER BY avg_fraud_ticket DESC;

-- Q9. Rule simulation in SQL (mirrors analysis.py R1+R2): amount above a
--     per-category threshold, or online+foreign — with precision/recall math
WITH flagged AS (
    SELECT *,
           CASE WHEN (merchant_category = 'electronics' AND amount > 400)
                  OR (merchant_category = 'travel'      AND amount > 600)
                  OR (merchant_category = 'e-commerce'  AND amount > 300)
                  OR (card_present = 0 AND foreign = 1)
                THEN 1 ELSE 0 END AS rule_flag
    FROM transactions
)
SELECT SUM(rule_flag)                                          AS flagged,
       SUM(rule_flag * is_fraud)                               AS true_positives,
       SUM(rule_flag * (1 - is_fraud))                         AS false_positives,
       ROUND(100.0 * SUM(rule_flag * is_fraud) /
             NULLIF(SUM(rule_flag), 0), 2)                     AS precision_pct,
       ROUND(100.0 * SUM(rule_flag * is_fraud) /
             SUM(is_fraud), 2)                                 AS recall_pct
FROM flagged;

-- Q10. Chargeback proxy: expected chargeback count and dollars by category
--      (assumes 65% of confirmed fraud converts to a chargeback)
SELECT merchant_category,
       SUM(is_fraud)                                   AS fraud_txns,
       ROUND(0.65 * SUM(is_fraud), 1)                  AS est_chargebacks,
       ROUND(0.65 * SUM(CASE WHEN is_fraud = 1
                             THEN amount END), 2)      AS est_chargeback_usd
FROM transactions
GROUP BY merchant_category
HAVING fraud_txns > 0
ORDER BY est_chargeback_usd DESC;
