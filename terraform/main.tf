# main.tf
# Core BigQuery infrastructure for Bitcoin SOPR Analytics

# BigQuery Dataset
resource "google_bigquery_dataset" "bitcoin_analytics" {
  dataset_id                 = var.dataset_id
  location                   = var.dataset_location
  description                = "Bitcoin SOPR Analytics - Price data and UTXO index"
  delete_contents_on_destroy = false

  labels = {
    project     = "bitcoin-sopr"
    managed_by  = "terraform"
    environment = "production"
  }
}

# Daily Prices Table
resource "google_bigquery_table" "daily_prices" {
  dataset_id          = google_bigquery_dataset.bitcoin_analytics.dataset_id
  table_id            = "daily_prices"
  description         = "Daily BTC-USD prices from Yahoo Finance"
  deletion_protection = true

  schema = jsonencode([
    {
      name        = "date"
      type        = "DATE"
      mode        = "REQUIRED"
      description = "Trading date"
    },
    {
      name        = "open"
      type        = "FLOAT64"
      mode        = "REQUIRED"
      description = "Opening price (USD)"
    },
    {
      name        = "high"
      type        = "FLOAT64"
      mode        = "REQUIRED"
      description = "Daily high price (USD)"
    },
    {
      name        = "low"
      type        = "FLOAT64"
      mode        = "REQUIRED"
      description = "Daily low price (USD)"
    },
    {
      name        = "close"
      type        = "FLOAT64"
      mode        = "REQUIRED"
      description = "Closing price (USD)"
    },
    {
      name        = "volume"
      type        = "FLOAT64"
      mode        = "REQUIRED"
      description = "Trading volume"
    }
  ])

  labels = {
    table_type = "price_data"
    source     = "yfinance"
  }
}

# UTXO Index Table (conditional creation)
resource "google_bigquery_table" "utxo_index" {
  count               = var.enable_utxo_index ? 1 : 0
  dataset_id          = google_bigquery_dataset.bitcoin_analytics.dataset_id
  table_id            = "utxo_index"
  description         = "Bitcoin UTXO creation index for SOPR calculation"
  deletion_protection = true

  # Note: The actual data is loaded via SQL query in etl/create_index.py
  # This just creates the table structure
  time_partitioning {
    type  = "DAY"
    field = "block_date"
  }

  clustering = ["tx_hash"]

  schema = jsonencode([
    {
      name        = "tx_hash"
      type        = "STRING"
      mode        = "REQUIRED"
      description = "Transaction hash where UTXO was created"
    },
    {
      name        = "output_index"
      type        = "INT64"
      mode        = "REQUIRED"
      description = "Output index within transaction"
    },
    {
      name        = "block_date"
      type        = "DATE"
      mode        = "REQUIRED"
      description = "Date of block (for partitioning)"
    },
    {
      name        = "created_at"
      type        = "TIMESTAMP"
      mode        = "REQUIRED"
      description = "Block timestamp when UTXO was created"
    },
    {
      name        = "btc_amount"
      type        = "FLOAT64"
      mode        = "REQUIRED"
      description = "Amount in BTC"
    }
  ])

  labels = {
    table_type = "utxo_index"
    source     = "bitcoin_public_ledger"
    cost_alert = "high"
  }
}
