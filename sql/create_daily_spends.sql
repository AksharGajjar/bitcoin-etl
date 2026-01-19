-- create_daily_spends.sql
-- Creates a cached table of all Bitcoin spend events
-- This avoids repeatedly scanning the expensive public transactions table
-- ⚠️ ONE-TIME COST: ~$5 (scans full transactions table since 2019)

CREATE OR REPLACE TABLE `{project_id}.bitcoin_analytics.daily_spends`
PARTITION BY spend_date
CLUSTER BY spent_transaction_hash
AS
SELECT
    DATE(t.block_timestamp) AS spend_date
    , t.block_timestamp AS spend_timestamp
    , i.spent_transaction_hash
    , i.spent_output_index
FROM `bigquery-public-data.crypto_bitcoin.transactions` t
    , UNNEST(t.inputs) i
WHERE t.block_timestamp >= '2019-01-01'
    AND i.spent_transaction_hash IS NOT NULL
;
