# pages/3_Technical_Analysis.py
# -------------------------------------------------------------------
# Lightweight Technical-Analysis page (line chart + SMAs)
# -------------------------------------------------------------------
import streamlit as st
import yfinance as yf
import pandas as pd

# ── Page config ────────────────────────────────────────────────────
st.set_page_config(page_title="📈 Technical Analysis", page_icon="📈", layout="wide")
st.title("📈 Technical Analysis – Line chart (Close | SMA20 | SMA50)")

# ── Sidebar controls ───────────────────────────────────────────────
symbol = st.sidebar.text_input("NSE Symbol", "RELIANCE").strip().upper()
period = st.sidebar.selectbox("Period", ["1mo", "3mo", "6mo", "1y", "2y", "5y", "max"], index=2)
interval = st.sidebar.selectbox("Interval", ["1d", "1wk", "1mo"], index=0)

if not symbol:
    st.stop()

# ── Download historical data ───────────────────────────────────────
df = yf.download(f"{symbol}.NS", period=period, interval=interval)

if df.empty:
    st.error("⚠️ No data returned. Check symbol or increase period.")
    st.stop()

# Flatten MultiIndex columns (if present) and drop duplicate labels
if isinstance(df.columns, pd.MultiIndex):
    df.columns = df.columns.get_level_values(-1)
df = df.loc[:, ~df.columns.duplicated()]

# Fallback: use 'Adj Close' if 'Close' missing
if "Close" not in df.columns:
    if "Adj Close" in df.columns:
        df["Close"] = df["Adj Close"]
        st.info("ℹ️ Using 'Adj Close' because 'Close' not provided.")
    else:
        st.error("⚠️ Neither 'Close' nor 'Adj Close' present in data.")
        st.write("Columns returned:", list(df.columns))
        st.stop()

# ── Compute indicators ─────────────────────────────────────────────
df["SMA20"] = df["Close"].rolling(20).mean()
df["SMA50"] = df["Close"].rolling(50).mean()

chart_df = df[["Close", "SMA20", "SMA50"]].dropna()

if chart_df.empty:
    st.error("⚠️ Not enough data to compute SMAs for this period.")
    st.stop()

# ── Render line chart ──────────────────────────────────────────────
st.line_chart(chart_df, use_container_width=True)

# Optional: show data preview
with st.expander("🔍 Raw data preview"):
    st.dataframe(chart_df.tail())
