# pages/3_Technical_Analysis.py
import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# ── Try to fetch full NSE ticker list from your DB (DimCompany) ──
def get_all_symbols():
    try:
        import sqlalchemy as sa
        eng = sa.create_engine("sqlite:///nse.db", future=True)
        tick = pd.read_sql("SELECT Symbol FROM DimCompany", eng)["Symbol"].tolist()
        return [s if s.endswith(".NS") else f"{s}.NS" for s in tick]
    except Exception:
        pass
    # Fallback: yfinance tickers list (NSE)
    try:
        tbl = yf.tickers_nifty50()
        return [t if t.endswith(".NS") else f"{t}.NS" for t in tbl.tickers]
    except Exception:
        pass
    # Last-resort manual
    return ["RELIANCE.NS","TCS.NS","INFY.NS","HDFCBANK.NS"]

SYMBOLS = sorted(set(get_all_symbols()))

# ─────────────────────────  UI  ─────────────────────────
st.set_page_config(page_title="📉 Technical Analysis", layout="wide")
st.title("📉 Technical Analysis")

symbol = st.sidebar.selectbox("NSE Symbol", SYMBOLS, index=SYMBOLS.index("RELIANCE.NS") if "RELIANCE.NS" in SYMBOLS else 0)

interval_map = {"5 m":"5m","15 m":"15m","30 m":"30m","1 h":"60m","4 h":"60m","1 d":"1d"}
interval_label = st.sidebar.selectbox("Interval", list(interval_map.keys()), index=5)
yf_interval = interval_map[interval_label]
period = st.sidebar.selectbox("Period", ["1d","5d","30d","3mo","6mo","1y","2y","5y","max"], index=2 if yf_interval.endswith("m") else 4)

# indicators
sma_vals = st.sidebar.multiselect("SMA lengths", [5,10,20,50,100,200], default=[20])
ema_vals = st.sidebar.multiselect("EMA lengths", [5,10,20,50,100,200])
show_rsi = st.sidebar.checkbox("Show RSI", value=False)
rsi_len  = st.sidebar.number_input("RSI length", 5, 50, 14) if show_rsi else None
pivot_on = st.sidebar.checkbox("Show Pivot Points", value=True)
pivot_type = st.sidebar.selectbox("Pivot type", ["classic","fibonacci","woodie","camarilla"])
pivot_lvls = st.sidebar.multiselect("Pivot levels", ["P","R1","R2","R3","S1","S2","S3"],
                                    default=["P","R1","S1"]) if pivot_on else []

# ───────────────────────  Data  ─────────────────────────
raw = yf.download(symbol, period=period, interval=yf_interval, group_by="ticker", progress=False)
if raw.empty:
    st.error("No data returned.")
    st.stop()

# Flatten columns
if isinstance(raw.columns, pd.MultiIndex):
    if {"Open","High","Low","Close"}.issubset(raw.columns.get_level_values(1)):
        df = raw.copy()
        df.columns = raw.columns.get_level_values(1)
    else:
        df = raw.xs(symbol, axis=1, level=0).copy()
else:
    df = raw.copy()

# Ensure no duplicates
df = df.loc[:, ~df.columns.duplicated()]

if {"Open","High","Low","Close"} - set(df.columns):
    st.error("Missing OHLC in data")
    st.stop()

# Resample 4-hour
if interval_label == "4 h":
    df = df.resample("4H").agg({"Open":"first","High":"max","Low":"min","Close":"last","Volume":"sum"}).dropna()

# ── Indicators
for n in sma_vals:
    df[f"SMA{n}"] = df["Close"].rolling(n).mean()
for n in ema_vals:
    df[f"EMA{n}"] = df["Close"].ewm(span=n, adjust=False).mean()
if show_rsi:
    d = df["Close"].diff()
    gain = d.clip(lower=0).rolling(rsi_len).mean()
    loss = (-d.clip(upper=0)).rolling(rsi_len).mean()
    df[f"RSI{rsi_len}"] = 100 - (100/(1+gain/loss))

# Pivot calc
def pivots(row, typ="classic"):
    H,L,C = row["High"], row["Low"], row["Close"]
    if typ=="classic":
        P=(H+L+C)/3;d=H-L
        return {"P":P,"R1":2*P-L,"S1":2*P-H,"R2":P+d,"S2":P-d,"R3":H+2*(P-L),"S3":L-2*(H-P)}
    if typ=="fibonacci":
        P=(H+L+C)/3;d=H-L
        return {"P":P,"R1":P+0.382*d,"S1":P-0.382*d,"R2":P+0.618*d,"S2":P-0.618*d,"R3":P+d,"S3":P-d}
    if typ=="woodie":
        P=(H+L+2*C)/4;d=H-L
        return {"P":P,"R1":2*P-L,"S1":2*P-H,"R2":P+d,"S2":P-d}
    if typ=="camarilla":
        d=H-L
        return {"P":(H+L+C)/3,"R1":C+0.0916*d,"S1":C-0.0916*d,"R2":C+0.183*d,"S2":C-0.183*d,"R3":C+0.275*d,"S3":C-0.275*d}
    return {}
pivot_dict = pivots(df.iloc[-2], pivot_type) if pivot_on and len(df)>=2 else {}

# ── Plot
rows = 2 if show_rsi else 1
fig  = make_subplots(rows=rows, cols=1, shared_xaxes=True,
                     specs=[[{}]]*rows, row_heights=[0.75,0.25] if rows==2 else [1])

fig.add_trace(go.Candlestick(
    x=df.index, open=df["Open"], high=df["High"],
    low=df["Low"], close=df["Close"],
    increasing_line_color="#26a69a", decreasing_line_color="#ef5350", name="Price"), row=1,col=1)

for n in sma_vals: fig.add_trace(go.Scatter(x=df.index,y=df[f"SMA{n}"],name=f"SMA {n}"), row=1,col=1)
for n in ema_vals: fig.add_trace(go.Scatter(x=df.index,y=df[f"EMA{n}"],name=f"EMA {n}"), row=1,col=1)

if pivot_on:
    colors={"P":"blue","R1":"green","R2":"lightgreen","R3":"lime","S1":"red","S2":"salmon","S3":"orangered"}
    for lvl in pivot_lvls:
        if lvl in pivot_dict:
            fig.add_hline(y=pivot_dict[lvl], line_color=colors.get(lvl,"gray"),
                          annotation_text=lvl, annotation_position="top left")

if show_rsi:
    fig.add_trace(go.Scatter(x=df.index,y=df[f"RSI{rsi_len}"], line_color="orange", name=f"RSI {rsi_len}"),row=2,col=1)
    fig.update_yaxes(range=[0,100], row=2,col=1)

lo, hi = df["Low"].min(), df["High"].max()
fig.update_yaxes(range=[lo-(hi-lo)*0.03, hi+(hi-lo)*0.03], row=1,col=1)
fig.update_xaxes(
    showgrid=False,
    rangebreaks=[dict(bounds=["sat","mon"]),
                 dict(pattern="hour", bounds=[10,24]),
                 dict(pattern="hour", bounds=[0,3.45])]
)
fig.update_yaxes(showgrid=False)
fig.update_layout(
    height=800 if rows==2 else 600,
    title=f"{symbol} — {interval_label}",
    dragmode="pan",
    xaxis_rangeslider_visible=False,   # slider removed
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
)

st.plotly_chart(fig, use_container_width=True)
