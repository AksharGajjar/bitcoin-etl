# variables.tf
# Input variables for Bitcoin SOPR Analytics infrastructure

variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "region" {
  description = "GCP region for resources"
  type        = string
  default     = "us-central1"
}

variable "dataset_location" {
  description = "BigQuery dataset location (US, EU, etc.)"
  type        = string
  default     = "US"
}

variable "dataset_id" {
  description = "BigQuery dataset ID"
  type        = string
  default     = "bitcoin_analytics"
}

variable "utxo_start_date" {
  description = "Start date for UTXO index (YYYY-MM-DD)"
  type        = string
  default     = "2019-01-01"
}

variable "dust_threshold" {
  description = "Minimum BTC value to include (ignore dust)"
  type        = number
  default     = 0.0001
}

variable "enable_utxo_index" {
  description = "Whether to create the UTXO index table (⚠️ costs $25-50)"
  type        = bool
  default     = false
}

variable "enable_scheduled_queries" {
  description = "Whether to enable daily scheduled queries for aSOPR pipeline (~$0.05/day)"
  type        = bool
  default     = false
}
