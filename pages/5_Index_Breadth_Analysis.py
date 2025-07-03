import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
from scipy.signal import argrelextrema
import plotly.graph_objects as go

# Load NIFTY 50 symbols + sectors
@st.cache_data
def load_symbols():
    df = pd.read_csv("HeatmapDetail_Data.csv")
    df.columns = ["Symbol", "Sector", "Price % Chng", "Price Chng", "Index % Chng", "Index Chng"]
    df["Symbol"] = df["Symbol"].str.strip().str.upper()
    df = df.dropna(subset=["Symbol"])
    return df

df_csv = load_symbols()
nifty_symbols = df_csv["Symbol"].unique().tolist()

st.title("📊 NIFTY 50 Breadth & Support/Resistance")



# Compute Breadth Metrics
ma50_above = ma200_above = advance = decline = 0
valid_count = 0
with st.spinner("Fetching stock data..."):
    for sym in nifty_symbols:
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

pct_50 = ma50_above / valid_count * 100 if valid_count else 0
pct_200 = ma200_above / valid_count * 100 if valid_count else 0
a_d_ratio = advance / decline if decline else np.inf

col1, col2, col3 = st.columns(3)
col1.metric("% Above 50-day MA", f"{pct_50:.1f}%")
col2.metric("% Above 200-day MA", f"{pct_200:.1f}%")
col3.metric("Advance/Decline", f"{a_d_ratio:.2f}")

# Support/Resistance for NIFTY Index
def get_nearest_support_resistance(df, price):
    df = df.copy()
    df["min"] = df["Close"].iloc[argrelextrema(df["Close"].values, np.less_equal, order=5)[0]]
    df["max"] = df["Close"].iloc[argrelextrema(df["Close"].values, np.greater_equal, order=5)[0]]
    supports = df["min"].dropna()
    resistances = df["max"].dropna()
    nearest_support = supports[supports < price].max() if not supports.empty else None
    nearest_resistance = resistances[resistances > price].min() if not resistances.empty else None
    return nearest_support, nearest_resistance

nifty_df = yf.Ticker("^NSEI").history(period="90d", interval="1d")
nifty_price = nifty_df["Close"].iloc[-1]
support, resistance = get_nearest_support_resistance(nifty_df, nifty_price)
fig = go.Figure()

fig.add_trace(go.Scatter(
    x=nifty_df.index,
    y=nifty_df["Close"],
    mode="lines",
    name="NIFTY Close",
    line=dict(color="blue")
))

if support:
    fig.add_hline(
        y=support,
        line_dash="dot",
        line_color="green",
        annotation_text=f"Support: {support:.2f}",
        annotation_position="bottom right"
    )

if resistance:
    fig.add_hline(
        y=resistance,
        line_dash="dot",
        line_color="red",
        annotation_text=f"Resistance: {resistance:.2f}",
        annotation_position="top right"
    )

fig.update_layout(
    title="📈 NIFTY Index with Support & Resistance",
    xaxis_title="Date",
    yaxis_title="Price",
    height=500,
    plot_bgcolor="#f9f9f9",
    paper_bgcolor="#f9f9f9"
)

st.plotly_chart(fig, use_container_width=True)

st.subheader("📍 NIFTY Index Key Levels")
st.write(f"💰 Current Price: `{nifty_price:.2f}`")
if support:
    st.success(f"📉 Nearest Support: `{support:.2f}`")
if resistance:
    st.warning(f"📈 Nearest Resistance: `{resistance:.2f}`")

# Insights
st.subheader("📌 Market Signal Summary")
if pct_50 > 70 and a_d_ratio > 1.2:
    st.success("✅ BUY: Strong breadth and momentum.")
elif pct_50 < 40 and a_d_ratio < 0.8:
    st.error("❌ SELL: Market showing weakness.")
elif 40 <= pct_50 <= 70 and 0.8 <= a_d_ratio <= 1.2:
    st.info("⏸️ HOLD: Mixed signals.")
else:
    st.warning("⚠️ Be cautious — conflicting signals.")

if pct_200 > 70:
    st.success("📈 Long-term trend is strong.")
elif pct_200 < 40:
    st.error("📉 Long-term trend is weak.")
