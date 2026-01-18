-- sopr_query.sql
-- Calculates daily SOPR (Spent Output Profit Ratio)
-- Parameters: @start_date, @end_date (DATE type)
-- Returns: date, sopr

WITH spends AS (
    SELECT 
        t.block_timestamp
        , i.spent_transaction_hash
        , i.spent_output_index
    FROM `bigquery-public-data.crypto_bitcoin.transactions` t
        , UNNEST(t.inputs) i
    WHERE t.block_timestamp BETWEEN @start_date AND @end_date
)

SELECT 
    DATE(s.block_timestamp) AS date
    , AVG(p_sold.price_usd / p_bought.price_usd) AS sopr
FROM spends s
INNER JOIN `{project_id}.bitcoin_analytics.utxo_index` c 
    ON s.spent_transaction_hash = c.tx_hash 
    AND s.spent_output_index = c.output_index
INNER JOIN `{project_id}.bitcoin_analytics.daily_prices` p_sold 
    ON DATE(s.block_timestamp) = p_sold.date
INNER JOIN `{project_id}.bitcoin_analytics.daily_prices` p_bought 
    ON c.block_date = p_bought.date
GROUP BY 1
ORDER BY 1 DESC
;
