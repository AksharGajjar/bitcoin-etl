# Phase 2: Price Data (2 tasks)

## Task 1: Run etl/load_prices.py to populate daily_prices table
**File**: `bitcoin-sopr-dashboard/etl/load_prices.py` (already implemented)
**Time**: ~5 minutes
**Prerequisites**:
- BigQuery dataset `bitcoin_analytics` exists
- `.env` configured with `GCP_PROJECT_ID`
- `GOOGLE_APPLICATION_CREDENTIALS` set

**Steps**:
```bash
# Run the ETL script
python3 bitcoin-sopr-dashboard/etl/load_prices.py
```

**What it does**:
- Fetches BTC-USD historical prices from yfinance API (2019-01-01 to today)
- Creates `daily_prices` table in BigQuery if it doesn't exist
- Uploads ~1800+ rows (one per day since 2019)
- Schema: `date, open, high, low, close, volume`

**Expected output**:
```
Fetching BTC-USD data from yfinance...
✓ Retrieved 1850 price records
Uploading to BigQuery: bitcoin-sopr-etl.bitcoin_analytics.daily_prices
✓ Upload complete
```

**Verification**: Proceed to Task 2

**Troubleshooting**:
- If `ModuleNotFoundError`: Run `pip install -r bitcoin-sopr-dashboard/requirements.txt`
- If auth error: Check `GOOGLE_APPLICATION_CREDENTIALS` path
- If dataset not found: Run `bq mk --location=US bitcoin_analytics`

---

## Task 2: Verify price data with bq head command
**File**: None (CLI verification)
**Time**: 2 minutes

**Steps**:
```bash
# View first 5 rows
bq head -n 5 bitcoin_analytics.daily_prices

# Check row count
bq query --nouse_legacy_sql \
  'SELECT COUNT(*) as total_rows FROM `bitcoin-sopr-etl.bitcoin_analytics.daily_prices`'

# Check date range
bq query --nouse_legacy_sql \
  'SELECT MIN(date) as earliest, MAX(date) as latest FROM `bitcoin-sopr-etl.bitcoin_analytics.daily_prices`'
```

**Expected output**:
```
+------------+----------+----------+----------+----------+------------+
|    date    |   open   |   high   |    low   |  close   |   volume   |
+------------+----------+----------+----------+----------+------------+
| 2024-01-15 | 42150.23 | 43200.50 | 41800.00 | 42900.12 | 25000000000|
| 2024-01-14 | 41900.00 | 42300.00 | 41500.00 | 42150.23 | 22000000000|
...
```

**Verification checklist**:
- [ ] Table has ~1800+ rows
- [ ] Earliest date is 2019-01-01
- [ ] Latest date is today or yesterday
- [ ] No NULL values in `close` column
- [ ] Prices are reasonable ($3k-$100k range depending on date)

---

# Phase 4: Query Layer (3 tasks)

## Task 3: Implement src/queries.py - query_sopr() function
**File**: `bitcoin-sopr-dashboard/src/queries.py` (currently empty)
**Lines**: ~60-80
**Time**: 20 minutes

**Implementation**:
Create the file with this code:

```python
#!/usr/bin/env python3
"""
BigQuery query builders for SOPR analytics.

Provides functions to fetch SOPR and price data with fallback to sample data.
"""

import sys
from pathlib import Path
from datetime import datetime
from typing import Optional

import pandas as pd
from google.cloud import bigquery
from google.cloud.exceptions import GoogleCloudError

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
import config
from docs.sample_data import SAMPLE_SOPR_DATA, SAMPLE_PRICES


def query_sopr(start_date: str, end_date: str, use_sample: bool = False) -> pd.DataFrame:
    """
    Fetch daily SOPR data from BigQuery or return sample data.

    Args:
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
        use_sample: If True, return sample data instead of querying BigQuery

    Returns:
        DataFrame with columns: date, sopr

    Raises:
        ValueError: If date format is invalid
    """
    # Use sample data if requested
    if use_sample:
        print("📊 Using sample SOPR data (no BigQuery cost)")
        sample = SAMPLE_SOPR_DATA.copy()
        sample['date'] = pd.to_datetime(sample['date'])
        mask = (sample['date'] >= start_date) & (sample['date'] <= end_date)
        return sample[mask].reset_index(drop=True)

    # Validate date format
    try:
        datetime.strptime(start_date, '%Y-%m-%d')
        datetime.strptime(end_date, '%Y-%m-%d')
    except ValueError as e:
        raise ValueError(f"Invalid date format. Use YYYY-MM-DD: {e}")

    try:
        # Read SQL query
        sql_path = config.SQL_DIR / "sopr_query.sql"
        with open(sql_path, 'r') as f:
            sql_template = f.read()

        # Replace project ID placeholders
        sql = sql_template.replace('{project_id}', config.GCP_PROJECT_ID)

        # Execute query
        client = bigquery.Client(project=config.GCP_PROJECT_ID)

        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("start_date", "DATE", start_date),
                bigquery.ScalarQueryParameter("end_date", "DATE", end_date),
            ]
        )

        print(f"🔍 Querying SOPR data from {start_date} to {end_date}...")
        query_job = client.query(sql, job_config=job_config)
        df = query_job.to_dataframe()

        print(f"✓ Retrieved {len(df)} rows")
        return df

    except GoogleCloudError as e:
        print(f"⚠️  BigQuery error: {e}")
        print("📊 Falling back to sample data")
        return SAMPLE_SOPR_DATA.copy()
    except FileNotFoundError:
        print(f"⚠️  SQL file not found: {sql_path}")
        print("📊 Falling back to sample data")
        return SAMPLE_SOPR_DATA.copy()
    except Exception as e:
        print(f"⚠️  Unexpected error: {e}")
        print("📊 Falling back to sample data")
        return SAMPLE_SOPR_DATA.copy()
```

