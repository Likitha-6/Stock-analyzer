import yfinance as yf
import pandas as pd

def get_previous_period_ohlc(symbol: str) -> dict:
    """Get previous day's OHLC data for intraday pivot calculation."""
    ticker = yf.Ticker(symbol)
    df = ticker.history(period="5d", interval="1d")  # Fetch last 5 daily candles

    if df.empty or len(df) < 2:
        return {}

    # Get the second last row (i.e., yesterday)
    prev_day = df.iloc[-2]
    return {
        "high": prev_day["High"],
        "low": prev_day["Low"],
        "close": prev_day["Close"],
        "date": prev_day.name.strftime("%Y-%m-%d")
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
