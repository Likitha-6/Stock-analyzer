import yfinance as yf
import pandas as pd

def get_pivot_source_period(interval: str) -> str:
    """Return period type to fetch pivot base data."""
    if interval in ["5m", "15m", "60m", "240m"]:
        return "1wk"  # Weekly OHLC for intraday
    elif interval == "1d":
        return "1mo"  # Monthly OHLC for daily candles
    else:
        return "1d"

def get_previous_period_ohlc(symbol: str, interval: str) -> dict:
    """Return OHLC for previous week or month based on interval."""
    pivot_source_period = get_pivot_source_period(interval)
    hist = yf.Ticker(symbol).history(interval="1d", period=pivot_source_period)

    if interval in ["5m", "15m", "60m", "240m"]:
        hist = hist.copy()
        hist["Week"] = hist.index.to_series().dt.isocalendar().week
        last_week = hist["Week"].max() - 1
        df_period = hist[hist["Week"] == last_week]
    elif interval == "1d":
        hist = hist.copy()
        hist["Month"] = hist.index.to_series().dt.month
        last_month = hist["Month"].max() - 1
        df_period = hist[hist["Month"] == last_month]
    else:
        df_period = hist.tail(1)

    if df_period.empty:
        return None

    return {
        "high": df_period["High"].max(),
        "low": df_period["Low"].min(),
        "close": df_period["Close"].iloc[-1],
        "open": df_period["Open"].iloc[0],
        "date": df_period.index[-1].strftime("%d-%b-%Y")
    }

def calculate_classic_pivots(high: float, low: float, close: float) -> dict:
    """Calculate Classic pivot levels."""
    P = (high + low + close) / 3
    return {
        "Pivot": P,
        "R1": 2 * P - low,
        "S1": 2 * P - high,
        "R2": P + (high - low),
        "S2": P - (high - low),
        "R3": high + 2 * (P - low),
        "S3": low - 2 * (high - P),
    }
