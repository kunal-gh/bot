"""
bot/ml/anomaly.py — Automated Anomaly Detection.
"""
from __future__ import annotations

import pandas as pd
from loguru import logger

try:
    from sklearn.ensemble import IsolationForest
except ImportError:
    IsolationForest = None


def detect_anomalies(df: pd.DataFrame) -> pd.DataFrame:
    """
    Given a DataFrame, use Isolation Forest to detect anomalies
    on numeric columns. Appends an `_is_anomaly` boolean column.
    """
    if IsolationForest is None:
        logger.warning("scikit-learn is not installed. Returning original df.")
        return df

    if df.empty:
        return df

    numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
    if not numeric_cols:
        logger.warning("No numeric columns found for anomaly detection.")
        return df

    try:
        # Fill NaNs temporarily for Isolation Forest
        X = df[numeric_cols].fillna(0)
        
        # Fit Isolation Forest
        # contamination=0.05 means we assume ~5% of data is anomalous
        model = IsolationForest(contamination=0.05, random_state=42)
        predictions = model.fit_predict(X)
        
        # -1 indicates anomaly, 1 indicates normal
        df["_is_anomaly"] = (predictions == -1)
        
        logger.info(f"Detected {df['_is_anomaly'].sum()} anomalies.")
    except Exception as e:
        logger.error(f"Anomaly detection failed: {e}")
        df["_is_anomaly"] = False

    return df
