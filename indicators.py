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


def get_pivot_lines(df: pd.DataFrame, symbol: str, interval: str) -> dict:
    pivot_annotations = []
    pivot_shapes = []

    base = get_previous_period_ohlc(symbol, interval)
    if base:
        pivots = calculate_classic_pivots(base["high"], base["low"], base["close"])

        for label, value in pivots.items():
            pivot_shapes.append({
                "type": "line",
                "x0": df["x_label"].iloc[0],
                "x1": df["x_label"].iloc[-1],
                "y0": value,
                "y1": value,
                "line": dict(color="#999999", width=1, dash="dot"),
                "layer": "below"
            })
            pivot_annotations.append({
                "x": df["x_label"].iloc[-1],
                "y": value,
                "text": label,
                "showarrow": False,
                "xanchor": "left",
                "yanchor": "middle",
                "font": dict(size=10),
                "bgcolor": "#FFFFFF",
                "borderpad": 2
            })
    return {
        "shapes": pivot_shapes,
        "annotations": pivot_annotations,
        "source": base["date"] if base else None
    }
