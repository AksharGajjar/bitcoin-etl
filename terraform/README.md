# Terraform Infrastructure

This directory contains Terraform configuration for deploying BigQuery infrastructure for the Bitcoin SOPR Analytics project.

## Files

- `provider.tf` - GCP provider configuration
- `variables.tf` - Input variable definitions
- `main.tf` - BigQuery dataset and tables
- `outputs.tf` - Output values after deployment
- `terraform.tfvars.example` - Example configuration (copy to `terraform.tfvars`)

## Quick Start

```bash
# 1. Copy example config
cp terraform.tfvars.example terraform.tfvars

# 2. Edit terraform.tfvars with your GCP project ID
vim terraform.tfvars

# 3. Initialize Terraform
terraform init

# 4. Review the plan
terraform plan

# 5. Deploy infrastructure
terraform apply

# 6. (Optional) Create UTXO index later
# Edit terraform.tfvars: enable_utxo_index = true
# Then: terraform apply
```

## Cost Warning

Setting `enable_utxo_index = true` will create a BigQuery table that scans 1TB+ of the Bitcoin public ledger. This costs approximately **$25-50** in BigQuery processing fees.

Only enable this when you're ready to incur the cost.

## Authentication

Ensure you have GCP credentials configured:

```bash
# Option 1: Application Default Credentials
gcloud auth application-default login

# Option 2: Service Account Key
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/key.json
```

## Outputs

After deployment, Terraform will output:
- Dataset ID
- Table names (fully qualified)
- Next steps for loading data
