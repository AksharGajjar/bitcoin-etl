-- update_daily_spends.sql
-- Incremental update: Adds yesterday's spend data to daily_spends table
-- Run daily via scheduled query
-- Cost: ~$0.03/day

INSERT INTO `{project_id}.bitcoin_analytics.daily_spends`
    (spend_date, spend_timestamp, spent_transaction_hash, spent_output_index)
SELECT
    DATE(t.block_timestamp) AS spend_date
    , t.block_timestamp AS spend_timestamp
    , i.spent_transaction_hash
    , i.spent_output_index
FROM `bigquery-public-data.crypto_bitcoin.transactions` t
    , UNNEST(t.inputs) i
WHERE DATE(t.block_timestamp) = DATE_SUB(CURRENT_DATE(), INTERVAL 1 DAY)
    AND i.spent_transaction_hash IS NOT NULL
;
