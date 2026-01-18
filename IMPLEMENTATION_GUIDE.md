# Bitcoin SOPR Analytics - Implementation Guide

> **Purpose**: Consolidated architectural decisions and implementation patterns for the Bitcoin SOPR Analytics Dashboard project. This guide preserves context for multi-session development.

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
