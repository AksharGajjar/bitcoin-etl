-- utxo_index.sql
-- Creates a partitioned/clustered index of Bitcoin UTXOs for efficient SOPR calculation
-- ⚠️ WARNING: Scans ~1TB+ of data. Estimated cost: $25-50
-- Run with: bq query --use_legacy_sql=false < sql/utxo_index.sql

CREATE OR REPLACE TABLE `{project_id}.bitcoin_analytics.utxo_index`
PARTITION BY block_date
CLUSTER BY tx_hash
AS
SELECT 
    hash AS tx_hash
    , o.index AS output_index
    , DATE(block_timestamp) AS block_date
    , block_timestamp AS created_at
    , o.value AS btc_amount
FROM `bigquery-public-data.crypto_bitcoin.transactions`
    , UNNEST(outputs) AS o
WHERE block_timestamp >= '2019-01-01' 
    AND o.value > 0.0001  -- Ignore dust
;
