# pages/3_Technical_Analysis.py
import streamlit as st
import yfinance as yf
import pandas as pd
from plotly.subplots import make_subplots
import plotly.graph_objects as go

st.set_page_config(page_title="📉 Technical Analysis", page_icon="📉", layout="wide")
st.title("📉 Technical Analysis")

# ── user controls ─────────────────────────────────────────────
symbol  = st.text_input("NSE symbol", "RELIANCE").upper().strip()
period  = st.selectbox("Period",   ["3mo","6mo","1y","2y","5y","max"], 1)
interval= st.selectbox("Interval", ["1d","1wk","1mo"], 0)
indicators = st.multiselect(
    "Indicators",
    ["SMA 20", "SMA 50", "EMA 20", "EMA 50", "RSI"],
    default=["SMA 20", "SMA 50"]
)

if not symbol:
    st.stop()

# ── download & clean ──────────────────────────────────────────
raw = yf.download(f"{symbol}.NS", period=period, interval=interval, group_by="ticker")
if raw.empty:
    st.error("No data returned. Try a different symbol/period.")
    st.stop()

# flatten multi-index
df = raw.xs(f"{symbol}.NS", axis=1, level=0) if isinstance(raw.columns, pd.MultiIndex) else raw.copy()
df = df.loc[:, ~df.columns.duplicated()]

# use Adj Close if Close missing
if "Close" not in df and "Adj Close" in df:
    df["Close"] = df["Adj Close"]

needed = ["Open","High","Low","Close","Volume"]
if not set(needed).issubset(df.columns):
    st.error(f"Missing columns: {set(needed)-set(df.columns)}")
    st.write(df.head())
    st.stop()

# ── indicators ────────────────────────────────────────────────
if "SMA 20" in indicators:
    df["SMA20"] = df["Close"].rolling(20).mean()
if "SMA 50" in indicators:
    df["SMA50"] = df["Close"].rolling(50).mean()
if "EMA 20" in indicators:
    df["EMA20"] = df["Close"].ewm(span=20, adjust=False).mean()
if "EMA 50" in indicators:
    df["EMA50"] = df["Close"].ewm(span=50, adjust=False).mean()
if "RSI" in indicators:
    delta = df["Close"].diff()
    gain  = delta.clip(lower=0).rolling(14).mean()
    loss  = (-delta.clip(upper=0)).rolling(14).mean()
    rs    = gain / loss
    df["RSI"] = 100 - (100 / (1 + rs))

# ── build figure ──────────────────────────────────────────────
rows = 2 if "RSI" in indicators else 1
fig  = make_subplots(
    rows=rows, cols=1, shared_xaxes=True,
    specs=[[{"secondary_y": True}]] + [[{}]]*(rows-1),
    row_heights=[0.75, 0.25] if rows==2 else [1],
    vertical_spacing=0.06
)

# 1️⃣ candlesticks
fig.add_trace(go.Candlestick(
    x=df.index, open=df["Open"], high=df["High"],
    low=df["Low"], close=df["Close"],
    name="Price",
    increasing_line_color="#26a69a",
    decreasing_line_color="#ef5350"
), row=1, col=1, secondary_y=False)

# ️▶ overlay MAs
if "SMA 20" in indicators:
    fig.add_trace(go.Scatter(x=df.index, y=df["SMA20"], name="SMA 20"), row=1, col=1)
if "SMA 50" in indicators:
    fig.add_trace(go.Scatter(x=df.index, y=df["SMA50"], name="SMA 50"), row=1, col=1)
if "EMA 20" in indicators:
    fig.add_trace(go.Scatter(x=df.index, y=df["EMA20"], name="EMA 20"), row=1, col=1)
if "EMA 50" in indicators:
    fig.add_trace(go.Scatter(x=df.index, y=df["EMA50"], name="EMA 50"), row=1, col=1)

# 📊 volume on secondary-y axis
fig.add_trace(go.Bar(
    x=df.index, y=df["Volume"], name="Volume",
    marker_color="rgba(150,150,150,0.4)"
), row=1, col=1, secondary_y=True)

# 2️⃣ RSI row
if "RSI" in indicators:
    fig.add_trace(go.Scatter(x=df.index, y=df["RSI"], name="RSI", line_color="orange"), row=2, col=1)
    fig.update_yaxes(range=[0, 100], row=2, col=1)

# layout
fig.update_layout(
    height=800, xaxis_rangeslider_visible=False,
    title=f"{symbol}.NS – Technical Chart",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
)
fig.update_yaxes(title_text="Price",  row=1, col=1, secondary_y=False)
fig.update_yaxes(title_text="Volume", row=1, col=1, secondary_y=True)

st.plotly_chart(fig, use_container_width=True)
