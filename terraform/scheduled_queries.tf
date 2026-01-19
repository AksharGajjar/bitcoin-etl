# scheduled_queries.tf
# BigQuery scheduled queries for daily aSOPR pipeline
# Requires the BigQuery Data Transfer API to be enabled

# Enable the BigQuery Data Transfer API
resource "google_project_service" "bigquery_datatransfer" {
  project = var.project_id
  service = "bigquerydatatransfer.googleapis.com"

  disable_on_destroy = false
}

# Service account for scheduled queries
resource "google_service_account" "scheduled_query_sa" {
  count        = var.enable_scheduled_queries ? 1 : 0
  account_id   = "bq-scheduled-queries"
  display_name = "BigQuery Scheduled Queries Service Account"
  description  = "Service account for running scheduled BigQuery queries"
}

# Grant BigQuery permissions to the service account
resource "google_project_iam_member" "scheduled_query_bq_admin" {
  count   = var.enable_scheduled_queries ? 1 : 0
  project = var.project_id
  role    = "roles/bigquery.admin"
  member  = "serviceAccount:${google_service_account.scheduled_query_sa[0].email}"
}

# ============================================================================
# Scheduled Query: Update daily_spends
# Runs daily at 6:00 AM UTC to add yesterday's spend data
# ============================================================================
resource "google_bigquery_data_transfer_config" "update_daily_spends" {
  count = var.enable_scheduled_queries ? 1 : 0

  display_name           = "Daily Spends Update"
  location               = var.dataset_location
  data_source_id         = "scheduled_query"
  schedule               = "every day 06:00"
  destination_dataset_id = var.dataset_id

  params = {
    query = <<-EOT
      -- Incremental update: Adds yesterday's spend data
      INSERT INTO `${var.project_id}.${var.dataset_id}.daily_spends`
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
    EOT
  }

  service_account_name = var.enable_scheduled_queries ? google_service_account.scheduled_query_sa[0].email : null

  depends_on = [
    google_project_service.bigquery_datatransfer,
    google_project_iam_member.scheduled_query_bq_admin
  ]
}

# ============================================================================
# Scheduled Query: Update daily_asopr
# Runs daily at 6:30 AM UTC (after spends update) to calculate yesterday's aSOPR
# ============================================================================
resource "google_bigquery_data_transfer_config" "update_daily_asopr" {
  count = var.enable_scheduled_queries ? 1 : 0

  display_name           = "Daily aSOPR Update"
  location               = var.dataset_location
  data_source_id         = "scheduled_query"
  schedule               = "every day 06:30"
  destination_dataset_id = var.dataset_id

  params = {
    query = <<-EOT
      -- Incremental update: Calculate yesterday's aSOPR
      INSERT INTO `${var.project_id}.${var.dataset_id}.daily_asopr`
          (date, sopr, total_btc_moved, num_transactions)

      WITH spend_with_origin AS (
          SELECT
              s.spend_timestamp
              , s.spend_date
              , c.created_at AS creation_timestamp
              , c.block_date AS creation_date
              , c.btc_amount
              , TIMESTAMP_DIFF(s.spend_timestamp, c.created_at, HOUR) AS hours_held
          FROM `${var.project_id}.${var.dataset_id}.daily_spends` s
          INNER JOIN `${var.project_id}.${var.dataset_id}.utxo_index` c
              ON s.spent_transaction_hash = c.tx_hash
              AND s.spent_output_index = c.output_index
          WHERE s.spend_date = DATE_SUB(CURRENT_DATE(), INTERVAL 1 DAY)
              AND c.block_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 730 DAY)
      )

      , adjusted_spends AS (
          SELECT spend_date, creation_date, btc_amount
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
      INNER JOIN `${var.project_id}.${var.dataset_id}.daily_prices` p_sold
          ON a.spend_date = p_sold.date
      INNER JOIN `${var.project_id}.${var.dataset_id}.daily_prices` p_bought
          ON a.creation_date = p_bought.date
      GROUP BY 1
    EOT
  }

  service_account_name = var.enable_scheduled_queries ? google_service_account.scheduled_query_sa[0].email : null

  depends_on = [
    google_project_service.bigquery_datatransfer,
    google_project_iam_member.scheduled_query_bq_admin,
    google_bigquery_data_transfer_config.update_daily_spends
  ]
}

# ============================================================================
# Scheduled Query: Update daily_prices
# Runs daily at 5:00 AM UTC to fetch latest BTC price
# ============================================================================
resource "google_bigquery_data_transfer_config" "update_daily_prices" {
  count = var.enable_scheduled_queries ? 1 : 0

  display_name           = "Daily Prices Update"
  location               = var.dataset_location
  data_source_id         = "scheduled_query"
  schedule               = "every day 05:00"
  destination_dataset_id = var.dataset_id

  # Note: This is a placeholder - actual price update requires external API call
  # In production, use Cloud Function to fetch from yfinance and insert
  params = {
    query = <<-EOT
      -- Placeholder: Check for missing price data
      -- Actual price fetching should be done via Cloud Function + yfinance
      SELECT
          CURRENT_DATE() AS check_date
          , (SELECT MAX(date) FROM `${var.project_id}.${var.dataset_id}.daily_prices`) AS latest_price_date
    EOT
  }

  service_account_name = var.enable_scheduled_queries ? google_service_account.scheduled_query_sa[0].email : null

  depends_on = [
    google_project_service.bigquery_datatransfer,
    google_project_iam_member.scheduled_query_bq_admin
  ]
}
