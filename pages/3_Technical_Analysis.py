# pages/3_Technical_Analysis.py
# ---------------------------------------------------------------
# Interactive Technical-Analysis dashboard (Plotly + Streamlit)
# Shows candlesticks, SMA/EMA, volume, RSI & MACD.
# ---------------------------------------------------------------
import streamlit as st
import yfinance as yf
import pandas as pd
from plotly.subplots import make_subplots
import plotly.graph_objects as go

# ─────────────────── Page & sidebar ────────────────────────────
st.set_page_config(page_title="📉 Technical Analysis", page_icon="📉", layout="wide")
st.title("📉 Technical Analysis – NSE stocks")

symbol = st.text_input("Enter NSE Symbol", "RELIANCE").strip().upper()
period = st.selectbox("Select period",
                      ["3mo", "6mo", "1y", "2y", "5y", "max"],
                      index=1)

# ─────────────────── Fetch data ────────────────────────────────
if symbol:
    df = yf.download(f"{symbol}.NS", period=period, interval="1d")
    if df.empty:
        st.error("⚠️ No data returned. Check the symbol or choose a longer period.")
        st.stop()

    # yfinance sometimes returns a MultiIndex (if multiple tickers). Flatten it.
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(-1)

    req_cols = ["Open", "High", "Low", "Close", "Volume"]
    missing  = [c for c in req_cols if c not in df.columns]
    if missing:
        st.error(f"⚠️ Data missing columns: {missing}")
        st.write(df.head())
        st.stop()

    df = df.dropna(subset=req_cols)

    # ──────────── Technical Indicators ─────────────────────────
    df["SMA20"] = df["Close"].rolling(20).mean()
    df["SMA50"] = df["Close"].rolling(50).mean()

    # RSI
    delta = df["Close"].diff()
    gain  = delta.clip(lower=0).rolling(14).mean()
    loss  = (-delta.clip(upper=0)).rolling(14).mean()
    rs    = gain / loss
    df["RSI"] = 100 - (100 / (1 + rs))

    # MACD
    exp12 = df["Close"].ewm(span=12, adjust=False).mean()
    exp26 = df["Close"].ewm(span=26, adjust=False).mean()
    df["MACD"]   = exp12 - exp26
    df["Signal"] = df["MACD"].ewm(span=9, adjust=False).mean()
    df["Hist"]   = df["MACD"] - df["Signal"]

    # ──────────── Plotly figure with subplots ──────────────────
    fig = make_subplots(
        rows=3, cols=1, shared_xaxes=True,
        row_heights=[0.55, 0.15, 0.30], vertical_spacing=0.03,
        specs=[[{"secondary_y": True}], [{}], [{}]],
        subplot_titles=(f"{symbol} – Candlestick with SMA20/50 & Volume",
                        "RSI (14-day)",
                        "MACD")
    )

    # 1️⃣ Candlesticks
    fig.add_trace(go.Candlestick(
        x=df.index, open=df["Open"], high=df["High"],
        low=df["Low"], close=df["Close"],
        name="OHLC",
        increasing_line_color="#26a69a",
        decreasing_line_color="#ef5350"
    ), row=1, col=1, secondary_y=False)

    # SMA20 & SMA50
    fig.add_trace(go.Scatter(x=df.index, y=df["SMA20"],
                             mode="lines", name="SMA 20",
                             line=dict(width=1, color="orange")),
                  row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df["SMA50"],
                             mode="lines", name="SMA 50",
                             line=dict(width=1, color="blue")),
                  row=1, col=1)

    # Volume (secondary y on first row)
    fig.add_trace(go.Bar(x=df.index, y=df["Volume"],
                         name="Volume",
                         marker_color="lightgray", opacity=0.4),
                  row=1, col=1, secondary_y=True)

    # 2️⃣ RSI
    fig.add_trace(go.Scatter(x=df.index, y=df["RSI"],
                             mode="lines", name="RSI",
                             line_color="purple"),
                  row=2, col=1)
    fig.add_hline(y=70, line_dash="dash", line_color="red", row=2, col=1)
    fig.add_hline(y=30, line_dash="dash", line_color="green", row=2, col=1)

    # 3️⃣ MACD & signal + histogram
    fig.add_trace(go.Bar(x=df.index, y=df["Hist"],
                         name="Hist", marker_color="gray"),
                  row=3, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df["MACD"],
                             name="MACD", line_color="blue"),
                  row=3, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df["Signal"],
                             name="Signal", line_color="orange"),
                  row=3, col=1)

    # ──────────── Layout tweaks ───────────────────────────────
    fig.update_layout(
        height=850,
        xaxis_rangeslider_visible=False,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=40, r=20, t=60, b=40)
    )
    fig.update_yaxes(title_text="Price",  row=1, col=1, secondary_y=False)
    fig.update_yaxes(title_text="Volume", row=1, col=1, secondary_y=True)
    fig.update_yaxes(title_text="RSI",    row=2, col=1)
    fig.update_yaxes(title_text="MACD",   row=3, col=1)

    st.plotly_chart(fig, use_container_width=True)
