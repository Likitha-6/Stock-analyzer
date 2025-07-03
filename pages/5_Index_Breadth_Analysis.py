import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
from scipy.signal import argrelextrema
import plotly.graph_objects as go
import requests

# Fetch symbols from NSE live endpoint
@st.cache_data
def fetch_nifty_50_symbols():
    url = "https://www1.nseindia.com/api/equity-stockIndices?index=NIFTY%2050"
    headers = {
        "User-Agent": "Mozilla/5.0"
    }
    try:
        response = requests.get(url, headers=headers)
        data = response.json()
        df = pd.DataFrame(data['data'])
        symbols = df['symbol'].dropna().unique().tolist()
        return symbols
    except Exception as e:
        st.error("Failed to load NIFTY 50 symbols dynamically.")
        return []

nifty_symbols = fetch_nifty_50_symbols()

st.title("Index Breadth & Support/Resistance Analysis")

# Function to get breadth metrics and chart for any index symbol
def analyze_index(index_symbol, index_name):
    st.header(f"📊 {index_name} Analysis")

    # Compute Breadth Metrics
    ma50_above = ma200_above = advance = decline = 0
    valid_count = 0
    with st.spinner(f"Fetching stock data for {index_name}..."):
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

    # Support/Resistance & EMA chart
    df_index = yf.Ticker(index_symbol).history(period="90d", interval="1d")
    price = df_index["Close"].iloc[-1]
    df_index = df_index.reset_index()
    if "Date" not in df_index.columns:
        df_index.rename(columns={df_index.columns[0]: "Date"}, inplace=True)

    def get_nearest_support_resistance(df, price):
        df = df.copy()
        df["min"] = df["Close"].iloc[argrelextrema(df["Close"].values, np.less_equal, order=5)[0]]
        df["max"] = df["Close"].iloc[argrelextrema(df["Close"].values, np.greater_equal, order=5)[0]]
        supports = df["min"].dropna()
        resistances = df["max"].dropna()
        nearest_support = supports[supports < price].max() if not supports.empty else None
        nearest_resistance = resistances[resistances > price].min() if not resistances.empty else None
        return nearest_support, nearest_resistance

    support, resistance = get_nearest_support_resistance(df_index, price)
    df_index["EMA_9"] = df_index["Close"].ewm(span=9, adjust=False).mean()
    df_index["EMA_15"] = df_index["Close"].ewm(span=15, adjust=False).mean()

    fig = go.Figure()
    fig.add_trace(go.Candlestick(
        x=df_index["Date"],
        open=df_index["Open"],
        high=df_index["High"],
        low=df_index["Low"],
        close=df_index["Close"],
        name=index_name,
        increasing_line_color="green",
        decreasing_line_color="red"
    ))
    fig.add_trace(go.Scatter(x=df_index["Date"], y=df_index["EMA_9"], mode="lines", name="EMA 9", line=dict(color="orange")))
    fig.add_trace(go.Scatter(x=df_index["Date"], y=df_index["EMA_15"], mode="lines", name="EMA 15", line=dict(color="cyan")))

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

    st.subheader("Market Signal Summary")
    if pct_50 > 70 and a_d_ratio > 1.2:
        st.success("BUY: Strong breadth and momentum.")
    elif pct_50 < 40 and a_d_ratio < 0.8:
        st.error("SELL: Market showing weakness.")
    elif 40 <= pct_50 <= 70 and 0.8 <= a_d_ratio <= 1.2:
        st.info("HOLD: Mixed signals.")
    else:
        st.warning("Be cautious — conflicting signals.")

    if pct_200 > 70:
        st.success("Long-term trend is strong.")
    elif pct_200 < 40:
        st.error("Long-term trend is weak.")

# Run analysis for NIFTY 50
analyze_index("^NSEI", "NIFTY 50")

# To add more indexes:
# analyze_index("^BSESN", "SENSEX")
# analyze_index("^NSEBANK", "NIFTY Bank")
