import streamlit as st
import yfinance as yf
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from scipy.signal import argrelextrema
from indicators import compute_rsi  # make sure this function exists and returns a "RSI" column

st.set_page_config(page_title=" Index Analysis", layout="wide")

# ─────────────────────────────────────
# Index Selector
# ─────────────────────────────────────
index_options = {
    "NIFTY 50": "^NSEI",
    "SENSEX": "^BSESN",
    "NIFTY Bank": "^NSEBANK",
    "NIFTY IT": "^CNXIT",
    "NIFTY FMCG": "^CNXFMCG",
    "NIFTY Auto": "^CNXAUTO",
    "NIFTY Pharma": "^CNXPHARMA",
}
selected_index = st.selectbox(" Select Index", list(index_options.keys()))
index_symbol = index_options[selected_index]


# ─────────────────────────────────────
# Load Data and Compute Indicators
# ─────────────────────────────────────
df = yf.Ticker(index_symbol).history(period="400d", interval="1d").reset_index()
price = df["Close"].iloc[-1]
# Ensure we have enough data
df["Date"] = pd.to_datetime(df["Date"])
df.set_index("Date", inplace=True)

# Compute previous values
day_ago = df["Close"].iloc[-2] if len(df) >= 2 else np.nan
month_ago = df["Close"].asfreq("D").last("30D").iloc[0] if len(df) >= 30 else np.nan
year_ago = df["Close"].asfreq("D").last("365D").iloc[0] if len(df) >= 250 else np.nan

# Compute percentage changes
day_change = (price - day_ago) / day_ago * 100 if not pd.isna(day_ago) else np.nan
month_change = (price - month_ago) / month_ago * 100 if not pd.isna(month_ago) else np.nan
year_change = (price - year_ago) / year_ago * 100 if not pd.isna(year_ago) else np.nan

df.reset_index(inplace=True)


col1, col2, col3, col4 = st.columns(4)

col1.metric(" Latest Price", f"{price:.2f} ₹")
col2.metric(" 1-Day Change", f"{day_change:+.2f}%", delta_color="inverse")
col3.metric("1-Month Change", f"{month_change:+.2f}%", delta_color="inverse")
col4.metric("1-Year Change", f"{year_change:+.2f}%", delta_color="inverse")


# Compute indicators
df["EMA_9"] = df["Close"].ewm(span=9, adjust=False).mean()
df["EMA_15"] = df["Close"].ewm(span=15, adjust=False).mean()
df["RSI"] = compute_rsi(df)

# ─────────────────────────────────────
# Nearest Support & Resistance
# ─────────────────────────────────────
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

# ─────────────────────────────────────
# Chart Rendering
# ─────────────────────────────────────
st.subheader(f" {selected_index} – Candlestick Chart with EMA 9, EMA 15")

fig = go.Figure()

fig.add_trace(go.Candlestick(
    x=df["Date"],
    open=df["Open"],
    high=df["High"],
    low=df["Low"],
    close=df["Close"],
    increasing_line_color="green",
    decreasing_line_color="#e74c3c",
    name="Price"
))
fig.add_trace(go.Scatter(x=df["Date"], y=df["EMA_9"], mode="lines", name="EMA 9", line=dict(color="orange")))
fig.add_trace(go.Scatter(x=df["Date"], y=df["EMA_15"], mode="lines", name="EMA 15", line=dict(color="cyan")))

if support:
    fig.add_hline(y=support, line_color="green", line_dash="dot", opacity=0.7,
                  annotation_text=f"Support: {support:.2f}", annotation_position="bottom right")
if resistance:
    fig.add_hline(y=resistance, line_color="red", line_dash="dot", opacity=0.7,
                  annotation_text=f"Resistance: {resistance:.2f}", annotation_position="top right")

fig.update_layout(
    title=f"{selected_index} – Nearest Support & Resistance",
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
    st.success(" EMA 15 is sloping upward — trend strengthening.")
else:
    st.warning(" EMA 15 is sloping downward — short-term weakening.")

if latest_rsi > 70:
    st.warning("⚠️ RSI > 70: **Overbought** — potential pullback.")
elif latest_rsi < 30:
    st.success("RSI < 30: **Oversold** — potential rebound opportunity.")
else:
    st.info("⚖️ RSI is in **neutral zone**.")

# ─────────────────────────────────────
# Final Recommendation
# ─────────────────────────────────────
st.markdown("---")
st.subheader(" Final Recommendation")

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
