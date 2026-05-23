"""
bot/ml/__init__.py — Machine Learning functionality.
"""
from bot.ml.forecasting import forecast_time_series
from bot.ml.anomaly import detect_anomalies
from bot.ml.clustering import cluster_data

__all__ = ["forecast_time_series", "detect_anomalies", "cluster_data"]
