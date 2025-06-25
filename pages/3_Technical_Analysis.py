# pages/3_Technical_Analysis.py
import streamlit as st
import yfinance as yf
import pandas as pd
from plotly.subplots import make_subplots
import plotly.graph_objects as go

st.set_page_config(page_title="📉 Technical Analysis", layout="wide")
st.title("📉 Technical Analysis")

# ── Sidebar controls ──────────────────────────────────────────
symbol   = st.sidebar.text_input("NSE symbol", "RELIANCE").upper().strip()
period   = st.sidebar.selectbox("Period", ["3mo","6mo","1y","2y","5y","max"], 1)
interval = st.sidebar.selectbox("Interval", ["1d","1wk"], 0)

indicator = st.sidebar.selectbox(
    "Indicator",
    ["SMA", "EMA", "RSI", "Pivot Points"]
)

length = None
if indicator in ("SMA", "EMA"):
    length = st.sidebar.number_input("Length", min_value=5, max_value=200, value=20, step=1)
elif indicator == "RSI":
    length = st.sidebar.number_input("RSI length", min_value=5, max_value=50, value=14, step=1)

# ── Fetch data ────────────────────────────────────────────────
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
    st.error("Missing OHLC columns.")
    st.stop()

# ── Compute chosen indicator ─────────────────────────────────
if indicator == "SMA":
    df[f"SMA{length}"] = df["Close"].rolling(length).mean()
elif indicator == "EMA":
    df[f"EMA{length}"] = df["Close"].ewm(span=length, adjust=False).mean()
elif indicator == "RSI":
    delta = df["Close"].diff()
    gain  = delta.clip(lower=0).rolling(length).mean()
    loss  = (-delta.clip(upper=0)).rolling(length).mean()
    rs    = gain / loss
    df[f"RSI{length}"] = 100 - (100 / (1 + rs))
elif indicator == "Pivot Points":
    last = df.iloc[-2] if len(df) > 1 else df.iloc[-1]
    P  = (last["High"] + last["Low"] + last["Close"]) / 3
    R1 = 2*P - last["Low"]
    S1 = 2*P - last["High"]
    R2 = P + (last["High"] - last["Low"])
    S2 = P - (last["High"] - last["Low"])
    R3 = last["High"] + 2*(P - last["Low"])
    S3 = last["Low"]  - 2*(last["High"] - P)
    pivots = {"P":P,"R1":R1,"S1":S1,"R2":R2,"S2":S2,"R3":R3,"S3":S3}

# ── Build figure ─────────────────────────────────────────────
rows = 2 if indicator.startswith("RSI") else 1
fig  = make_subplots(rows=rows, cols=1, shared_xaxes=True,
                     specs=[[{}]]*rows,
                     row_heights=[0.75,0.25] if rows==2 else [1])

# Candlesticks
fig.add_trace(go.Candlestick(
    x=df.index, open=df["Open"], high=df["High"],
    low=df["Low"], close=df["Close"],
    name="Price", increasing_line_color="#26a69a",
    decreasing_line_color="#ef5350"
), row=1, col=1)

# Overlay chosen indicator
if indicator == "SMA":
    fig.add_trace(go.Scatter(x=df.index, y=df[f"SMA{length}"],
                             name=f"SMA {length}", line_width=1.5), row=1, col=1)
elif indicator == "EMA":
    fig.add_trace(go.Scatter(x=df.index, y=df[f"EMA{length}"],
                             name=f"EMA {length}", line_width=1.5), row=1, col=1)
elif indicator == "RSI":
    fig.add_trace(go.Scatter(x=df.index, y=df[f"RSI{length}"],
                             name=f"RSI {length}", line_color="orange"), row=2, col=1)
    fig.update_yaxes(range=[0,100], row=2, col=1)
elif indicator == "Pivot Points":
    for name, y in pivots.items():
        fig.add_hline(y=y, annotation_text=name, annotation_position="top left",
                      line_dash="dot", line_color="gray")

# Adjust y-axis to price range
ymin, ymax = df["Low"].min(), df["High"].max()
pad = (ymax - ymin) * 0.02
fig.update_yaxes(range=[ymin-pad, ymax+pad], row=1, col=1)

fig.update_layout(
    height=800 if rows==2 else 600,
    title=f"{symbol}.NS – {indicator} Chart",
    xaxis_rangeslider_visible=True,
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
)

st.plotly_chart(fig, use_container_width=True)