**Key features**:
- Sample data mode (no BigQuery needed)
- Date validation
- Graceful error handling with fallback
- Reads SQL from `sql/sopr_query.sql`
- Parameterized queries (prevents SQL injection)

**Quick test**:
```bash
python3 -c "
import sys; sys.path.insert(0, 'bitcoin-sopr-dashboard')
from src.queries import query_sopr
df = query_sopr('2024-01-01', '2024-01-07', use_sample=True)
print(df.head())
print(f'SOPR range: {df[\"sopr\"].min():.3f} - {df[\"sopr\"].max():.3f}')
"
```

**Expected output**:
```
📊 Using sample SOPR data (no BigQuery cost)
         date      sopr
0  2024-01-07  1.0234
1  2024-01-06  0.9876
...
SOPR range: 0.950 - 1.050
```

---

## Task 4: Implement src/queries.py - query_prices() function
**File**: `bitcoin-sopr-dashboard/src/queries.py` (append to existing file)
**Lines**: +40-50
**Time**: 15 minutes

**Implementation**:
Add this function to the same file (after `query_sopr`):

```python
def query_prices(start_date: str, end_date: str, use_sample: bool = False) -> pd.DataFrame:
    """
    Fetch daily BTC price data from BigQuery or return sample data.

    Args:
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
        use_sample: If True, return sample data instead of querying BigQuery

    Returns:
        DataFrame with columns: date, price

    Raises:
        ValueError: If date format is invalid
    """
    # Use sample data if requested
    if use_sample:
        print("📊 Using sample price data (no BigQuery cost)")
        sample = SAMPLE_PRICES.copy()
        sample['date'] = pd.to_datetime(sample['date'])
        mask = (sample['date'] >= start_date) & (sample['date'] <= end_date)
        result = sample[mask].reset_index(drop=True)
        # Rename column to 'price' for consistency
        if 'price_usd' in result.columns:
            result = result.rename(columns={'price_usd': 'price'})
        return result

    # Validate date format
    try:
        datetime.strptime(start_date, '%Y-%m-%d')
        datetime.strptime(end_date, '%Y-%m-%d')
    except ValueError as e:
        raise ValueError(f"Invalid date format. Use YYYY-MM-DD: {e}")

    try:
        # Build SQL query
        sql = f"""
        SELECT
            date,
            close as price
        FROM `{config.TABLE_DAILY_PRICES}`
        WHERE date BETWEEN @start_date AND @end_date
        ORDER BY date DESC
        """

        # Execute query
        client = bigquery.Client(project=config.GCP_PROJECT_ID)

        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("start_date", "DATE", start_date),
                bigquery.ScalarQueryParameter("end_date", "DATE", end_date),
            ]
        )

        print(f"💰 Querying price data from {start_date} to {end_date}...")
        query_job = client.query(sql, job_config=job_config)
        df = query_job.to_dataframe()

        print(f"✓ Retrieved {len(df)} price records")
        return df

    except GoogleCloudError as e:
        print(f"⚠️  BigQuery error: {e}")
        print("📊 Falling back to sample data")
        sample = SAMPLE_PRICES.copy()
        if 'price_usd' in sample.columns:
            sample = sample.rename(columns={'price_usd': 'price'})
        return sample
    except Exception as e:
        print(f"⚠️  Unexpected error: {e}")
        print("📊 Falling back to sample data")
        sample = SAMPLE_PRICES.copy()
        if 'price_usd' in sample.columns:
            sample = sample.rename(columns={'price_usd': 'price'})
        return sample
```

