import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objs as go
from plotly.subplots import make_subplots

st.set_page_config(page_title="📈 Technical Analysis", page_icon="📉", layout="wide")

st.title("📈 Technical Analysis")

symbol = st.text_input("Enter NSE stock symbol (e.g., RELIANCE)", value="RELIANCE").upper()
period = st.selectbox("Select period", ["1mo", "3mo", "6mo", "1y", "2y", "5y", "max"], index=2)

if not symbol:
    st.warning("Please enter a stock symbol.")
    st.stop()

# Download with MultiIndex
raw = yf.download(f"{symbol}.NS", period=period, interval="1d", group_by="ticker", auto_adjust=False)

if raw.empty:
    st.error("⚠️ No data found for this symbol.")
    st.stop()

# Handle MultiIndex
if isinstance(raw.columns, pd.MultiIndex):
    try:
        df = raw.xs(f"{symbol}.NS", axis=1, level=0)
    except KeyError:
        st.error("⚠️ Could not locate expected ticker columns in data.")
        st.write("Columns:", raw.columns)
        st.stop()
else:
    df = raw.copy()

expected_cols = ["Open", "High", "Low", "Close", "Volume"]
missing = [col for col in expected_cols if col not in df.columns]
if missing:
    st.error(f"⚠️ Missing expected columns: {missing}")
    st.write(df.head())
    st.stop()

# Indicators
df["SMA20"] = df["Close"].rolling(window=20).mean()
df["SMA50"] = df["Close"].rolling(window=50).mean()

# Plotting
fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                    vertical_spacing=0.1, row_heights=[0.7, 0.3],
                    specs=[[{"secondary_y": False}], [{"secondary_y": False}]])

# Candlestick
fig.add_trace(go.Candlestick(
    x=df.index,
    open=df["Open"], high=df["High"],
    low=df["Low"], close=df["Close"],
    name="Price"), row=1, col=1)

# SMA overlays
fig.add_trace(go.Scatter(x=df.index, y=df["SMA20"], name="SMA 20", line=dict(width=1.5)), row=1, col=1)
fig.add_trace(go.Scatter(x=df.index, y=df["SMA50"], name="SMA 50", line=dict(width=1.5)), row=1, col=1)

# Volume
fig.add_trace(go.Bar(x=df.index, y=df["Volume"], name="Volume", marker_color='gray'), row=2, col=1)

fig.update_layout(height=700, width=1000, title=f"Technical Analysis for {symbol}.NS", 
                  xaxis_rangeslider_visible=False)

st.plotly_chart(fig, use_container_width=True)
