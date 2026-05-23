"""
bot/ml/clustering.py — Data Clustering / Segmentation.
"""
from __future__ import annotations

import pandas as pd
from loguru import logger

try:
    from sklearn.cluster import KMeans
    from sklearn.preprocessing import StandardScaler
except ImportError:
    KMeans = None


def cluster_data(df: pd.DataFrame, n_clusters: int = 3) -> pd.DataFrame:
    """
    Given a DataFrame, clusters rows using KMeans on numeric features.
    Appends a `_cluster_id` column.
    """
    if KMeans is None:
        logger.warning("scikit-learn is not installed. Returning original df.")
        return df

    if df.empty or len(df) < n_clusters:
        return df

    numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
    if not numeric_cols:
        logger.warning("No numeric columns found for clustering.")
        return df

    try:
        # Scale the data first
        X = df[numeric_cols].fillna(0)
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        
        # Apply KMeans
        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init="auto")
        clusters = kmeans.fit_predict(X_scaled)
        
        df["_cluster_id"] = clusters
        logger.info(f"Assigned data into {n_clusters} clusters.")
    except Exception as e:
        logger.error(f"Clustering failed: {e}")
        df["_cluster_id"] = -1

    return df
