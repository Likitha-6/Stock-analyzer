import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from indicators import compute_rsi  # Ensure compute_rsi is in your indicators.py

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
df["EMA_20"] = df["Close"].ewm(span=20, adjust=False).mean()
df["SMA_50"] = df["Close"].rolling(window=50).mean()
df["SMA_200"] = df["Close"].rolling(window=200).mean()
df["RSI"] = compute_rsi(df)

# ─────────────────────────────────────
# Price Chart
# ─────────────────────────────────────
st.subheader(f"📈 {selected_index} – Price Chart with EMAs & SMAs")

fig = go.Figure()
fig.add_trace(go.Scatter(x=df["Date"], y=df["Close"], name="Close Price", line=dict(width=2)))
fig.add_trace(go.Scatter(x=df["Date"], y=df["EMA_9"], name="EMA 9", line=dict(dash="dot")))
fig.add_trace(go.Scatter(x=df["Date"], y=df["EMA_15"], name="EMA 15", line=dict(dash="dot")))
fig.add_trace(go.Scatter(x=df["Date"], y=df["EMA_20"], name="EMA 20", line=dict(dash="dash")))
fig.add_trace(go.Scatter(x=df["Date"], y=df["SMA_50"], name="SMA 50", line=dict(dash="solid")))
fig.add_trace(go.Scatter(x=df["Date"], y=df["SMA_200"], name="SMA 200", line=dict(dash="solid")))

fig.update_layout(
    height=500,
    xaxis_title="Date",
    yaxis_title="Price",
    legend_title="Indicators",
    margin=dict(t=10)
)
st.plotly_chart(fig, use_container_width=True)

# ─────────────────────────────────────
# Technical Insights
# ─────────────────────────────────────
st.subheader("📋 Technical Insights")

latest_price = df["Close"].iloc[-1]
latest_50 = df["SMA_50"].iloc[-1]
latest_200 = df["SMA_200"].iloc[-1]
latest_ema20 = df["EMA_20"].iloc[-1]
ema20_5days_ago = df["EMA_20"].iloc[-5]
latest_rsi = df["RSI"].iloc[-1]

if latest_50 > latest_200:
    st.success("✅ Medium-term trend is **bullish** (50 > 200 SMA).")
else:
    st.error("❌ Medium-term trend is **bearish** (50 < 200 SMA).")

if latest_ema20 > ema20_5days_ago:
    st.success("📈 Short-term momentum is **strengthening** (20 EMA sloping upward).")
else:
    st.warning("📉 Short-term momentum is **weakening** (20 EMA sloping downward).")

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

buy_signal = latest_50 > latest_200 and latest_rsi < 30 and latest_ema20 < ema20_5days_ago
wait_signal = latest_50 > latest_200 and 30 <= latest_rsi <= 60
avoid_signal = latest_50 < latest_200 and latest_ema20 < ema20_5days_ago

if buy_signal:
    st.success("✅ **Buy**: Oversold condition with bullish trend. Potential reversal setup.")
elif wait_signal:
    st.info("⚖️ **Hold / Wait**: Bullish trend, but momentum not strong yet.")
elif avoid_signal:
    st.error("❌ **Avoid**: Weak trend and short-term pressure. Stay cautious.")
else:
    st.warning("ℹ️ No strong signal. Continue to monitor index behavior.")
