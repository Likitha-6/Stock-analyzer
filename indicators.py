import pandas as pd
from pivot_utils import get_previous_period_ohlc, calculate_classic_pivots

def apply_sma(df: pd.DataFrame, lengths: list) -> pd.DataFrame:
    for sma_len in lengths:
        df[f"SMA_{sma_len}"] = df["Close"].rolling(window=sma_len).mean()
    return df

def apply_ema(df: pd.DataFrame, lengths: list) -> pd.DataFrame:
    for ema_len in lengths:
        df[f"EMA_{ema_len}"] = df["Close"].ewm(span=ema_len, adjust=False).mean()
    return df

def apply_smma(df: pd.DataFrame, lengths: list) -> pd.DataFrame:
    for length in lengths:
        df[f"SMMA_{length}"] = calculate_smma(df["Close"], length)
    return df

def calculate_smma(series: pd.Series, length: int) -> pd.Series:
    """Calculate Smoothed Moving Average (SMMA) using TradingView's logic."""
    smma = pd.Series(index=series.index, dtype=float)
    smma.iloc[length - 1] = series.iloc[:length].mean()  # Initialize with SMA
    for i in range(length, len(series)):
        smma.iloc[i] = (smma.iloc[i - 1] * (length - 1) + series.iloc[i]) / length
    return smma

def compute_sma(df: pd.DataFrame, length: int) -> pd.Series:
    """Compute a single SMA series without modifying original DataFrame."""
    return df["Close"].rolling(window=length).mean()

def detect_cross_signals(df: pd.DataFrame) -> str:
    if "SMA_50" not in df.columns or "SMA_200" not in df.columns:
        return ""

    latest_50 = df["SMA_50"].iloc[-1]
    latest_200 = df["SMA_200"].iloc[-1]
    prev_50 = df["SMA_50"].iloc[-2]
    prev_200 = df["SMA_200"].iloc[-2]

    if pd.notna(latest_50) and pd.notna(latest_200):
        if latest_50 > latest_200:
            if prev_50 < prev_200:
                return "✅ Short-term momentum (50-day) is overtaking long-term momentum (200-day). Now might be a good time to buy."
            else:
                return "✅ Bullish continuation: 50-day average remains above 200-day. Trend looks strong."
        elif latest_50 < latest_200:
            if prev_50 > prev_200:
                return "❌ Short-term momentum (50-day) is dropping below long-term trend (200-day). Caution is advised."
            else:
                return "❌ Bearish continuation: 50-day average remains below 200-day. Downtrend may persist."

    return "No crossover signals detected at this time."

def get_pivot_lines(df: pd.DataFrame, symbol: str, interval: str):
    pivot_shapes = []
    pivot_annotations = []
    base = get_previous_period_ohlc(symbol, interval)

    if base:
        pivots = calculate_classic_pivots(base["high"], base["low"], base["close"])

        for label, value in pivots.items():
            pivot_shapes.append({
                "shape": {
                    "type": "line",
                    "x0": df["x_label"].iloc[0],
                    "x1": df["x_label"].iloc[-1],
                    "y0": value,
                    "y1": value,
                    "line": dict(color="#999999", width=1, dash="dot"),
                    "layer": "below"
                },
                "annotation": {
                    "x": df["x_label"].iloc[-1],
                    "y": value,
                    "text": label,
                    "showarrow": False,
                    "xanchor": "left",
                    "yanchor": "middle",
                    "font": dict(size=10),
                    "bgcolor": "#FFFFFF",
                    "borderpad": 2
                }
            })

    return pivot_shapes, f"\U0001F4CF Pivot Source: {base['date']} – Classic" if base else ""
