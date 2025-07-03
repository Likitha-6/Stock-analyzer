import streamlit as st
import yfinance as yf
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from scipy.signal import argrelextrema
from indicators import compute_rsi  # make sure this function exists

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
price = df["Close"].iloc[-1]

df["EMA_9"] = df["Close"].ewm(span=9, adjust=False).mean()
df["EMA_15"] = df["Close"].ewm(span=15, adjust=False).mean()
df["RSI"] = compute_rsi(df)

# ─────────────────────────────────────
# Find Swing Highs and Lows
# ─────────────────────────────────────
def find_swing_levels(df, window=5):
    swing_highs = []
    swing_lows = []
    for i in range(window, len(df) - window):
        is_high = all(df["High"].iloc[i] > df["High"].iloc[i - j] and df["High"].iloc[i] > df["High"].iloc[i + j] for j in range(1, window + 1))
        is_low = all(df["Low"].iloc[i] < df["Low"].iloc[i - j] and df["Low"].iloc[i] < df["Low"].iloc[i + j] for j in range(1, window + 1))

        if is_high:
            swing_highs.append((df["Date"].iloc[i], df["High"].iloc[i]))
        if is_low:
            swing_lows.append((df["Date"].iloc[i], df["Low"].iloc[i]))

    return swing_highs[-3:], swing_lows[-3:]  # last 3 each


st.subheader(f"📈 {selected_index} – Candlestick Chart with EMA 9, EMA 15")

show_levels = st.checkbox("📏 Show Support & Resistance", value=True)

def get_nearest_support_resistance(df, price):
        df = df.copy()
        df["min"] = df["Close"].iloc[argrelextrema(df["Close"].values, np.less_equal, order=5)[0]]
        df["max"] = df["Close"].iloc[argrelextrema(df["Close"].values, np.greater_equal, order=5)[0]]
        supports = df["min"].dropna()
        resistances = df["max"].dropna()
        nearest_support = supports[supports < price].max() if not supports.empty else None
        nearest_resistance = resistances[resistances > price].min() if not resistances.empty else None
        return nearest_support, nearest_resistance

support, resistance = get_nearest_support_resistance(df, price)
df["EMA_9"] = df["Close"].ewm(span=9, adjust=False).mean()
df["EMA_15"] = df["Close"].ewm(span=15, adjust=False).mean()

fig = go.Figure()
fig.add_trace(go.Candlestick(
    x=df["Date"],
    open=df["Open"],
    high=df["High"],
    low=df["Low"],
    close=df["Close"],
    name=index_name,
    increasing_line_color="green",
    decreasing_line_color="red"
))
fig.add_trace(go.Scatter(x=df["Date"], y=df["EMA_9"], mode="lines", name="EMA 9", line=dict(color="orange")))
fig.add_trace(go.Scatter(x=df["Date"], y=df["EMA_15"], mode="lines", name="EMA 15", line=dict(color="cyan")))

if support:
    fig.add_hline(y=support, line_color="green", line_dash="dot", opacity=0.7, annotation_text=f"Support: {support:.2f}", annotation_position="bottom right")
if resistance:
    fig.add_hline(y=resistance, line_color="red", line_dash="dot", opacity=0.7, annotation_text=f"Resistance: {resistance:.2f}", annotation_position="top right")

fig.update_layout(
    title=f"{index_name} – Nearest Support & Resistance",
    xaxis_title="Date",
    yaxis_title="Price",
    template="plotly_dark",
    xaxis_rangeslider_visible=False,
    dragmode="pan",
    height=600,
    xaxis=dict(showgrid=False),
    yaxis=dict(showgrid=False)
)
st.plotly_chart(fig, use_container_width=True, config={"scrollZoom": True})

st.subheader(f"{index_name} Key Levels")
st.write(f"Current Price: `{price:.2f}`")
if support:
    st.success(f"Nearest Support: `{support:.2f}`")
if resistance:
    st.warning(f"Nearest Resistance: `{resistance:.2f}`")

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
