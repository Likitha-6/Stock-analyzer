import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from indicators import compute_rsi

# If you want to use nsetools:
# pip install nsetools
from nsetools import Nse

st.set_page_config(page_title="📈 NIFTY 50 Breadth Analysis", layout="wide")

st.title("📈 NIFTY 50 – Breadth & Technical Analysis")

# ────────────────────────────
# 1. Load NIFTY 50 constituents
# ────────────────────────────
nse = Nse()
symbols = nse.get_stocks_in_index("NIFTY 50")  # returns list of tickers
symbols = [sym + ".NS" for sym in symbols]

# ────────────────────────────
# 2. Fetch index price data
# ────────────────────────────
df = yf.Ticker("^NSEI").history(period="12mo", interval="1d").reset_index()
df["EMA_9"] = df["Close"].ewm(span=9, adjust=False).mean()
df["EMA_15"] = df["Close"].ewm(span=15, adjust=False).mean()
df["RSI"] = compute_rsi(df)

# ────────────────────────────
# 3. Breadth Metrics Computation
# ────────────────────────────
with st.spinner("🔄 Fetching breadth data..."):
    ma50_above = ma200_above = advance = decline = 0
    for sym in symbols:
        data = yf.Ticker(sym).history(period="250d", interval="1d")
        if len(data) < 200: continue
        close = data["Close"].iloc[-1]
        if close > data["Close"].rolling(50).mean().iloc[-1]:
            ma50_above += 1
        if close > data["Close"].rolling(200).mean().iloc[-1]:
            ma200_above += 1
        if data["Close"].iloc[-1] > data["Close"].iloc[-2]:
            advance += 1
        else:
            decline += 1

    pct_50 = ma50_above / len(symbols) * 100
    pct_200 = ma200_above / len(symbols) * 100
    a_d_ratio = advance / decline if decline else np.inf

# ────────────────────────────
# 4. Put/Call Ratio using option chain
# ────────────────────────────
opt = yf.Ticker("^NSEI").option_chain()
total_put_oi = opt.puts["openInterest"].sum()
total_call_oi = opt.calls["openInterest"].sum()
pcr = total_put_oi / total_call_oi if total_call_oi else None

# ────────────────────────────
# 5. Display Breadth Metrics
# ────────────────────────────
st.subheader("📊 Market Breadth Metrics")
col1, col2, col3 = st.columns(3)
col1.metric("% > 50-day MA", f"{pct_50:.1f}%")
col2.metric("% > 200-day MA", f"{pct_200:.1f}%")
col3.metric("Advance/Decline Ratio", f"{a_d_ratio:.2f}")

if pcr:
    sentiment = "Bearish contrarian (PCR > 1)" if pcr > 1 else "Neutral/Bullish"
    st.write(f"**Put/Call Ratio (Open Interest)**: {pcr:.2f} — {sentiment}")
else:
    st.info("Put/Call Ratio data not available")

# ────────────────────────────
# 6. Candlestick Chart + EMAs + Support/Resistance
# ────────────────────────────
st.subheader("📈 NIFTY 50 – Candlestick with EMA 9/15")

def find_swing(df, window=5):
    highs, lows = [], []
    for i in range(window, len(df) - window):
        if all(df.High[i] > df.High[i - j] and df.High[i] > df.High[i+j] for j in range(1, window+1)):
            highs.append(df.High[i])
        if all(df.Low[i] < df.Low[i - j] and df.Low[i] < df.Low[i+j] for j in range(1, window+1)):
            lows.append(df.Low[i])
    return highs[-3:], lows[-3:]

show_levels = st.checkbox("📏 Show Support/Resistance Levels", value=True)

fig = go.Figure(go.Candlestick(
    x=df.Date, open=df.Open, high=df.High, low=df.Low, close=df.Close,
    increasing_line_color="#26de81", decreasing_line_color="#eb3b5a"
))
fig.add_trace(go.Scatter(x=df.Date, y=df.EMA_9, mode="lines", name="EMA 9", line=dict(dash="dot")))
fig.add_trace(go.Scatter(x=df.Date, y=df.EMA_15, mode="lines", name="EMA 15", line=dict(dash="dot")))

if show_levels:
    highs, lows = find_swing(df)
    for price in highs:
        fig.add_shape(type="line", x0=df.Date.min(), x1=df.Date.max(), y0=price, y1=price,
                      line=dict(color="red", dash="dash"))
    for price in lows:
        fig.add_shape(type="line", x0=df.Date.min(), x1=df.Date.max(), y0=price, y1=price,
                      line=dict(color="green", dash="dash"))

fig.update_layout(dragmode="pan", xaxis_rangeslider_visible=False, xaxis=dict(showgrid=False),
                  yaxis=dict(showgrid=False), height=550, margin=dict(t=10))
st.plotly_chart(fig, use_container_width=True,
                config={"scrollZoom": True, "displayModeBar": True,
                        "modeBarButtonsToRemove": ["select2d", "lasso2d"], "displaylogo": False})

# ────────────────────────────
# 7. Technical Insights + Recommendation
# ────────────────────────────
st.subheader("📋 Technical Insights & Recommendation")

latest_ema9 = df.EMA_9.iloc[-1]
latest_ema15 = df.EMA_15.iloc[-1]
ema15_5ago = df.EMA_15.iloc[-5]
latest_rsi = df.RSI.iloc[-1]

# Breadth interpretations
if pct_50 > 70 and pct_200 > 70:
    st.success("✅ Strong breadth: Over 70% of stocks are above both 50- and 200-day MAs.")
elif pct_50 < 50:
    st.warning("⚠️ Weak short-term breadth: Less than half of stocks above 50-day MA.")
if a_d_ratio > 1:
    st.success("📈 Advance/Decline > 1: More stocks are advancing than declining.")
else:
    st.warning("📉 Advance/Decline < 1: More stocks are declining — caution.")

if pcr:
    if pcr > 1:
        st.success("🔄 High PCR (>1): Contrarian bullish signal.")
    elif pcr < 0.7:
        st.warning("📉 Low PCR (<0.7): Bullish sentiment—possible short-term caution.")
    else:
        st.info("ℹ️ PCR neutral.")

# EMA & RSI insights
if latest_ema9 > latest_ema15:
    st.success("✅ Short-term momentum bullish (EMA 9 > EMA 15)")
else:
    st.error("❌ Short-term momentum bearish (EMA 9 < EMA 15)")
if latest_ema15 > ema15_5ago:
    st.success("📈 EMA 15 is rising — strengthening trend.")
else:
    st.warning("📉 EMA 15 is falling — weakening trend.")
if latest_rsi > 70:
    st.warning("⚠️ RSI > 70: Overbought — pullback likely.")
elif latest_rsi < 30:
    st.success("📉 RSI < 30: Oversold — rebound possible.")
else:
    st.info("⚖️ RSI is neutral.")

# Final recommendation logic
buy = latest_ema9 > latest_ema15 and latest_rsi < 30 and pct_50 > 50 and pcr and pcr > 1
hold = latest_ema9 > latest_ema15 and pct_50 > 50
avoid = latest_ema9 < latest_ema15 and pct_50 < 50

st.markdown("---")
st.subheader("📌 Final Recommendation")
if buy:
    st.success("✅ **Buy** — Multiple bullish signals aligned.")
elif hold:
    st.info("⚖️ **Hold / Watch** — Market fundamentals OK, but wait for confirmation.")
elif avoid:
    st.error("❌ **Avoid** — Weak breadth and bearish momentum.")
else:
    st.warning("ℹ️ No clear directional signal — observe further.")

