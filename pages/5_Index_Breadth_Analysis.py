import streamlit as st
import pandas as pd
import yfinance as yf
import numpy as np

# ───────────────────────────────
# Load symbols & sectors from CSV
# ───────────────────────────────
@st.cache_data
def load_nifty_symbols():
    df = pd.read_csv("HeatmapDetail_Data.csv")
    df.columns = ["Symbol", "Sector", "Price % Chng", "Price Chng", "Index % Chng", "Index Chng"]
    df["Symbol"] = df["Symbol"].str.strip().str.upper()
    df["Sector"] = df["Sector"].str.strip()
    df = df.dropna(subset=["Symbol", "Sector"])
    return df

df_csv = load_nifty_symbols()
nifty_symbols = df_csv["Symbol"].unique().tolist()

# ───────────────────────────────
# Streamlit Setup
# ───────────────────────────────
st.title("📊 NIFTY 50 – Breadth Analysis (using CSV & yFinance)")
st.markdown("This page shows market breadth using your sector-wise CSV + live prices from Yahoo Finance.")

# ───────────────────────────────
# Compute Breadth Metrics
# ───────────────────────────────
st.subheader("🔄 Computing Breadth Metrics...")

ma50_above = ma200_above = advance = decline = 0
valid_count = 0

progress = st.progress(0)
for i, sym in enumerate(nifty_symbols):
    try:
        df = yf.Ticker(sym + ".NS").history(period="250d", interval="1d")
        if len(df) < 200:
            continue

        close = df["Close"].iloc[-1]
        prev_close = df["Close"].iloc[-2]
        ma50 = df["Close"].rolling(50).mean().iloc[-1]
        ma200 = df["Close"].rolling(200).mean().iloc[-1]

        if close > ma50:
            ma50_above += 1
        if close > ma200:
            ma200_above += 1
        if close > prev_close:
            advance += 1
        else:
            decline += 1
        valid_count += 1
    except:
        continue
    progress.progress((i + 1) / len(nifty_symbols))

st.success(f"✅ Fetched data for {valid_count} out of {len(nifty_symbols)} stocks.")

# ───────────────────────────────
# Display Results
# ───────────────────────────────
st.subheader("📈 Breadth Summary")

pct_50 = ma50_above / valid_count * 100 if valid_count else 0
pct_200 = ma200_above / valid_count * 100 if valid_count else 0
a_d_ratio = advance / decline if decline else np.inf

col1, col2, col3 = st.columns(3)
col1.metric("% Above 50-day MA", f"{pct_50:.1f}%")
col2.metric("% Above 200-day MA", f"{pct_200:.1f}%")
col3.metric("Advance/Decline", f"{a_d_ratio:.2f}")

# ───────────────────────────────
# Insights
# ───────────────────────────────
st.subheader("📋 Market Insight")

if pct_50 > 70 and pct_200 > 70:
    st.success("✅ Strong market breadth — most stocks are above both 50 and 200 MAs.")
elif pct_50 < 50:
    st.warning("⚠️ Weak short-term breadth — less than half of stocks above 50-day MA.")

if a_d_ratio > 1.2:
    st.success("📈 More stocks are advancing than declining.")
elif a_d_ratio < 0.8:
    st.warning("📉 More stocks are declining — cautious tone.")
else:
    st.info("↔️ Market is balanced today.")

# ───────────────────────────────
# Final Recommendation
# ───────────────────────────────
st.subheader("📌 Final Recommendation")

if pct_50 > 65 and a_d_ratio > 1:
    st.success("✅ Market supports **buying** — trend looks healthy.")
elif pct_50 < 50 and a_d_ratio < 1:
    st.error("❌ Consider **avoiding** fresh entries — trend is weak.")
else:
    st.info("📊 Stay **neutral** and observe for clarity.")
