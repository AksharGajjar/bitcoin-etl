-- update_daily_asopr.sql
-- Incremental update: Calculates yesterday's aSOPR and appends to daily_asopr
-- Run daily via scheduled query (after update_daily_spends completes)
-- Cost: ~$0.02/day

INSERT INTO `{project_id}.bitcoin_analytics.daily_asopr`
    (date, sopr, total_btc_moved, num_transactions)

WITH spend_with_origin AS (
    SELECT
        s.spend_timestamp
        , s.spend_date
        , c.created_at AS creation_timestamp
        , c.block_date AS creation_date
        , c.btc_amount
        , TIMESTAMP_DIFF(s.spend_timestamp, c.created_at, HOUR) AS hours_held
    FROM `{project_id}.bitcoin_analytics.daily_spends` s
    INNER JOIN `{project_id}.bitcoin_analytics.utxo_index` c
        ON s.spent_transaction_hash = c.tx_hash
        AND s.spent_output_index = c.output_index
    -- Only process yesterday's spends
    WHERE s.spend_date = DATE_SUB(CURRENT_DATE(), INTERVAL 1 DAY)
    -- Optimization: Only look at UTXOs created in last 2 years
    AND c.block_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 730 DAY)
)

, adjusted_spends AS (
    SELECT
        spend_date
        , creation_date
        , btc_amount
    FROM spend_with_origin
    WHERE hours_held >= 1
)

SELECT
    a.spend_date AS date
    , SAFE_DIVIDE(
        SUM(a.btc_amount * p_sold.close),
        SUM(a.btc_amount * p_bought.close)
    ) AS sopr
    , SUM(a.btc_amount) / 100000000 AS total_btc_moved
    , COUNT(*) AS num_transactions
FROM adjusted_spends a
INNER JOIN `{project_id}.bitcoin_analytics.daily_prices` p_sold
    ON a.spend_date = p_sold.date
INNER JOIN `{project_id}.bitcoin_analytics.daily_prices` p_bought
    ON a.creation_date = p_bought.date
GROUP BY 1
;
