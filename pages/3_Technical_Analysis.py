# pages/3_Technical_Analysis.py
import streamlit as st
import yfinance as yf
import pandas as pd
from plotly.subplots import make_subplots
import plotly.graph_objects as go

# ── page & sidebar ────────────────────────────────────────────────
st.set_page_config(page_title="📉 Technical Analysis", layout="wide")
st.title("📉 Interactive Technical Chart (candlestick + MAs)")

symbol   = st.sidebar.text_input("NSE Symbol", "RELIANCE").upper().strip()
period   = st.sidebar.selectbox("Period",   ["3mo","6mo","1y","2y","5y","max"], 1)
interval = st.sidebar.selectbox("Interval", ["1d","1wk","1mo"], 0)
indicators = st.sidebar.multiselect(
    "Indicators",
    ["SMA 20", "SMA 50", "EMA 20", "EMA 50", "RSI"],
    default=["SMA 20", "SMA 50"]
)

# ── download & clean ─────────────────────────────────────────────
if not symbol: st.stop()
raw = yf.download(f"{symbol}.NS", period=period, interval=interval, group_by="ticker")

if raw.empty:
    st.error("No data returned. Try different symbol/period.")
    st.stop()

df = raw.xs(f"{symbol}.NS", axis=1, level=0) if isinstance(raw.columns, pd.MultiIndex) else raw.copy()
df = df.loc[:, ~df.columns.duplicated()]

if "Close" not in df and "Adj Close" in df:
    df["Close"] = df["Adj Close"]

needed = ["Open","High","Low","Close"]
if not set(needed).issubset(df.columns):
    st.error("Missing OHLC columns in data.")
    st.write(df.head())
    st.stop()

# ── indicators ───────────────────────────────────────────────────
if "SMA 20" in indicators: df["SMA20"] = df["Close"].rolling(20).mean()
if "SMA 50" in indicators: df["SMA50"] = df["Close"].rolling(50).mean()
if "EMA 20" in indicators: df["EMA20"] = df["Close"].ewm(span=20, adjust=False).mean()
if "EMA 50" in indicators: df["EMA50"] = df["Close"].ewm(span=50, adjust=False).mean()
if "RSI"    in indicators:
    delta = df["Close"].diff()
    gain  = delta.clip(lower=0).rolling(14).mean()
    loss  = (-delta.clip(upper=0)).rolling(14).mean()
    rs    = gain / loss
    df["RSI"] = 100 - (100 / (1 + rs))

# ── plotly figure ────────────────────────────────────────────────
rows = 2 if "RSI" in indicators else 1
fig  = make_subplots(rows=rows, cols=1, shared_xaxes=True,
                     specs=[[{}]]*rows,
                     row_heights=[0.75,0.25] if rows==2 else [1],
                     vertical_spacing=0.06)

# Candlestick
fig.add_trace(go.Candlestick(
    x=df.index, open=df["Open"], high=df["High"],
    low=df["Low"], close=df["Close"],
    name="Price",
    increasing_line_color="#26a69a",
    decreasing_line_color="#ef5350"
), row=1, col=1)

# Moving-average overlays
if "SMA 20" in indicators: fig.add_trace(go.Scatter(x=df.index, y=df["SMA20"], name="SMA 20"), row=1, col=1)
if "SMA 50" in indicators: fig.add_trace(go.Scatter(x=df.index, y=df["SMA50"], name="SMA 50"), row=1, col=1)
if "EMA 20" in indicators: fig.add_trace(go.Scatter(x=df.index, y=df["EMA20"], name="EMA 20"), row=1, col=1)
if "EMA 50" in indicators: fig.add_trace(go.Scatter(x=df.index, y=df["EMA50"], name="EMA 50"), row=1, col=1)

# RSI row (if chosen)
if "RSI" in indicators:
    fig.add_trace(go.Scatter(x=df.index, y=df["RSI"], name="RSI", line_color="orange"), row=2, col=1)
    fig.update_yaxes(range=[0,100], row=2, col=1)

# ── axis ranges: y from data min→max (pad 2 %) ───────────────────
y_min, y_max = df["Low"].min(), df["High"].max()
pad = (y_max - y_min) * 0.02
fig.update_yaxes(range=[y_min-pad, y_max+pad], row=1, col=1)

# Show only the last 30% of points initially (user can zoom out)
num_points = len(df)
start_idx  = max(0, int(num_points * 0.7))
fig.update_xaxes(range=[df.index[start_idx], df.index[-1]], row=1, col=1)

# add range-slider for easy zoom
fig.update_layout(
    height=750 if rows==2 else 600,
    title=f"{symbol}.NS – Technical Chart",
    xaxis_rangeslider_visible=True,
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
)

st.plotly_chart(fig, use_container_width=True)
