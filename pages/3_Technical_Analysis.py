import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

st.set_page_config(page_title="📉 Technical Analysis", page_icon="📉")

st.title("📉 Technical Analysis")

# Input
symbol = st.text_input("Enter NSE Stock Symbol (e.g., INFY)", "INFY")

# Fetch historical data
df = yf.download(f"{symbol}.NS", period="6mo", interval="1d")
if df.empty:
    st.error("Could not fetch data. Please check the symbol.")
    st.stop()

# SMA and EMA
df["SMA20"] = df["Close"].rolling(20).mean()
df["SMA50"] = df["Close"].rolling(50).mean()
df["EMA20"] = df["Close"].ewm(span=20, adjust=False).mean()

# RSI
delta = df["Close"].diff()
gain = (delta.where(delta > 0, 0)).rolling(14).mean()
loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
rs = gain / loss
df["RSI"] = 100 - (100 / (1 + rs))

# MACD
exp1 = df["Close"].ewm(span=12, adjust=False).mean()
exp2 = df["Close"].ewm(span=26, adjust=False).mean()
df["MACD"] = exp1 - exp2
df["Signal"] = df["MACD"].ewm(span=9, adjust=False).mean()

# Candlestick and SMAs
st.subheader("📊 Price with SMA/EMA")
fig, ax = plt.subplots(figsize=(12, 5))
df["Close"].plot(ax=ax, label="Close")
df["SMA20"].plot(ax=ax, label="SMA20")
df["SMA50"].plot(ax=ax, label="SMA50")
df["EMA20"].plot(ax=ax, label="EMA20")
ax.legend()
st.pyplot(fig)

# RSI Plot
st.subheader("📈 Relative Strength Index (RSI)")
fig, ax = plt.subplots()
df["RSI"].plot(ax=ax, color='purple')
ax.axhline(70, color='red', linestyle='--')
ax.axhline(30, color='green', linestyle='--')
st.pyplot(fig)

# MACD Plot
st.subheader("📉 MACD")
fig, ax = plt.subplots()
df["MACD"].plot(ax=ax, label="MACD", color='blue')
df["Signal"].plot(ax=ax, label="Signal", color='orange')
ax.legend()
st.pyplot(fig)
