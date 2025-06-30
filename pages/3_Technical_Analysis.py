import streamlit as st
from streamlit_lightweight_charts import Chart
import yfinance as yf
import pandas as pd

from common.data import load_name_lookup

# ─────────────────────────────────────
# Page config
# ─────────────────────────────────────
st.set_page_config(page_title="📉 Technical Analysis", page_icon="📈", layout="wide")
st.title("📉 Technical Analysis – TradingView-style Chart")

# ─────────────────────────────────────
# Load stock names
# ─────────────────────────────────────
name_df = load_name_lookup()
symbol2name = dict(zip(name_df["Symbol"], name_df["Company Name"]))

# ─────────────────────────────────────
# Symbol search
# ─────────────────────────────────────
query = st.text_input("Search by symbol or company name").strip()
chosen_sym = None

if query:
    mask = (
        name_df["Symbol"].str.contains(query, case=False, na=False) |
        name_df["Company Name"].str.contains(query, case=False, na=False)
    )
    matches = name_df[mask]
    if matches.empty:
        st.warning("No match found.")
    else:
        opts = matches.apply(lambda r: f"{r['Symbol']} – {r['Company Name']}", axis=1)
        chosen = st.selectbox("Select company", opts.tolist())
        chosen_sym = chosen.split(" – ")[0]

if not chosen_sym:
    st.stop()

# ─────────────────────────────────────
# Load and plot chart
# ─────────────────────────────────────
st.markdown("---")
st.subheader(f"🔧 Candlestick Chart – {chosen_sym}")

symbol = chosen_sym.strip().upper()
yf_symbol = f"{symbol}.NS"

try:
    df = yf.download(yf_symbol, period="6mo", interval="1d", auto_adjust=False)

    required_cols = ["Open", "High", "Low", "Close"]
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        raise ValueError(f"Missing expected columns from data: {missing_cols}")

    if df.empty or df[required_cols].isna().all().all():
        st.warning("No price data available or symbol not valid on Yahoo Finance.")
        st.stop()

    df = df.dropna(subset=required_cols).copy()

    # Prepare data for lightweight chart
    candles = []
    for idx, row in df.iterrows():
        try:
            candles.append({
                "time": idx.strftime("%Y-%m-%d"),
                "open": float(row["Open"]),
                "high": float(row["High"]),
                "low": float(row["Low"]),
                "close": float(row["Close"])
            })
        except Exception:
            continue

    if not candles:
        st.warning("No valid candlestick data available to display.")
        st.stop()

    # Render chart with correct candlestick parameter
    chart = Chart()
    chart.set(series=[{"type": "Candlestick", "data": candles}])
    chart.render()

except Exception as e:
    st.error(f"Failed to fetch or display data: {e}")
