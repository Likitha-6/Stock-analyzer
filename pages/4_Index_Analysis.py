import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from indicators import compute_rsi  # Ensure compute_rsi exists in your indicators.py

st.set_page_config(page_title="📈 Index Analysis", layout="wide")

# ─────────────────────────────────────
# Index Selector
# ─────────────────────────────────────
index_options = {
    "NIFTY 50": "^NSEI",
    "Sensex": "^BSESN",
    "NIFTY Bank": "^NSEBANK"
}
selected_index = st.selectbox("📊 Select Index", list(index_options.keys()))
index_symbol = index_options[selected_index]

# ─────────────────────────────────────
# Load Data and Compute Indicators
# ─────────────────────────────────────
df = yf.Ticker(index_symbol).history(period="12mo", interval="1d").reset_index()

df["EMA_9"] = df["Close"].ewm(span=9, adjust=False).mean()
df["EMA_15"] = df["Close"].ewm(span=15, adjust=False).mean()
df["RSI"] = compute_rsi(df)

# ─────────────────────────────────────
# Price Chart (Only EMA 9 and EMA 15)
# ─────────────────────────────────────
st.subheader(f"📈 {selected_index} – Price Chart with EMA 9 & EMA 15")

fig = go.Figure()
fig.add_trace(go.Scatter(x=df["Date"], y=df["Close"], name="Close Price", line=dict(width=2)))
fig.add_trace(go.Scatter(x=df["Date"], y=df["EMA_9"], name="EMA 9", line=dict(dash="solid")))
fig.add_trace(go.Scatter(x=df["Date"], y=df["EMA_15"], name="EMA 15", line=dict(dash="solid")))

fig.update_layout(
    height=500,
    xaxis_title="Date",
    yaxis_title="Price",
    legend_title="Indicators",
    dragmode="pan",
    margin=dict(t=10)
)
st.plotly_chart(fig, use_container_width=True)

# ─────────────────────────────────────
# Technical Insights
# ─────────────────────────────────────
st.subheader("📋 Technical Insights")

latest_ema9 = df["EMA_9"].iloc[-1]
latest_ema15 = df["EMA_15"].iloc[-1]
ema15_5days_ago = df["EMA_15"].iloc[-5]
latest_rsi = df["RSI"].iloc[-1]

if latest_ema9 > latest_ema15:
    st.success("✅ Short-term momentum is **bullish** (EMA 9 > EMA 15).")
else:
    st.error("❌ Short-term momentum is **bearish** (EMA 9 < EMA 15).")

if latest_ema15 > ema15_5days_ago:
    st.success("📈 EMA 15 is sloping upward — trend strengthening.")
else:
    st.warning("📉 EMA 15 is sloping downward — short-term weakening.")

if latest_rsi > 70:
    st.warning("⚠️ RSI > 70: **Overbought** — potential pullback.")
elif latest_rsi < 30:
    st.success("📉 RSI < 30: **Oversold** — potential rebound opportunity.")
else:
    st.info("⚖️ RSI is in **neutral zone**.")

# ─────────────────────────────────────
# Final Recommendation
# ─────────────────────────────────────
st.markdown("---")
st.subheader("📌 Final Recommendation")

buy_signal = latest_ema9 > latest_ema15 and latest_rsi < 30 and latest_ema15 < ema15_5days_ago
wait_signal = latest_ema9 > latest_ema15 and 30 <= latest_rsi <= 60
avoid_signal = latest_ema9 < latest_ema15 and latest_ema15 < ema15_5days_ago

if buy_signal:
    st.success("✅ **Buy**: Oversold condition and bullish crossover. Potential short-term reversal.")
elif wait_signal:
    st.info("⚖️ **Hold / Wait**: Momentum improving, but no clear breakout yet.")
elif avoid_signal:
    st.error("❌ **Avoid**: Bearish alignment and weakening trend. Stay cautious.")
else:
    st.warning("ℹ️ No strong signal. Continue to monitor index behavior.")
