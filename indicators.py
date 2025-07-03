import pandas as pd
from pivot_utils import get_previous_period_ohlc, calculate_classic_pivots

def apply_sma(df: pd.DataFrame, lengths: list) -> pd.DataFrame:
    for sma_len in lengths:
        col_name = f"SMA_{sma_len}"
        if col_name in df.columns and df[col_name].notna().sum() > 10:  # only if sufficient data
            fig.add_trace(go.Scatter(
                x=df["x_label"],
                y=df[col_name],
                mode="lines",
                line=dict(width=1.5),
                name=f"SMA ({sma_len})"
            ))

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
def detect_crossovers(df, short_col="EMA_20", long_col="EMA_50"):
    """
    Detect crossover points between short-term and long-term EMAs or SMAs.

    Returns:
        dict with 'buy' and 'sell' indices
    """
    signals = {"buy": [], "sell": []}

    if short_col not in df.columns or long_col not in df.columns:
        return signals  # Gracefully skip if columns are missing

    short = df[short_col]
    long = df[long_col]

    # Generate crossover signals
    for i in range(1, len(df)):
        if pd.notna(short[i]) and pd.notna(long[i]):
            if short[i - 1] < long[i - 1] and short[i] > long[i]:
                signals["buy"].append(i)
            elif short[i - 1] > long[i - 1] and short[i] < long[i]:
                signals["sell"].append(i)

    return signals


def detect_cross_signals(df: pd.DataFrame) -> str:
    if "SMA_50" not in df.columns or "SMA_200" not in df.columns:
        return ""

    latest_price = df["Close"].iloc[-1]
    latest_50 = df["SMA_50"].iloc[-1]
    latest_200 = df["SMA_200"].iloc[-1]
    prev_50 = df["SMA_50"].iloc[-2]
    prev_200 = df["SMA_200"].iloc[-2]

    if pd.notna(latest_50) and pd.notna(latest_200):
        # Golden cross
        if latest_50 > latest_200:
            if prev_50 < prev_200:
                return "✅ Golden cross: Short-term momentum (50-day) is overtaking long-term momentum (200-day). This may be a bullish signal."
            elif latest_price < latest_50:
                return "📉 Price is below the 50-day average, but the overall trend remains bullish (50 > 200). This could be a healthy pullback within an uptrend."
            else:
                return "✅ Bullish continuation: 50-day average remains above 200-day. Trend looks strong."

        # Death cross
        elif latest_50 < latest_200:
            if prev_50 > prev_200:
                return "❌ Death cross: Short-term momentum (50-day) just dropped below long-term trend (200-day). Caution is advised."
            elif latest_price > latest_50:
                return "📈 Price is above the 50-day average, but the overall trend remains bearish (50 < 200). Potential short-term strength in a weak market."
            else:
                return "❌ Bearish continuation: 50-day average remains below 200-day. Downtrend may persist."

    return "⚠️ No crossover signals detected at this time."

def compute_rsi(df: pd.DataFrame, period: int = 14) -> pd.Series:
    delta = df["Close"].diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)

    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def get_pivot_lines(df: pd.DataFrame, symbol: str, interval: str):
    pivot_shapes = []
    pivot_annotations = []

    # Only use previous day OHLC for intraday intervals
    if interval in ["5m", "15m", "60m", "240m"]:
        base = get_previous_period_ohlc(symbol)
    else:
        return [], "⏳ Pivot levels not supported for this interval."

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

        return pivot_shapes, f"📍 Pivot Source: {base['date']} (Prev Day OHLC)"
    else:
        return [], "⚠️ Could not fetch pivot source data."
