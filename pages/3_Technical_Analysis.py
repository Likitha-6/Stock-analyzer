# pages/3_Technical_Analysis.py
import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(page_title="📈 Technical Analysis", layout="wide")
st.title("📈 Technical Analysis – Line chart (Close | SMA20 | SMA50)")

# ── sidebar inputs ──────────────────────────────────────────────
symbol  = st.sidebar.text_input("NSE Symbol", "RELIANCE").strip().upper()
period  = st.sidebar.selectbox("Period",   ["3mo","6mo","1y","2y","5y","max"], 1)
interval= st.sidebar.selectbox("Interval", ["1d","1wk","1mo"], 0)

if not symbol:
    st.stop()

# ── download data ───────────────────────────────────────────────
raw = yf.download(f"{symbol}.NS", period=period, interval=interval, group_by="ticker")

if raw.empty:
    st.error("⚠️  Yahoo Finance returned no data.")
    st.stop()

# ── handle MultiIndex (field, ticker) ───────────────────────────
if isinstance(raw.columns, pd.MultiIndex):
    try:
        df = raw.xs(f"{symbol}.NS", axis=1, level=1)
    except KeyError:
        st.error("⚠️ Could not locate ticker columns in data frame.")
        st.write("Columns:", raw.columns)
        st.stop()
else:
    df = raw.copy()

# drop duplicate column labels if any
df = df.loc[:, ~df.columns.duplicated()]

# ── sanity-check for Close price ────────────────────────────────
if "Close" not in df.columns:
    if "Adj Close" in df.columns:
        df["Close"] = df["Adj Close"]
        st.info("ℹ️  Using 'Adj Close' because 'Close' not provided.")
    else:
        st.error("⚠️  Neither 'Close' nor 'Adj Close' present.")
        st.write(df.head())
        st.stop()

# ── compute simple moving averages ─────────────────────────────-
df["SMA20"] = df["Close"].rolling(20).mean()
df["SMA50"] = df["Close"].rolling(50).mean()
plot_df     = df[["Close", "SMA20", "SMA50"]].dropna()

if plot_df.empty:
    st.error("⚠️  Not enough data to compute SMAs for this period/interval.")
    st.stop()

# ── interactive line chart ─────────────────────────────────────
st.line_chart(plot_df, use_container_width=True)

with st.expander("🔍  Raw data preview"):
    st.dataframe(plot_df.tail())
