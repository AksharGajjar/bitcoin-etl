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
        return query_sopr(start_date, end_date, use_sample=True)
    except FileNotFoundError:
        print(f"⚠️  SQL file not found: {sql_path}")
        print("📊 Falling back to sample data")
        return query_sopr(start_date, end_date, use_sample=True)
    except Exception as e:
        print(f"⚠️  Unexpected error: {e}")
        print("📊 Falling back to sample data")
        return query_sopr(start_date, end_date, use_sample=True)


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
        select
            date
            , close as price
        from `{config.TABLE_DAILY_PRICES}`
        where date between @start_date and @end_date
        order by date desc
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
        return query_prices(start_date, end_date, use_sample=True)
    except Exception as e:
        print(f"⚠️  Unexpected error: {e}")
        print("📊 Falling back to sample data")
        return query_prices(start_date, end_date, use_sample=True)
