import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objs as go
from plotly.subplots import make_subplots

st.set_page_config(page_title="📈 Technical Analysis", page_icon="📉", layout="wide")

st.title("📈 Technical Analysis")

# ─── User Inputs ─────────────────────────────────────────────
symbol = st.text_input("Enter NSE stock symbol (e.g., RELIANCE)", value="RELIANCE").upper()
period = st.selectbox("Select period", ["1mo", "3mo", "6mo", "1y", "2y", "5y", "max"], index=2)
indicators = st.multiselect(
    "Select indicators to overlay",
    ["SMA 20", "SMA 50", "EMA 20", "EMA 50", "RSI"],
    default=["SMA 20", "SMA 50"]
)

# ─── Data Fetching ───────────────────────────────────────────
if not symbol:
    st.warning("Please enter a stock symbol.")
    st.stop()

raw = yf.download(f"{symbol}.NS", period=period, interval="1d", group_by="ticker", auto_adjust=False)

if raw.empty:
    st.error("⚠️ No data found for this symbol.")
    st.stop()

# ─── MultiIndex Handling ─────────────────────────────────────
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

# ─── Indicator Calculations ──────────────────────────────────
if "SMA 20" in indicators:
    df["SMA20"] = df["Close"].rolling(window=20).mean()
if "SMA 50" in indicators:
    df["SMA50"] = df["Close"].rolling(window=50).mean()
if "EMA 20" in indicators:
    df["EMA20"] = df["Close"].ewm(span=20, adjust=False).mean()
if "EMA 50" in indicators:
    df["EMA50"] = df["Close"].ewm(span=50, adjust=False).mean()
if "RSI" in indicators:
    delta = df["Close"].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss
    df["RSI"] = 100 - (100 / (1 + rs))

# ─── Plotting ────────────────────────────────────────────────
rows = 2 if "RSI" in indicators else 1
fig = make_subplots(rows=rows, cols=1, shared_xaxes=True, vertical_spacing=0.1,
                    row_heights=[0.7] + [0.3] * (rows - 1),
                    specs=[[{"secondary_y": False}]] * rows)

# Candlestick
fig.add_trace(go.Candlestick(
    x=df.index,
    open=df["Open"], high=df["High"],
    low=df["Low"], close=df["Close"],
    name="Price"), row=1, col=1)

# Overlays
if "SMA 20" in indicators:
    fig.add_trace(go.Scatter(x=df.index, y=df["SMA20"], name="SMA 20"), row=1, col=1)
if "SMA 50" in indicators:
    fig.add_trace(go.Scatter(x=df.index, y=df["SMA50"], name="SMA 50"), row=1, col=1)
if "EMA 20" in indicators:
    fig.add_trace(go.Scatter(x=df.index, y=df["EMA20"], name="EMA 20"), row=1, col=1)
if "EMA 50" in indicators:
    fig.add_trace(go.Scatter(x=df.index, y=df["EMA50"], name="EMA 50"), row=1, col=1)

# RSI subplot
if "RSI" in indicators:
    fig.add_trace(go.Scatter(x=df.index, y=df["RSI"], name="RSI", line=dict(color='orange')), row=2, col=1)
    fig.update_yaxes(range=[0, 100], row=2, col=1)

# Volume subplot
fig.add_trace(go.Bar(x=df.index, y=df["Volume"], name="Volume", marker_color='gray'), row=rows, col=1)

fig.update_layout(
    height=700 if rows == 1 else 900,
    width=1000,
    title=f"Technical Analysis – {symbol}.NS",
    xaxis_rangeslider_visible=False
)

st.plotly_chart(fig, use_container_width=True)
