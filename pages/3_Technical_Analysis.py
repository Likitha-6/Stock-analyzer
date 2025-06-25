# pages/3_Technical_Analysis.py
import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# ────────── Page config ──────────
st.set_page_config(page_title="📉 Technical Analysis", layout="wide")
st.title("📉 Technical Analysis")

# ────────── Sidebar controls ──────────
tickers = raw.columns.get_level_values(0).unique()
symbol = st.selectbox("Select Symbol", tickers)

interval_map = {"5m":"5m","15m":"15m","30m":"30m","1 h":"60m","4 h":"60m","1 d":"1d"}
interval_key = st.sidebar.selectbox("Interval", list(interval_map.keys()), index=5)
yf_interval  = interval_map[interval_key]

period = st.sidebar.selectbox(
    "Period",
    ["1d","5d","30d","3mo","6mo","1y","2y","5y","max"],
    index=2 if yf_interval.endswith("m") else 4
)

# Indicator selections
sma_lengths = st.sidebar.multiselect("SMA lengths", [5,10,20,50,100,200], default=[20])
ema_lengths = st.sidebar.multiselect("EMA lengths", [5,10,20,50,100,200], default=[])
rsi_length  = st.sidebar.number_input("RSI length", 5, 50, 14, step=1)
show_rsi    = st.sidebar.checkbox("Show RSI", value=False)

pivot_on    = st.sidebar.checkbox("Show Pivot Points", value=True)
pivot_type  = st.sidebar.selectbox("Pivot type", ["classic","fibonacci","woodie","camarilla"])
pivot_lvls  = st.sidebar.multiselect(
    "Pivot levels", ["P","R1","R2","R3","S1","S2","S3"], default=["P","R1","S1"]
)

# ────────── Fetch data ──────────
raw = yf.download(symbol, period=period, interval=yf_interval, progress=False)
if raw.empty:
    st.error("No data returned for this symbol / period / interval.")
    st.stop()

# Flatten multi-index columns
if isinstance(raw.columns, pd.MultiIndex):
    if {"Open","High","Low","Close"}.issubset(raw.columns.get_level_values(1)):
        raw.columns = raw.columns.get_level_values(1)
    else:
        raw = raw.xs(symbol, axis=1, level=0)

raw = raw.loc[:, ~raw.columns.duplicated()]

need = {"Open","High","Low","Close"}
if not need.issubset(raw.columns):
    st.error(f"Missing columns: {need - set(raw.columns)}")
    st.stop()

# Resample 4 h from 60 m data
if interval_key == "4 h":
    raw = raw.resample("4H").agg({"Open":"first","High":"max","Low":"min","Close":"last"}).dropna()

df = raw.copy()

# ────────── Indicators ──────────
for n in sma_lengths:
    df[f"SMA{n}"] = df["Close"].rolling(n).mean()

for n in ema_lengths:
    df[f"EMA{n}"] = df["Close"].ewm(span=n, adjust=False).mean()

if show_rsi:
    delta = df["Close"].diff()
    gain  = delta.clip(lower=0).rolling(rsi_length).mean()
    loss  = (-delta.clip(upper=0)).rolling(rsi_length).mean()
    df[f"RSI{rsi_length}"] = 100 - (100 / (1 + gain / loss))

def calc_pivots(row, ptype="classic"):
    H, L, C = row["High"], row["Low"], row["Close"]
    if ptype == "classic":
        P = (H+L+C)/3; return {
            "P":P,"R1":2*P-L,"S1":2*P-H,
            "R2":P+(H-L),"S2":P-(H-L),
            "R3":H+2*(P-L),"S3":L-2*(H-P)
        }
    if ptype == "fibonacci":
        P=(H+L+C)/3;d=H-L;return{
            "P":P,"R1":P+0.382*d,"S1":P-0.382*d,
            "R2":P+0.618*d,"S2":P-0.618*d,
            "R3":P+d,"S3":P-d}
    if ptype == "woodie":
        P=(H+L+2*C)/4;return{
            "P":P,"R1":2*P-L,"S1":2*P-H,
            "R2":P+(H-L),"S2":P-(H-L)}
    if ptype == "camarilla":
        d=H-L;return{
            "P":(H+L+C)/3,"R1":C+0.0916*d,"S1":C-0.0916*d,
            "R2":C+0.183*d,"S2":C-0.183*d,
            "R3":C+0.275*d,"S3":C-0.275*d}
    return {}

pivots = calc_pivots(df.iloc[-2], pivot_type) if pivot_on and len(df) >= 2 else {}

# ────────── Plot ──────────
rows = 2 if show_rsi else 1
fig  = make_subplots(rows=rows, cols=1, shared_xaxes=True,
                     specs=[[{}]]*rows,
                     row_heights=[0.75,0.25] if rows==2 else [1],
                     vertical_spacing=0.06)

fig.add_trace(go.Candlestick(
    x=df.index, open=df["Open"], high=df["High"],
    low=df["Low"], close=df["Close"],
    name="Price", increasing_line_color="#26a69a", decreasing_line_color="#ef5350"
), row=1, col=1)

for n in sma_lengths:
    fig.add_trace(go.Scatter(x=df.index, y=df[f"SMA{n}"], name=f"SMA {n}"), row=1, col=1)
for n in ema_lengths:
    fig.add_trace(go.Scatter(x=df.index, y=df[f"EMA{n}"], name=f"EMA {n}"), row=1, col=1)

# Pivot lines
colors={"P":"blue","R1":"green","R2":"lightgreen","R3":"lime","S1":"red","S2":"salmon","S3":"orangered"}
for lvl in pivot_lvls:
    if lvl in pivots:
        fig.add_hline(y=pivots[lvl], line_color=colors.get(lvl,"gray"),
                      annotation_text=lvl, annotation_position="top left")

# RSI subplot
if show_rsi:
    fig.add_trace(go.Scatter(
        x=df.index, y=df[f"RSI{rsi_length}"],
        line_color="orange", name=f"RSI {rsi_length}"
    ), row=2, col=1)
    fig.update_yaxes(range=[0,100], row=2, col=1)

# Axis padding & grid removal
lo, hi = df["Low"].min(), df["High"].max()
pad = (hi-lo)*0.03
fig.update_yaxes(range=[lo-pad, hi+pad], row=1, col=1)
fig.update_xaxes(showgrid=False,
                 rangebreaks=[
                     dict(bounds=["sat","mon"]),
                     dict(pattern="hour", bounds=[10,24]),
                     dict(pattern="hour", bounds=[0,3.45])
                 ])
fig.update_yaxes(showgrid=False)

fig.update_layout(
    height=800 if rows == 2 else 600,
    title=f"{symbol} — {interval_key}",
    xaxis_rangeslider_visible=True,
    legend=dict(orientation="h", y=1.02),
    dragmode="pan"  # ← ADD THIS LINE
)


st.plotly_chart(fig, use_container_width=True)
