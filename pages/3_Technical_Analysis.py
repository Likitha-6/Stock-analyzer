# pages/3_Technical_Analysis.py
import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

st.set_page_config(page_title="📈 Technical Analysis – Lite", layout="wide")
st.title("📈 Technical Analysis (Line-chart version)")

# ── User inputs ───────────────────────────────────────────────
symbol = st.text_input("Enter NSE symbol", "RELIANCE").strip().upper()
period = st.selectbox("Period", ["3mo", "6mo", "1y", "2y", "5y", "max"], index=1)

if not symbol:
    st.stop()

# ── Download data ─────────────────────────────────────────────
df = yf.download(f"{symbol}.NS", period=period, interval="1d")

if df.empty:
    st.error("⚠️ No data returned. Try another symbol or a longer period.")
    st.stop()

# 🔧 Flatten MultiIndex columns & drop duplicates --------------
if isinstance(df.columns, pd.MultiIndex):
    df.columns = df.columns.get_level_values(-1)

df = df.loc[:, ~df.columns.duplicated()]        # drop duplicate col names

# We need at least "Close"
if "Close" not in df.columns and "Adj Close" in df.columns:
    df["Close"] = df["Adj Close"]
    st.error("⚠️ Data has no 'Close' column. Unable to plot line chart.")
    st.table(df.head())                         # show for debugging
    st.stop()

# ── Compute moving averages ──────────────────────────────────
df["SMA20"] = df["Close"].rolling(20).mean()
df["SMA50"] = df["Close"].rolling(50).mean()

# ── Build line-chart friendly DataFrame ----------------------
chart_df = df[["Close", "SMA20", "SMA50"]].dropna()

# ── Display line chart ───────────────────────────────────────
st.line_chart(chart_df, use_container_width=True)

# Optional: show last few rows for quick reference
st.write("Latest values", chart_df.tail())