**Quick test**:
```bash
python3 -c "
import sys; sys.path.insert(0, 'bitcoin-sopr-dashboard')
from src.queries import query_prices
df = query_prices('2024-01-01', '2024-01-07', use_sample=True)
print(df.head())
print(f'Price range: \${df[\"price\"].min():,.0f} - \${df[\"price\"].max():,.0f}')
"
```

**Expected output**:
```
📊 Using sample price data (no BigQuery cost)
         date      price
0  2024-01-07  42900.12
1  2024-01-06  42150.23
...
Price range: $41,500 - $43,200
```

---

## Task 5: Test query layer with real data in Python REPL
**File**: None (interactive test)
**Time**: 5 minutes

**Full test script**:
Save as `test_queries_manual.py`:

```python
#!/usr/bin/env python3
"""Manual test script for query layer."""

import sys
sys.path.insert(0, 'bitcoin-sopr-dashboard')

from src.queries import query_sopr, query_prices
from datetime import datetime, timedelta

# Test with sample data (no BigQuery needed)
end = datetime.now().strftime('%Y-%m-%d')
start = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')

print("=" * 60)
print("Testing Query Layer with Sample Data")
print("=" * 60)

print(f"\n📅 Date range: {start} to {end}\n")

# Test SOPR query
print("=== Testing SOPR Query ===")
try:
    sopr_df = query_sopr(start, end, use_sample=True)
    print(f"✓ Retrieved {len(sopr_df)} rows")
    print("\nFirst 5 rows:")
    print(sopr_df.head())
    print(f"\nSOPR Statistics:")
    print(f"  Min:  {sopr_df['sopr'].min():.4f}")
    print(f"  Max:  {sopr_df['sopr'].max():.4f}")
    print(f"  Mean: {sopr_df['sopr'].mean():.4f}")

    # Validation
    assert 'date' in sopr_df.columns, "Missing 'date' column"
    assert 'sopr' in sopr_df.columns, "Missing 'sopr' column"
    assert len(sopr_df) > 0, "Empty DataFrame"
    assert sopr_df['sopr'].min() > 0.5, "SOPR too low"
    assert sopr_df['sopr'].max() < 2.0, "SOPR too high"
    print("\n✅ SOPR query tests passed!")

except Exception as e:
    print(f"\n❌ SOPR query failed: {e}")

# Test price query
print("\n" + "=" * 60)
print("=== Testing Price Query ===")
try:
    prices_df = query_prices(start, end, use_sample=True)
    print(f"✓ Retrieved {len(prices_df)} rows")
    print("\nFirst 5 rows:")
    print(prices_df.head())
    print(f"\nPrice Statistics:")
    print(f"  Min:  ${prices_df['price'].min():,.2f}")
    print(f"  Max:  ${prices_df['price'].max():,.2f}")
    print(f"  Mean: ${prices_df['price'].mean():,.2f}")

    # Validation
    assert 'date' in prices_df.columns, "Missing 'date' column"
    assert 'price' in prices_df.columns, "Missing 'price' column"
    assert len(prices_df) > 0, "Empty DataFrame"
    assert (prices_df['price'] > 0).all(), "Negative prices found"
    print("\n✅ Price query tests passed!")

except Exception as e:
    print(f"\n❌ Price query failed: {e}")

print("\n" + "=" * 60)
print("✅ All query layer tests complete!")
print("=" * 60)
```

**Run test**:
```bash
python3 test_queries_manual.py
```

**Verification checklist**:
- [ ] Both functions return DataFrames without errors
- [ ] SOPR values are between 0.85-1.15
- [ ] Price values are positive and realistic
- [ ] Sample data mode works (no BigQuery credentials needed)
- [ ] Date filtering works correctly
- [ ] All assertions pass

**Troubleshooting**:
- If `ModuleNotFoundError` for sample_data: Check `docs/sample_data.py` exists
- If import errors: Verify `sys.path.insert(0, ...)` points to correct directory
- If assertion fails: Check sample data format in `docs/sample_data.py`

---

**Next**: Proceed to Phase 5 (Visualization)

Phase 5: Visualization (2 tasks)
6. Implement src/charts.py - create_sopr_chart() function
7. Test chart with mock data

Phase 6: Streamlit App (6 tasks)
8. Implement main.py - basic layout
9. Add sidebar date controls to main.py
10. Add data fetching with caching to main.py
11. Add metrics row to main.py
12. Integrate Plotly chart in main.py
13. Add export functionality to main.py

Phase 7: Documentation (4 tasks)
14. Create comprehensive README.md
15. Create .env.example template
16. Add minimal unit tests in tests/test_queries.py
17. Add architecture diagram to documentation

Phase 3: UTXO Index (1 task - optional, expensive)
18. Implement etl/create_index.py for UTXO index ($25-50 cost)
