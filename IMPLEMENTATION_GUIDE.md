# Bitcoin SOPR Analytics - Implementation Guide

> **Purpose**: Consolidated architectural decisions and implementation patterns for the Bitcoin SOPR Analytics Dashboard project. This guide preserves context for multi-session development.

---

## Table of Contents

1. [Architectural Decisions](#architectural-decisions-2026-01-17)
2. [Infrastructure Management with Terraform](#infrastructure-management-with-terraform)
3. [Code Patterns & Standards](#code-patterns--standards)
4. [File Structure & Responsibilities](#file-structure--responsibilities)
5. [Critical Implementation Notes](#critical-implementation-notes)
6. [Testing Checklist](#testing-checklist)
7. [Common Commands Reference](#common-commands-reference)
8. [Next Steps](#next-steps-execution-order)

---

## Architectural Decisions (2026-01-17)

### Error Handling Strategy
**Decision**: Graceful degradation with fallback to cached/sample data

**Implementation**:
- All BigQuery query functions accept `use_sample: bool = False` parameter
- Catch `google.cloud.exceptions.GoogleCloudError`
- On error: log warning, return sample data from `docs/sample_data.py`
- Display user-friendly message: "Using sample data due to BigQuery error"

**Rationale**: Better UX for demos and when BigQuery quota is exhausted. Users can still interact with the dashboard.

---

### Testing Strategy
**Decision**: Minimal testing - validate query builders with mock data only

**Implementation**:
- Unit tests in `tests/test_queries.py` use `docs/sample_data.py`
- Test query builders with `use_sample=True` mode
- No BigQuery integration tests (avoids cost/quota usage)
- Manual verification through Streamlit UI for end-to-end testing

**Test Cases**:
- Query functions return correct DataFrame structure
- SOPR values are reasonable (0.5-2.0 range)
- Sample data mode works without BigQuery connection
- Export functionality produces valid CSV/JSON

**Rationale**: Portfolio/learning project doesn't need production-grade test coverage. Manual testing is acceptable.

---

### Query Scope
**Decision**: Keep it simple - just daily SOPR calculation

**Implementation**:
- Use `sql/sopr_query.sql` as-is (no modifications)
- Return only: `date`, `sopr` columns
- No moving averages, no volume metrics, no complex aggregations

**Rationale**: Core SOPR metric is sufficient for learning objectives. Additional metrics add complexity without educational value.

---

### UI Structure
**Decision**: Single-page layout with all features

**Layout**:
```
┌─────────────────────────────────────────────────┐
│ Sidebar                │ Main Area              │
│ ├─ Date Range Picker   │ ├─ Metrics Row         │
│ ├─ Refresh Button      │ │  ├─ Current SOPR     │
│ ├─ Use Sample Data     │ │  ├─ Period Average   │
│ ├─ Export (CSV/JSON)   │ │  └─ Current BTC Price│
│                        │ ├─ SOPR Chart (Plotly) │
│                        │ └─ Raw Data (Expander) │
└─────────────────────────────────────────────────┘
```

**Rationale**: Simple, everything visible at once, easy to navigate. Multi-page/tabs add unnecessary complexity.

---

### UTXO Index Execution
**Decision**: Manual dry-run first, then interactive confirmation

**Implementation in `etl/create_index.py`**:
1. `estimate_cost()` function runs BigQuery dry-run
2. Calculate cost: `bytes_scanned / (1024^4) * 5.0` USD
3. Display estimate to user
4. Prompt: "Estimated cost: $X. Proceed? (yes/no)"
5. Only execute if user types "yes"

**Safety Features**:
- Show cost before execution
- Require explicit confirmation
- Print BigQuery job ID for tracking
- Verify table after creation

**Rationale**: $25-50 is significant cost. User must consciously approve spending.

---

### Default Date Range
**Decision**: Last 30 days (uses `config.DEFAULT_LOOKBACK_DAYS`)

**Implementation**:
```python
default_start = datetime.date.today() - datetime.timedelta(days=config.DEFAULT_LOOKBACK_DAYS)
default_end = datetime.date.today()
```

**Query Cost**: ~$0.10 per 30-day query (acceptable for regular use)

**Rationale**: Shows recent trends, low cost, aligns with project constant.

---

### Export Functionality
**Decision**: Both CSV and JSON export formats

**Implementation in `main.py`**:
```python
# CSV export
csv = sopr_df.to_csv(index=False)
st.sidebar.download_button(
    label="📥 Download CSV",
    data=csv,
    file_name=f"sopr_{start_str}_{end_str}.csv",
    mime="text/csv"
)

# JSON export
json = sopr_df.to_json(orient='records', date_format='iso')
st.sidebar.download_button(
    label="📥 Download JSON",
    data=json,
    file_name=f"sopr_{start_str}_{end_str}.json",
    mime="application/json"
)
```

**Rationale**: CSV for spreadsheets, JSON for APIs. Minimal code, nice portfolio feature.

---

## Infrastructure Management with Terraform

### Why Terraform?

**Decision**: Use Infrastructure as Code (IaC) with Terraform for all GCP resource management.

**Benefits**:
- **Reproducibility**: Same infrastructure every time, no manual console clicks
- **Version Control**: Infrastructure changes tracked in git
- **State Management**: Know what's deployed vs what's planned
- **Cost Safety**: Review changes before applying (especially UTXO index)
- **Team Collaboration**: Share infrastructure definitions across sessions
- **Auditability**: See full history of infrastructure changes

**Rationale**: Manual GCP Console operations are error-prone and not repeatable. Terraform ensures consistency and allows infrastructure changes to be reviewed before applying.

---

### Terraform Configuration Structure

```
terraform/
├── provider.tf              # GCP provider configuration
├── variables.tf             # Input variables (project_id, dataset, etc.)
├── main.tf                  # BigQuery dataset and tables
├── outputs.tf               # Useful outputs after deployment
├── terraform.tfvars.example # Template for configuration
├── terraform.tfvars         # Actual config (gitignored)
└── README.md                # Terraform-specific docs
```

---

### Quick Start Guide

#### 1. Configure Terraform

```bash
cd terraform

# Copy example configuration
cp terraform.tfvars.example terraform.tfvars

# Edit with your GCP project ID
vim terraform.tfvars
```

**terraform.tfvars:**
```hcl
project_id = "your-gcp-project-id"  # ← REQUIRED: Your GCP project

# Optional overrides (defaults are sensible)
# region           = "us-central1"
# dataset_location = "US"
# dataset_id       = "bitcoin_analytics"

# ⚠️ COST WARNING: Keep this false until ready ($25-50 cost)
enable_utxo_index = false
```

#### 2. Initialize Terraform

```bash
# Download provider plugins and initialize backend
terraform init
```

Expected output:
```
Terraform has been successfully initialized!
```

#### 3. Review the Plan

```bash
# See what Terraform will create (dry run)
terraform plan
```

Expected resources:
- `google_bigquery_dataset.bitcoin_analytics` - Dataset container
- `google_bigquery_table.daily_prices` - Price data table
- (Optional) `google_bigquery_table.utxo_index` - UTXO index (if enabled)

#### 4. Deploy Infrastructure

```bash
# Apply the configuration
terraform apply

# Review the plan, type 'yes' to confirm
```

Output shows:
```
Apply complete! Resources: 2 added, 0 changed, 0 destroyed.

Outputs:

dataset_id = "bitcoin_analytics"
daily_prices_table = "your-project.bitcoin_analytics.daily_prices"
next_steps = "..."
```

#### 5. (Later) Enable UTXO Index

**⚠️ WARNING**: This step costs ~$25-50 in BigQuery processing.

```bash
# Edit terraform.tfvars
vim terraform.tfvars
# Change: enable_utxo_index = true

# Review what will be added
terraform plan

# Apply the change
terraform apply
```

---

### Terraform Variables Reference

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `project_id` | string | **REQUIRED** | GCP project ID |
| `region` | string | `us-central1` | GCP region |
| `dataset_location` | string | `US` | BigQuery dataset location |
| `dataset_id` | string | `bitcoin_analytics` | BigQuery dataset name |
| `utxo_start_date` | string | `2019-01-01` | Start date for UTXO index |
| `dust_threshold` | number | `0.0001` | Min BTC value to include |
| `enable_utxo_index` | bool | `false` | Create UTXO index (costs $25-50) |

---

### Terraform Best Practices

**DO:**
- ✓ Keep `terraform.tfvars` out of git (already in .gitignore)
- ✓ Run `terraform plan` before `apply`
- ✓ Use `terraform fmt` to format configuration files
- ✓ Review state with `terraform show`
- ✓ Comment variable overrides in terraform.tfvars

**DON'T:**
- ✗ Don't manually modify resources in GCP Console (defeats IaC purpose)
- ✗ Don't commit `terraform.tfstate` to git (contains sensitive data)
- ✗ Don't commit `terraform.tfvars` to git (contains project IDs)
- ✗ Don't enable `enable_utxo_index` without budget approval
- ✗ Don't run `terraform destroy` in production without backup

---

### Terraform Commands Cheat Sheet

```bash
# Initialize (run once, or after adding providers)
terraform init

# Format code
terraform fmt

# Validate configuration
terraform validate

# Preview changes (dry run)
terraform plan

# Apply changes
terraform apply

# Apply without confirmation prompt
terraform apply -auto-approve

# Show current state
terraform show

# List resources
terraform state list

# Get specific output value
terraform output dataset_id

# Destroy all infrastructure (⚠️ DESTRUCTIVE)
terraform destroy
```

---

### Cost Control with Terraform

**UTXO Index Conditional Creation**:
```hcl
resource "google_bigquery_table" "utxo_index" {
  count = var.enable_utxo_index ? 1 : 0
  # ... table configuration ...
}
```

**How it works**:
- `enable_utxo_index = false` → 0 instances created (no cost)
- `enable_utxo_index = true` → 1 instance created (triggers ~$25-50 cost)
- Change is visible in `terraform plan` before applying

**Workflow**:
1. Initial deployment: `enable_utxo_index = false` (creates dataset + daily_prices only)
2. Load price data: `python etl/load_prices.py`
3. Test queries with sample data
4. When ready: Set `enable_utxo_index = true`, run `terraform plan`
5. Review cost impact in plan output
6. Apply: `terraform apply`

---

### Terraform State Management

**Local State** (default):
- State file: `terraform/terraform.tfstate`
- Stored locally (gitignored)
- Contains resource IDs, metadata, sensitive data
- **Backup**: Run `cp terraform.tfstate terraform.tfstate.backup` before major changes

**Remote State** (optional, for teams):
```hcl
# Add to provider.tf for GCS backend
terraform {
  backend "gcs" {
    bucket = "your-project-terraform-state"
    prefix = "bitcoin-sopr"
  }
}
```

---

### Common Terraform Issues & Solutions

**Issue**: "Error creating Dataset: googleapi: Error 409: Already Exists"
```bash
# Import existing resource
terraform import google_bigquery_dataset.bitcoin_analytics PROJECT_ID:bitcoin_analytics
```

**Issue**: "Error locking state"
```bash
# Remove stale lock (if you're sure no other process is running)
terraform force-unlock LOCK_ID
```

**Issue**: "Access Denied: User does not have permission"
```bash
# Grant yourself BigQuery Admin role
gcloud projects add-iam-policy-binding PROJECT_ID \
  --member="user:YOUR_EMAIL" \
  --role="roles/bigquery.admin"

# Or use service account
gcloud auth application-default login
```

**Issue**: Changes not detected after manual GCP Console edits
```bash
# Refresh state from actual infrastructure
terraform refresh

# Or re-import the resource
terraform import RESOURCE_TYPE.RESOURCE_NAME RESOURCE_ID
```

---

### Terraform Workflow Integration

**With Git**:
```bash
# Create feature branch for infrastructure changes
git checkout -b akshar/add-utxo-index

# Make Terraform changes
vim terraform/main.tf

# Format and validate
terraform fmt
terraform validate

# Preview changes
terraform plan

# Apply
terraform apply

# Commit infrastructure code (NOT state files)
git add terraform/*.tf
git commit -m "add: UTXO index table configuration"
git push origin akshar/add-utxo-index

# Create PR
gh pr create --fill
```

**With Phase Workflow**:
- Phase 0: Manual GCP setup (project, APIs)
- **Phase 1: Terraform deployment** (dataset + tables)
- Phase 2: Load price data (ETL)
- Phase 3: Create UTXO index (enable in Terraform)
- Phases 4-7: Application development

---

### Terraform vs Manual Alternatives

| Task | Manual Approach | Terraform Approach |
|------|----------------|-------------------|
| Create dataset | `bq mk bitcoin_analytics` | `terraform apply` |
| Create table | `bq mk --table` + schema JSON | Resource definition in `main.tf` |
| Update schema | `bq update` or recreate | Edit `main.tf`, run `terraform apply` |
| Delete resources | `bq rm` (risky, no confirmation) | `terraform destroy` (shows plan first) |
| Audit changes | No history | Git history of `.tf` files |
| Replicate setup | Manual steps, error-prone | `terraform apply` (identical) |

**Verdict**: Terraform wins for repeatability, safety, and collaboration.

---

## Code Patterns & Standards

### Python Function Signature Pattern
```python
from typing import Optional
import pandas as pd

def query_sopr(
    start_date: str,
    end_date: str,
    use_sample: bool = False
) -> pd.DataFrame:
    """
    Fetch SOPR data from BigQuery or sample data.

    Args:
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
        use_sample: If True, return sample data instead of querying BigQuery

    Returns:
        DataFrame with columns: date (DATE), sopr (FLOAT64)

    Raises:
        ValueError: If date format is invalid
    """
    if use_sample:
        from docs.sample_data import SAMPLE_SOPR_DATA
        return SAMPLE_SOPR_DATA

    # BigQuery logic with error handling
    try:
        # ... query execution ...
    except google.cloud.exceptions.GoogleCloudError as e:
        print(f"⚠️  BigQuery error: {e}. Using sample data as fallback.")
        return query_sopr(start_date, end_date, use_sample=True)
```

**Key Elements**:
- Type hints on all parameters and return
- Google-style docstring
- `use_sample` parameter for testing
- Error handling with fallback to sample data
- Emoji feedback (⚠️, ❌, ✓)

---

### Streamlit Caching Pattern
```python
@st.cache_data(ttl=config.CACHE_TTL_SECONDS)
def fetch_sopr_data(start: str, end: str, use_sample: bool) -> pd.DataFrame:
    """Cached SOPR data fetch."""
    with st.spinner("Fetching SOPR data from BigQuery..."):
        return query_sopr(start, end, use_sample)
```

**Key Elements**:
- Cache decorator with TTL from config (3600 seconds = 1 hour)
- Spinner for user feedback during long operations
- Wrapper around actual query function

---

### SQL File Reading Pattern
```python
from pathlib import Path
import config

def read_sql(filename: str) -> str:
    """Read SQL file from config.SQL_DIR."""
    sql_path = config.SQL_DIR / filename
    return sql_path.read_text()

# Usage
sopr_sql = read_sql("sopr_query.sql")
```

**Key Elements**:
- Use `pathlib.Path` (not `os.path`)
- Read from `config.SQL_DIR` constant
- Centralized SQL file management

---

### BigQuery Parameterized Query Pattern
```python
from google.cloud import bigquery
from datetime import datetime

client = bigquery.Client(project=config.GCP_PROJECT_ID)

job_config = bigquery.QueryJobConfig(
    query_parameters=[
        bigquery.ScalarQueryParameter("start_date", "DATE", start_date),
        bigquery.ScalarQueryParameter("end_date", "DATE", end_date),
    ]
)

query_job = client.query(sql, job_config=job_config)
df = query_job.to_dataframe()
```

**Key Elements**:
- Always parameterize dates (never string interpolation)
- Use `ScalarQueryParameter` for type safety
- Convert result directly to pandas DataFrame

---

## File Structure & Responsibilities

```
bitcoin-etl/
├── config.py                    # SINGLE SOURCE OF TRUTH for all settings
│   ├── GCP_PROJECT_ID, BQ_DATASET, BQ_LOCATION (env-driven)
│   ├── TABLE_DAILY_PRICES, TABLE_UTXO_INDEX (fully qualified)
│   ├── DEFAULT_LOOKBACK_DAYS, CACHE_TTL_SECONDS
│   └── SOPR_THRESHOLD, SOPR_GREED_LABEL, SOPR_FEAR_LABEL
│
├── sql/                         # BigQuery SQL queries
│   ├── sopr_query.sql          # SOPR calculation (uses @start_date, @end_date)
│   └── utxo_index.sql          # UTXO index creation (expensive ~$25-50)
│
├── docs/
│   ├── sample_data.py          # Mock data for testing (SAMPLE_SOPR_DATA, SAMPLE_PRICES)
│   └── schemas.yaml            # BigQuery table schemas (documentation)
│
└── bitcoin-sopr-dashboard/
    ├── etl/
    │   ├── load_prices.py      # yfinance → BigQuery daily_prices table
    │   └── create_index.py     # Execute utxo_index.sql with cost confirmation
    │
    ├── src/
    │   ├── queries.py          # query_sopr(), query_prices() with sample fallback
    │   └── charts.py           # create_sopr_chart() using Plotly
    │
    ├── tests/
    │   └── test_queries.py     # Unit tests using sample data
    │
    └── main.py                 # Streamlit app entry point
```

---

## Critical Implementation Notes

### 1. Schema Alignment

**Issue**: `schemas.yaml` shows `daily_prices` with only `date` and `price_usd`, but `load_prices.py` creates table with `date, open, high, low, close, volume`.

**Resolution**: Update `schemas.yaml` OR simplify `load_prices.py` to only store `date` and `close` (as `price_usd`).

**Recommendation**: Keep full OHLCV data in case future features need it. Update schema documentation to match.

---

### 2. SOPR Query Validation

**Expected SOPR Range**: 0.9 - 1.1 (typically)
- Values consistently >1.2: Likely calculation error (check join logic)
- Values consistently <0.8: Likely calculation error (check join logic)
- Values == NULL: Missing price data for some dates

**Validation Query** (run after first execution):
```sql
SELECT
  MIN(sopr) as min_sopr,
  MAX(sopr) as max_sopr,
  AVG(sopr) as avg_sopr,
  COUNT(*) as row_count
FROM (
  -- paste sopr_query.sql here with actual dates
)
```

---

### 3. Cost Optimization

**Partition Filtering** (CRITICAL):
- ALWAYS filter `utxo_index` by `block_date` partition
- Example: `WHERE block_date BETWEEN @start_date AND @end_date`
- Without filter: full table scan = $$$$

**Clustering Benefit**:
- `utxo_index` clustered by `tx_hash`
- Joining on `tx_hash` is fast and cheap
- Don't scan by other columns

**Cache Strategy**:
- Streamlit cache TTL = 1 hour (`config.CACHE_TTL_SECONDS`)
- Changing date range invalidates cache (new parameters)
- "Refresh" button clears cache via `st.cache_data.clear()`

---

### 4. Sample Data Usage

**When to Use**:
- During UI development (avoid BigQuery costs)
- When UTXO index not yet created
- When BigQuery quota exhausted
- For screenshots/demos

**Implementation**:
```python
from docs.sample_data import SAMPLE_SOPR_DATA, SAMPLE_PRICES

# Always available, no BigQuery connection needed
df = SAMPLE_SOPR_DATA  # 30 days of realistic SOPR values (0.85-1.15)
```

**Limitations**:
- Fixed 30-day range
- Not real Bitcoin data (generated with seed=42)
- Doesn't reflect current market conditions

---

## Testing Checklist

### Unit Tests (`pytest tests/ -v`)
- [ ] `test_query_sopr_with_sample_data()` - Returns DataFrame
- [ ] `test_query_sopr_has_required_columns()` - Has 'date', 'sopr'
- [ ] `test_sopr_values_reasonable()` - Values in 0.5-2.0 range
- [ ] `test_query_prices_with_sample_data()` - Returns DataFrame
- [ ] `test_query_prices_has_required_columns()` - Has 'date', 'price'

### Manual Streamlit Tests
- [ ] App loads with sample data (no BigQuery connection)
- [ ] Date range picker changes data
- [ ] Metrics row shows current SOPR and BTC price
- [ ] Chart renders with threshold line at y=1.0
- [ ] Colors change above/below threshold (green/red)
- [ ] Export CSV downloads valid file
- [ ] Export JSON downloads valid file
- [ ] Raw data expander shows table

### BigQuery Integration Tests (if UTXO index exists)
- [ ] Query completes in <10 seconds for 30-day range
- [ ] SOPR values are 0.9-1.1 range (realistic)
- [ ] No NULL values in results
- [ ] Date range matches input parameters

### Error Handling Tests
- [ ] Invalid credentials → falls back to sample data
- [ ] Missing table → falls back to sample data
- [ ] Invalid date range → shows error message
- [ ] Empty results → shows "No data" message

---

## Common Commands Reference

```bash
# Environment setup
pip install -r bitcoin-sopr-dashboard/requirements.txt
export GOOGLE_APPLICATION_CREDENTIALS=~/.gcp/your-key.json
export GCP_PROJECT_ID=your-project-id

# BigQuery dataset creation
bq mk --location=US bitcoin_analytics

# ETL scripts
python bitcoin-sopr-dashboard/etl/load_prices.py          # Load BTC prices (~2 min)
python bitcoin-sopr-dashboard/etl/create_index.py         # Create UTXO index (~10 min, $25-50)

# Verification
bq ls bitcoin_analytics                                   # List tables
bq head -n 5 bitcoin_analytics.daily_prices              # Sample price data
bq show bitcoin_analytics.utxo_index                     # Table schema
bq query --dry_run --use_legacy_sql=false "$(cat sql/utxo_index.sql)"  # Cost estimate

# Development
streamlit run bitcoin-sopr-dashboard/main.py              # Run app (localhost:8501)
pytest bitcoin-sopr-dashboard/tests/ -v                   # Run tests
ruff check . && ruff format .                             # Code quality

# Debugging
python3 -i                                                # Interactive REPL
>>> import sys; sys.path.insert(0, 'bitcoin-sopr-dashboard')
>>> from src.queries import query_sopr
>>> df = query_sopr('2024-01-01', '2024-01-07', use_sample=True)
>>> print(df)
```

---

## Next Steps (Execution Order)

### Phase A: Core Data Layer (Priority 1)
1. Verify price data load (Task 2.2-2.3)
2. Implement `src/queries.py` with sample fallback (Task 4.1-4.2)
3. Test queries with sample data (Task 4.3 with `use_sample=True`)

### Phase B: Visualization (Priority 2)
4. Implement `src/charts.py` (Task 5.1)
5. Test chart with sample data (Task 5.2)

### Phase C: Streamlit UI (Priority 3)
6. Build main.py incrementally (Tasks 6.1-6.6)
7. Test end-to-end with sample data
8. Add export functionality

### Phase D: Optional UTXO Index (Priority 4, Cost-Dependent)
9. Implement `etl/create_index.py` (Task 3.1)
10. Dry-run cost estimate (Task 3.2)
11. Get budget approval
12. Execute index creation (Task 3.3-3.4)
13. Test queries with real BigQuery data

### Phase E: Polish (Priority 5)
14. Write README.md (Task 7.1)
15. Create .env.example (Task 7.2)
16. Add unit tests (Task 7.3)
17. Document architecture (Task 7.4)
18. Capture screenshot (Task 7.5)

**Total Time Estimate**: 2-3 weeks (excluding UTXO index wait time)

---

## Risk Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| BigQuery cost overrun | High ($$$) | Always use partition filters, dry-run first, sample data mode |
| UTXO index creation fails | Medium | Implement retry logic, save intermediate results, verify schema first |
| yfinance API rate limit | Low | Caching, exponential backoff, fallback to manual CSV upload |
| Streamlit Cloud deployment quota | Low | Keep queries under 10s, use caching, document self-hosting |
| Schema mismatch between docs and code | Medium | Single source of truth in code, auto-generate docs from actual tables |

---

## Future Enhancements (Out of Scope)

- Real-time updates (WebSocket to BigQuery Streaming)
- Email/SMS alerts when SOPR crosses thresholds
- Multi-asset support (ETH, altcoins)
- Mobile-responsive UI
- User authentication (multi-user dashboards)
- Backtesting framework (historical strategy simulation)
- Machine learning predictions (SOPR trend forecasting)

---

**Last Updated**: 2026-01-17
**Status**: Implementation phase - core features defined, ready for execution
**Budget**: $25-50 one-time (UTXO index), ~$0.10/month (queries)
