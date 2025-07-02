import yfinance as yf
import pandas as pd

def get_previous_period_ohlc(symbol: str, interval: str) -> dict:
    """Returns OHLC based on standard pivot logic:
    - Intraday intervals: previous day
    - 1D interval: previous week
    """
    # Load historical daily data
    ticker = yf.Ticker(symbol)
    hist = ticker.history(interval="1d", period="2mo")
    hist = hist[~hist.index.duplicated()]

    # Ensure timezone handling
    if hist.index.tz is None:
        hist.index = hist.index.tz_localize("UTC")
    hist.index = hist.index.tz_convert("Asia/Kolkata")

    hist = hist.sort_index()

    if interval in ["5m", "15m", "60m", "240m"]:
        # Use previous DAY’s OHLC
        last_date = hist.index[-1].date()
        prev_day_data = hist[hist.index.date < last_date]
        prev_day = prev_day_data.groupby(prev_day_data.index.date).last().index[-1]

        df_day = hist[hist.index.date == prev_day]
    elif interval == "1d":
        # Use previous WEEK’s OHLC
        hist["Week"] = hist.index.to_period("W-MON")
        last_week = hist["Week"].iloc[-1]
        prev_week = last_week - 1

        df_day = hist[hist["Week"] == prev_week]
    else:
        return None

    if df_day.empty:
        return None

    return {
        "high": df_day["High"].max(),
        "low": df_day["Low"].min(),
        "close": df_day["Close"].iloc[-1],
        "open": df_day["Open"].iloc[0],
        "date": df_day.index[0].strftime("%d-%b-%Y")
    }

    if len(resampled) < 2:
        return None

    prev = resampled.iloc[-2]

    return {
        "high": prev["High"],
        "low": prev["Low"],
        "close": prev["Close"],
        "open": prev["Open"],
        "date": prev.name.strftime("%d-%b-%Y")
    }

def calculate_classic_pivots(high: float, low: float, close: float) -> dict:
    """Classic pivot formula (TradingView-style)."""
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
