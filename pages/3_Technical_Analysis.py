import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(page_title="📉 Technical Analysis", page_icon="📉")
st.title("📉 Technical Analysis")

# User input
symbol = st.text_input("Enter NSE Stock Symbol (e.g., INFY)", "INFY").upper()

# Pull history
df = yf.download(f"{symbol}.NS", period="6mo", interval="1d")
if df.empty:
    st.error("Could not fetch data. Check the symbol.")
    st.stop()

# ─── Indicators ────────────────────────────────────────────────
df["SMA20"] = df["Close"].rolling(20).mean()
df["SMA50"] = df["Close"].rolling(50).mean()
df["EMA20"] = df["Close"].ewm(span=20, adjust=False).mean()

# RSI
delta = df["Close"].diff()
gain = delta.clip(lower=0).rolling(14).mean()
loss = (-delta.clip(upper=0)).rolling(14).mean()
rs = gain / loss
df["RSI"] = 100 - (100 / (1 + rs))

# MACD
exp12 = df["Close"].ewm(span=12, adjust=False).mean()
exp26 = df["Close"].ewm(span=26, adjust=False).mean()
df["MACD"] = exp12 - exp26
df["Signal"] = df["MACD"].ewm(span=9, adjust=False).mean()

# ─── Plotly figure with subplots ───────────────────────────────
fig = make_subplots(
    rows=3, cols=1,
    shared_xaxes=True,
    vertical_spacing=0.02,
    row_heights=[0.5, 0.2, 0.3],
    subplot_titles=("Price & Moving Averages", "RSI", "MACD")
)

# 1️⃣ Candlestick + SMAs/EMA
fig.add_trace(go.Candlestick(
    x=df.index, open=df["Open"], high=df["High"],
    low=df["Low"], close=df["Close"], name="OHLC"
), row=1, col=1)

fig.add_trace(go.Scatter(x=df.index, y=df["SMA20"],
                         mode="lines", name="SMA 20"), row=1, col=1)
fig.add_trace(go.Scatter(x=df.index, y=df["SMA50"],
                         mode="lines", name="SMA 50"), row=1, col=1)
fig.add_trace(go.Scatter(x=df.index, y=df["EMA20"],
                         mode="lines", name="EMA 20"), row=1, col=1)

# 2️⃣ RSI
fig.add_trace(go.Scatter(x=df.index, y=df["RSI"],
                         mode="lines", name="RSI", line_color="purple"), row=2, col=1)
fig.add_hline(y=70, line_dash="dash", line_color="red", row=2, col=1)
fig.add_hline(y=30, line_dash="dash", line_color="green", row=2, col=1)

# 3️⃣ MACD + Signal
fig.add_trace(go.Bar(x=df.index, y=df["MACD"] - df["Signal"],
                     name="MACD Histogram", marker_color="steelblue"), row=3, col=1)
fig.add_trace(go.Scatter(x=df.index, y=df["MACD"],
                         mode="lines", name="MACD", line_color="blue"), row=3, col=1)
fig.add_trace(go.Scatter(x=df.index, y=df["Signal"],
                         mode="lines", name="Signal", line_color="orange"), row=3, col=1)

fig.update_layout(
    height=900, showlegend=True,
    xaxis_rangeslider_visible=False,
    xaxis_title="Date"
)

# ─── Display ───────────────────────────────────────────────────
st.plotly_chart(fig, use_container_width=True)

