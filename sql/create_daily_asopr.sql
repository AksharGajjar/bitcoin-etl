-- create_daily_asopr.sql
-- Creates a cached table of daily Adjusted SOPR values
-- Reads from daily_spends (cached) and utxo_index (cached)
-- ⚠️ ONE-TIME COST: ~$2 (joins our cached tables)
-- After creation, dashboard queries are essentially FREE

CREATE OR REPLACE TABLE `{project_id}.bitcoin_analytics.daily_asopr`
PARTITION BY date
AS
WITH spend_with_origin AS (
    -- Join spends with their original creation data
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
)

, adjusted_spends AS (
    -- Filter: Only include coins held for more than 1 hour (aSOPR adjustment)
    SELECT
        spend_date
        , creation_date
        , btc_amount
    FROM spend_with_origin
    WHERE hours_held >= 1
)

SELECT
    a.spend_date AS date
    -- aSOPR = Realized Value / Realized Cap (value-weighted)
    , SAFE_DIVIDE(
        SUM(a.btc_amount * p_sold.close),
        SUM(a.btc_amount * p_bought.close)
    ) AS sopr
    -- Additional metrics
    , SUM(a.btc_amount) / 100000000 AS total_btc_moved  -- Convert satoshis to BTC
    , COUNT(*) AS num_transactions
FROM adjusted_spends a
INNER JOIN `{project_id}.bitcoin_analytics.daily_prices` p_sold
    ON a.spend_date = p_sold.date
INNER JOIN `{project_id}.bitcoin_analytics.daily_prices` p_bought
    ON a.creation_date = p_bought.date
GROUP BY 1
;
