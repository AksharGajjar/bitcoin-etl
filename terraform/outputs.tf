# outputs.tf
# Useful outputs for Bitcoin SOPR Analytics infrastructure

output "dataset_id" {
  description = "The ID of the BigQuery dataset"
  value       = google_bigquery_dataset.bitcoin_analytics.dataset_id
}

output "dataset_location" {
  description = "The location of the BigQuery dataset"
  value       = google_bigquery_dataset.bitcoin_analytics.location
}

output "daily_prices_table" {
  description = "Fully qualified daily_prices table name"
  value       = "${var.project_id}.${google_bigquery_dataset.bitcoin_analytics.dataset_id}.${google_bigquery_table.daily_prices.table_id}"
}

output "utxo_index_table" {
  description = "Fully qualified utxo_index table name (if enabled)"
  value       = var.enable_utxo_index ? "${var.project_id}.${google_bigquery_dataset.bitcoin_analytics.dataset_id}.${google_bigquery_table.utxo_index[0].table_id}" : "not_created"
}

output "scheduled_queries_enabled" {
  description = "Whether scheduled queries are enabled"
  value       = var.enable_scheduled_queries
}

output "scheduled_query_service_account" {
  description = "Service account for scheduled queries"
  value       = var.enable_scheduled_queries ? google_service_account.scheduled_query_sa[0].email : "not_created"
}

output "next_steps" {
  description = "Next steps after Terraform deployment"
  value       = <<-EOT
    ✓ BigQuery infrastructure created successfully!

    Next steps:
    1. Load price data: python etl/load_prices.py
    2. Create cached tables: Run sql/create_daily_spends.sql and sql/create_daily_asopr.sql
    3. Enable scheduled queries: Set enable_scheduled_queries=true and re-run terraform apply
    4. Run Streamlit dashboard: streamlit run main.py

    Environment variables to set:
    - GCP_PROJECT_ID=${var.project_id}
    - BQ_DATASET=${var.dataset_id}
    - BQ_LOCATION=${var.dataset_location}

    Daily pipeline schedule (when enabled):
    - 05:00 UTC: Check/update daily_prices
    - 06:00 UTC: Update daily_spends (~$0.03)
    - 06:30 UTC: Update daily_asopr (~$0.02)
  EOT
}
