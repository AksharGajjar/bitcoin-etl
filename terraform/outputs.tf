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

output "next_steps" {
  description = "Next steps after Terraform deployment"
  value       = <<-EOT
    ✓ BigQuery infrastructure created successfully!

    Next steps:
    1. Load price data: python etl/load_prices.py
    2. (Optional) Create UTXO index: Set enable_utxo_index=true and re-run terraform apply
    3. Run Streamlit dashboard: streamlit run main.py

    Environment variables to set:
    - GCP_PROJECT_ID=${var.project_id}
    - BQ_DATASET=${var.dataset_id}
    - BQ_LOCATION=${var.dataset_location}
  EOT
}
