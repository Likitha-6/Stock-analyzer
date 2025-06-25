# pages/3_Technical_Analysis.py
import streamlit as st
import yfinance as yf
import pandas as pd
from plotly.subplots import make_subplots
import plotly.graph_objects as go

# ───────────────────────────────────────────────────────────────
st.set_page_config(page_title="📉 Technical Analysis", layout="wide")
st.title("📉 Technical Analysis")

# ── sidebar ────────────────────────────────────────────────────
symbol   = st.sidebar.text_input("NSE symbol", "RELIANCE").strip().upper()
period   = st.sidebar.selectbox("Period",
            ["30d","3mo","6mo","1y","2y","5y","max"], index=1)   # 30d for intraday
interval_label = st.sidebar.selectbox("Interval",
    ["1d","1wk","5 m","15 m","30 m","1 hr","4 hr"], index=0)

indicator = st.sidebar.selectbox("Indicator", ["SMA","EMA","RSI","Pivot Points"])
length = None
if indicator in ("SMA","EMA"):
    length = st.sidebar.number_input("Length", 5, 200, 20)
elif indicator=="RSI":
    length = st.sidebar.number_input("RSI length", 5, 50, 14)

# ── map interval label → yf interval code ──────────────────────
interval_map = {
    "1d":"1d","1wk":"1wk",
    "5 m":"5m","15 m":"15m","30 m":"30m",
    "1 hr":"60m","4 hr":"60m"   # 4-hour built from 60-minute
}
yf_interval = interval_map[interval_label]

# Yahoo only allows max ~30d for intraday; adjust if needed
if yf_interval.endswith("m") and period not in ("5d","7d","10d","30d"):
    st.info("⏱️ Intraday data limited to 30 days – period set to 30d.")
    period = "30d"

if not symbol: st.stop()

raw = yf.download(f"{symbol}.NS", period=period, interval=yf_interval, group_by="ticker")
if raw.empty:
    st.error("No data returned. Try another symbol, shorter period, or larger interval.")
    st.stop()

# ── flatten multi-index & basic clean-up ───────────────────────
df = raw.xs(f"{symbol}.NS", axis=1, level=0) if isinstance(raw.columns, pd.MultiIndex) else raw.copy()
df = df.loc[:, ~df.columns.duplicated()]

if "Close" not in df and "Adj Close" in df:
    df["Close"] = df["Adj Close"]

needed = ["Open","High","Low","Close"]
if not set(needed).issubset(df.columns):
    st.error("Missing OHLC columns.")
    st.stop()

# ── if user chose 4-hour, resample 60 m data → 4 H OHLCV ——––—
if interval_label == "4 hr":
    df = df.resample("4H").agg({
        "Open":  "first",
        "High":  "max",
        "Low":   "min",
        "Close": "last",
        "Volume":"sum"
    }).dropna()

# ── indicators ────────────────────────────────────────────────
if indicator=="SMA":
    df[f"SMA{length}"] = df["Close"].rolling(length).mean()
elif indicator=="EMA":
    df[f"EMA{length}"] = df["Close"].ewm(span=length, adjust=False).mean()
elif indicator=="RSI":
    delta = df["Close"].diff()
    gain  = delta.clip(lower=0).rolling(length).mean()
    loss  = (-delta.clip(upper=0)).rolling(length).mean()
    rs    = gain / loss
    df[f"RSI{length}"] = 100 - (100 / (1 + rs))
elif indicator=="Pivot Points":
    last = df.iloc[-2] if len(df) > 1 else df.iloc[-1]
    P  = (last["High"] + last["Low"] + last["Close"]) / 3
    pivots = {
        "P": P,
        "R1": 2*P - last["Low"],
        "S1": 2*P - last["High"],
        "R2": P + (last["High"] - last["Low"]),
        "S2": P - (last["High"] - last["Low"]),
        "R3": last["High"] + 2*(P - last["Low"]),
        "S3": last["Low"]  - 2*(last["High"] - P)
    }

# ── build figure ──────────────────────────────────────────────
rows = 2 if indicator=="RSI" else 1
fig  = make_subplots(rows=rows, cols=1, shared_xaxes=True,
                     specs=[[{}]]*rows,
                     row_heights=[0.75,0.25] if rows==2 else [1],
                     vertical_spacing=0.06)

fig.add_trace(go.Candlestick(
    x=df.index, open=df["Open"], high=df["High"],
    low=df["Low"], close=df["Close"],
    name="Price", increasing_line_color="#26a69a",
    decreasing_line_color="#ef5350"
), row=1, col=1)

if indicator=="SMA":
    fig.add_trace(go.Scatter(x=df.index, y=df[f"SMA{length}"], name=f"SMA {length}"), row=1, col=1)
elif indicator=="EMA":
    fig.add_trace(go.Scatter(x=df.index, y=df[f"EMA{length}"], name=f"EMA {length}"), row=1, col=1)
elif indicator=="RSI":
    fig.add_trace(go.Scatter(x=df.index, y=df[f"RSI{length}"], name=f"RSI {length}", line_color="orange"), row=2, col=1)
    fig.update_yaxes(range=[0,100], row=2, col=1)
elif indicator=="Pivot Points":
    for name,y in pivots.items():
        fig.add_hline(y=y, line_dash="dot", line_color="gray",
                      annotation_text=name, annotation_position="top left")

# y-axis tight padding
low, high = df["Low"].min(), df["High"].max()
pad = (high-low)*0.03
fig.update_yaxes(range=[low-pad, high+pad], row=1, col=1)

fig.update_layout(
    height=800 if rows==2 else 600,
    title=f"{symbol}.NS – {indicator} ({interval_label})",
    xaxis_rangeslider_visible=True,
    legend=dict(orientation="h", y=1.02)
)

st.plotly_chart(fig, use_container_width=True)
