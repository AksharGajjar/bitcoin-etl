#!/usr/bin/env python3
"""
Load daily BTC-USD prices from Yahoo Finance into BigQuery.

Fetches historical Bitcoin prices and uploads them to the daily_prices table.
"""

import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
import yfinance as yf
from google.cloud import bigquery
from google.cloud.exceptions import NotFound

# Add parent directory to path to import config
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
import config


def check_existing_data(client: bigquery.Client, table_id: str) -> int:
    """
    Check if table exists and count rows.

    Args:
        client: BigQuery client instance
        table_id: Fully qualified table ID (project.dataset.table)

    Returns:
        Number of rows in table, or 0 if table doesn't exist
    """
    try:
        table = client.get_table(table_id)
        query = f"SELECT COUNT(*) as row_count FROM `{table_id}`"
        result = client.query(query).result()
        row_count = list(result)[0].row_count
        return row_count
    except NotFound:
        return 0


def fetch_btc_prices(start_date: str, end_date: str) -> pd.DataFrame:
    """
    Fetch BTC-USD daily prices from Yahoo Finance.

    Args:
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format

    Returns:
        DataFrame with columns: date, open, high, low, close, volume
    """
    print(f"Fetching BTC-USD prices from {start_date} to {end_date}...")

    btc = yf.Ticker("BTC-USD")
    df = btc.history(start=start_date, end=end_date, interval="1d")

    # Reset index to make Date a column
    df = df.reset_index()

    # Rename columns to match BigQuery schema
    df = df.rename(columns={
        "Date": "date",
        "Open": "open",
        "High": "high",
        "Low": "low",
        "Close": "close",
        "Volume": "volume"
    })

    # Select only needed columns
    df = df[["date", "open", "high", "low", "close", "volume"]]

    # Convert date to date-only (remove time component)
    df["date"] = pd.to_datetime(df["date"]).dt.date

    print(f"Fetched {len(df)} rows")
    return df


def upload_to_bigquery(
    client: bigquery.Client,
    df: pd.DataFrame,
    table_id: str
) -> None:
    """
    Upload DataFrame to BigQuery table.

    Args:
        client: BigQuery client instance
        df: DataFrame to upload
        table_id: Fully qualified table ID (project.dataset.table)
    """
    print(f"Uploading to {table_id}...")

    # Define schema
    schema = [
        bigquery.SchemaField("date", "DATE", mode="REQUIRED"),
        bigquery.SchemaField("open", "FLOAT64", mode="REQUIRED"),
        bigquery.SchemaField("high", "FLOAT64", mode="REQUIRED"),
        bigquery.SchemaField("low", "FLOAT64", mode="REQUIRED"),
        bigquery.SchemaField("close", "FLOAT64", mode="REQUIRED"),
        bigquery.SchemaField("volume", "FLOAT64", mode="REQUIRED"),
    ]

    # Configure load job
    job_config = bigquery.LoadJobConfig(
        schema=schema,
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,  # Overwrite table
    )

    # Upload data
    job = client.load_table_from_dataframe(df, table_id, job_config=job_config)
    job.result()  # Wait for job to complete

    print(f"Upload complete!")


def main() -> None:
    """Main execution function."""
    # Validate configuration
    config.validate_config()

    # Initialize BigQuery client
    client = bigquery.Client(project=config.GCP_PROJECT_ID)

    # Check for existing data
    existing_rows = check_existing_data(client, config.TABLE_DAILY_PRICES)

    if existing_rows > 0:
        print(f"⚠️  Table {config.TABLE_DAILY_PRICES} already contains {existing_rows} rows")
        response = input("Overwrite existing data? (yes/no): ").strip().lower()
        if response not in ["yes", "y"]:
            print("Operation cancelled")
            return

    # Fetch data from yfinance
    start_date = config.UTXO_START_DATE
    end_date = datetime.now().strftime("%Y-%m-%d")

    df = fetch_btc_prices(start_date, end_date)

    if df.empty:
        print("❌ No data fetched from yfinance")
        return

    # Upload to BigQuery
    upload_to_bigquery(client, df, config.TABLE_DAILY_PRICES)

    # Verify upload
    final_count = check_existing_data(client, config.TABLE_DAILY_PRICES)
    print(f"✓ Complete! Table now contains {final_count} rows")


if __name__ == "__main__":
    main()
