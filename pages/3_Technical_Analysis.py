# pages/3_Technical_Analysis.py
import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(page_title="📉 Technical Analysis", layout="wide")
st.title("📉 Technical Analysis")

# ───────────────────────────── sidebar ─────────────────────────────
symbol_in = st.sidebar.text_input("NSE symbol", "RELIANCE").strip().upper()
symbol    = f"{symbol_in}.NS" if not symbol_in.endswith(".NS") else symbol_in

interval_label = st.sidebar.selectbox(
    "Interval", ["5m","15m","30m","1h","4h","1d"], index=5
)
interval_map = {"5m":"5m","15m":"15m","30m":"30m","1h":"60m","4h":"60m","1d":"1d"}
yf_interval  = interval_map[interval_label]

# Intraday data limited to 30d by Yahoo
period = st.sidebar.selectbox(
    "Period",
    ["1d","5d","7d","30d","3mo","6mo","1y","2y","5y","max"],
    index=3 if yf_interval.endswith("m") else 6
)

indicators = st.sidebar.multiselect(
    "Indicators", ["SMA","EMA","RSI","Pivot Points"], default=["SMA"]
)

lens = {}
if "SMA" in indicators:
    lens["SMA"] = st.sidebar.number_input("SMA length", 5, 200, 20)
if "EMA" in indicators:
    lens["EMA"] = st.sidebar.number_input("EMA length", 5, 200, 20)
if "RSI" in indicators:
    lens["RSI"] = st.sidebar.number_input("RSI length", 5, 50, 14)

pivot_levels = []
if "Pivot Points" in indicators:
    pivot_levels = st.sidebar.multiselect(
        "Pivot levels", ["P","R1","R2","R3","S1","S2","S3"], default=["P","R1","S1"]
    )

# ─────────────────────────── fetch data ────────────────────────────
raw = yf.download(symbol, period=period, interval=yf_interval, progress=False)
if raw.empty:
    st.error("No data returned for this symbol/period/interval.")
    st.stop()

# ---------- flatten MultiIndex properly ----------
if isinstance(raw.columns, pd.MultiIndex):
    # Determine which level has the OHLC labels
    level0 = list(raw.columns.get_level_values(0))
    level1 = list(raw.columns.get_level_values(1))
    if set(level1) >= {"Open","High","Low","Close"}:
        df = raw.copy()
        df.columns = level1                        # keep level-1 field names
    elif set(level0) >= {"Open","High","Low","Close"}:
        df = raw.copy()
        df.columns = level0                        # keep level-0 field names
    else:
        # Most common: level-0 = ticker, level-1 = field
        try:
            df = raw.xs(symbol, axis=1, level=0)
        except KeyError:
            st.error("Could not flatten MultiIndex columns.")
            st.write(raw.head())
            st.stop()
else:
    df = raw.copy()

# ensure unique columns
df = df.loc[:, ~df.columns.duplicated()]

needed = {"Open","High","Low","Close"}
if not needed.issubset(df.columns):
    st.error(f"Missing OHLC columns: {needed - set(df.columns)}")
    st.write(df.head())
    st.stop()

# Resample 4h if requested
if interval_label == "4h":
    df = df.resample("4H").agg(
        {"Open":"first","High":"max","Low":"min","Close":"last","Volume":"sum"}
    ).dropna()

# ───── indicators ─────
if "SMA" in indicators:
    df[f"SMA{lens['SMA']}"] = df["Close"].rolling(lens["SMA"]).mean()
if "EMA" in indicators:
    df[f"EMA{lens['EMA']}"] = df["Close"].ewm(span=lens["EMA"], adjust=False).mean()
if "RSI" in indicators:
    delta = df["Close"].diff()
    gain  = delta.clip(lower=0).rolling(lens["RSI"]).mean()
    loss  = (-delta.clip(upper=0)).rolling(lens["RSI"]).mean()
    rs    = gain / loss
    df[f"RSI{lens['RSI']}"] = 100 - (100 / (1 + rs))

pivots = {}
if "Pivot Points" in indicators and len(df) >= 2:
    last = df.iloc[-2]
    P = (last["High"] + last["Low"] + last["Close"]) / 3
    pivots = {
        "P": P,
        "R1": 2*P - last["Low"],
        "S1": 2*P - last["High"],
        "R2": P + (last["High"] - last["Low"]),
        "S2": P - (last["High"] - last["Low"]),
        "R3": last["High"] + 2*(P - last["Low"]),
        "S3": last["Low"]  - 2*(last["High"] - P)
    }

# ───── plot ─────
rows = 2 if "RSI" in indicators else 1
fig  = make_subplots(
    rows=rows, cols=1, shared_xaxes=True,
    specs=[[{}]]*rows, row_heights=[0.75,0.25] if rows==2 else [1],
    vertical_spacing=0.06
)

fig.add_trace(go.Candlestick(
    x=df.index, open=df["Open"], high=df["High"],
    low=df["Low"], close=df["Close"],
    name="Price", increasing_line_color="#26a69a", decreasing_line_color="#ef5350"
), row=1, col=1)

for ind in ("SMA","EMA"):
    if ind in indicators:
        fig.add_trace(go.Scatter(
            x=df.index, y=df[f"{ind}{lens[ind]}"],
            name=f"{ind} {lens[ind]}"
        ), row=1, col=1)

if "Pivot Points" in indicators:
    colors = {
        "P":"blue","R1":"green","S1":"red",
        "R2":"lightgreen","S2":"salmon",
        "R3":"lime","S3":"orangered"
    }
    for lvl in pivot_levels:
        if lvl in pivots:
            fig.add_hline(y=pivots[lvl], line_color=colors.get(lvl,"gray"),
                          annotation_text=lvl, annotation_position="top left")

if "RSI" in indicators:
    fig.add_trace(go.Scatter(
        x=df.index, y=df[f"RSI{lens['RSI']}"],
        name=f"RSI {lens['RSI']}", line_color="orange"
    ), row=2, col=1)
    fig.update_yaxes(range=[0,100], row=2, col=1)

# clean layout
low, high = df["Low"].min(), df["High"].max()
pad = (high-low)*0.03
fig.update_yaxes(range=[low-pad, high+pad], row=1, col=1)
fig.update_xaxes(showgrid=False)
fig.update_yaxes(showgrid=False)
fig.update_layout(
    height=800 if rows==2 else 600,
    title=f"{symbol} – Technical Chart ({interval_label})",
    xaxis_rangeslider_visible=True,
    legend=dict(orientation="h", y=1.02)
)

st.plotly_chart(fig, use_container_width=True)
