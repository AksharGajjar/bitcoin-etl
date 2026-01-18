# sample_data.py
# Mock data for testing Streamlit/Plotly without BigQuery costs
# Usage: from docs.sample_data import SAMPLE_SOPR_DATA

import pandas as pd
from datetime import datetime, timedelta

def generate_sample_sopr_data(days: int = 30) -> pd.DataFrame:
    """
    Generate realistic-looking SOPR data for testing.
    SOPR typically oscillates between 0.85 and 1.15.
    """
    import random
    random.seed(42)  # Reproducible
    
    end_date = datetime.now().date()
    dates = [end_date - timedelta(days=i) for i in range(days)]
    
    # Generate SOPR values that oscillate around 1.0
    sopr_values = []
    current = 1.0
    for _ in range(days):
        change = random.uniform(-0.03, 0.03)
        current = max(0.85, min(1.15, current + change))
        sopr_values.append(round(current, 4))
    
    return pd.DataFrame({
        'date': dates,
        'sopr': sopr_values
    })

# Pre-generated sample for quick imports
SAMPLE_SOPR_DATA = generate_sample_sopr_data(30)

# Sample daily prices for testing
SAMPLE_PRICES = pd.DataFrame({
    'date': pd.date_range(end=datetime.now().date(), periods=30).date,
    'price_usd': [42000 + i * 100 for i in range(30)]  # Fake uptrend
})
