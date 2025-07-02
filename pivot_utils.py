import yfinance as yf
import pandas as pd

def get_previous_period_ohlc(symbol: str, interval: str) -> dict:
    """Get previous week's or previous month's OHLC depending on the interval."""
    ticker = yf.Ticker(symbol)
    hist = ticker.history(interval="1d", period="2mo")  # longer period for safety
    hist = hist[~hist.index.duplicated()]
    hist.index = hist.index.tz_localize("UTC").tz_convert("Asia/Kolkata")

    if interval in ["5m", "15m", "60m", "240m"]:
        resampled = hist.resample("W").agg({
            "Open": "first",
            "High": "max",
            "Low": "min",
            "Close": "last"
        })
    elif interval == "1d":
        resampled = hist.resample("M").agg({
            "Open": "first",
            "High": "max",
            "Low": "min",
            "Close": "last"
        })
    else:
        return None

    if len(resampled) < 2:
        return None  # not enough data

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
