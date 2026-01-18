# config.py
# Centralized configuration - Claude: reference this for all project constants

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Paths
PROJECT_ROOT = Path(__file__).parent
SQL_DIR = PROJECT_ROOT / "sql"

# GCP Settings
GCP_PROJECT_ID = os.environ.get("GCP_PROJECT_ID")
BQ_DATASET = os.environ.get("BQ_DATASET", "bitcoin_analytics")
BQ_LOCATION = os.environ.get("BQ_LOCATION", "US")

# Table names (fully qualified)
TABLE_DAILY_PRICES = f"{GCP_PROJECT_ID}.{BQ_DATASET}.daily_prices"
TABLE_UTXO_INDEX = f"{GCP_PROJECT_ID}.{BQ_DATASET}.utxo_index"

# App defaults
DEFAULT_LOOKBACK_DAYS = 30
CACHE_TTL_SECONDS = 3600  # 1 hour

# SOPR thresholds
SOPR_THRESHOLD = 1.0  # Break-even line
SOPR_GREED_LABEL = "Greed 🟢"
SOPR_FEAR_LABEL = "Fear 🔴"

# Data constraints
UTXO_START_DATE = "2019-01-01"  # Don't query before this
DUST_THRESHOLD = 0.0001  # BTC - ignore outputs smaller than this


def validate_config() -> bool:
    """Check that required environment variables are set."""
    if not GCP_PROJECT_ID:
        raise ValueError("GCP_PROJECT_ID environment variable not set")
    return True
