"""
bot/ml/forecasting.py — Time-Series Forecasting.
"""
from __future__ import annotations

import pandas as pd
from loguru import logger

try:
    from statsmodels.tsa.holtwinters import SimpleExpSmoothing
except ImportError:
    SimpleExpSmoothing = None


def forecast_time_series(df: pd.DataFrame, periods: int = 30) -> pd.DataFrame:
    """
    Given a DataFrame with a date/time column and numeric columns,
    generates a forecast for the specified number of periods.
    """
    if SimpleExpSmoothing is None:
        logger.warning("statsmodels is not installed. Returning original df.")
        return df

    if df.empty:
        return df

    # Find the date column
    date_cols = df.select_dtypes(include=["datetime", "datetimetz"]).columns.tolist()
    if not date_cols:
        # Try to infer date from object columns
        for col in df.columns:
            try:
                df[col] = pd.to_datetime(df[col])
                date_cols.append(col)
                break
            except (ValueError, TypeError):
                continue

    if not date_cols:
        logger.warning("No date column found for forecasting.")
        return df

    date_col = date_cols[0]
    df = df.sort_values(by=date_col).set_index(date_col)
    
    numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
    if not numeric_cols:
        logger.warning("No numeric columns found for forecasting.")
        return df.reset_index()

    # Resample to daily (assuming daily data for simplicity, forward fill)
    df = df.resample('D').sum().fillna(0)

    forecast_results = {}
    last_date = df.index[-1]
    future_dates = pd.date_range(start=last_date + pd.Timedelta(days=1), periods=periods, freq='D')
    
    forecast_results[date_col] = future_dates

    for col in numeric_cols:
        try:
            # Simple Exponential Smoothing
            model = SimpleExpSmoothing(df[col], initialization_method="estimated")
            fit_model = model.fit()
            forecast = fit_model.forecast(periods)
            forecast_results[col] = forecast.values
        except Exception as e:
            logger.error(f"Forecasting failed for {col}: {e}")
            forecast_results[col] = [0] * periods

    forecast_df = pd.DataFrame(forecast_results)
    
    # Identify the forecast rows
    forecast_df["_is_forecast"] = True
    
    original_df = df.reset_index()
    original_df["_is_forecast"] = False
    
    # Combine historical and forecast data
    combined = pd.concat([original_df, forecast_df], ignore_index=True)
    return combined
