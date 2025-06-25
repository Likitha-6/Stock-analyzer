
# pages/3_Technical_Analysis.py
import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd

st.set_page_config(page_title="📈 Technical Analysis", layout="wide")
st.title("📈 Technical Analysis")

symbol = st.text_input("Enter NSE Symbol (e.g., RELIANCE):", "RELIANCE").upper()
interval = st.selectbox("Select Interval", ["5m", "15m", "30m", "1h", "4h", "1d", "30d"], index=5)
period = st.selectbox("Select Period", ["1d", "5d", "1mo", "3mo", "6mo", "1y"], index=2)

indicators = st.multiselect("Select Indicators", ["SMA", "EMA", "RSI", "Pivot Points"])

sma_len = ema_len = rsi_len = 14
if "SMA" in indicators:
    sma_len = st.slider("SMA Length", 5, 100, 20)
if "EMA" in indicators:
    ema_len = st.slider("EMA Length", 5, 100, 20)
if "RSI" in indicators:
    rsi_len = st.slider("RSI Length", 5, 50, 14)

pivot_levels = []
if "Pivot Points" in indicators:
    pivot_levels = st.multiselect("Select Pivot Levels", ["P", "R1", "R2", "S1", "S2"], default=["P", "R1", "S1"])

try:
    df = yf.download(f"{symbol}.NS", period=period, interval=interval, auto_adjust=True, progress=False)

    if df.empty or "Close" not in df.columns:
        st.error("⚠️ No valid data found for the given symbol.")
    else:
        df["SMA"] = df["Close"].rolling(sma_len).mean() if "SMA" in indicators else None
        df["EMA"] = df["Close"].ewm(span=ema_len, adjust=False).mean() if "EMA" in indicators else None

        if "RSI" in indicators:
            delta = df["Close"].diff()
            gain = (delta.where(delta > 0, 0)).rolling(rsi_len).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(rsi_len).mean()
            rs = gain / loss
            df["RSI"] = 100 - (100 / (1 + rs))

        fig = go.Figure()

        # Candlestick
        fig.add_trace(go.Candlestick(
            x=df.index,
            open=df["Open"],
            high=df["High"],
            low=df["Low"],
            close=df["Close"],
            name="Candlesticks"
        ))

        if "SMA" in indicators:
            fig.add_trace(go.Scatter(x=df.index, y=df["SMA"], mode="lines", name=f"SMA{sma_len}"))
        if "EMA" in indicators:
            fig.add_trace(go.Scatter(x=df.index, y=df["EMA"], mode="lines", name=f"EMA{ema_len}"))

        if "Pivot Points" in indicators and not df.empty:
            hlc = df.iloc[-1]
            pivot = (hlc["High"] + hlc["Low"] + hlc["Close"]) / 3
            r1 = 2 * pivot - hlc["Low"]
            s1 = 2 * pivot - hlc["High"]
            r2 = pivot + (hlc["High"] - hlc["Low"])
            s2 = pivot - (hlc["High"] - hlc["Low"])
            pivot_dict = {"P": pivot, "R1": r1, "R2": r2, "S1": s1, "S2": s2}
            for level in pivot_levels:
                fig.add_hline(y=pivot_dict[level], line_dash="solid", annotation_text=level)

        fig.update_layout(
            title=f"{symbol} – Technical Chart",
            xaxis_rangeslider_visible=False,
            template="plotly_white",
            xaxis=dict(showgrid=False),
            yaxis=dict(showgrid=False),
            height=600
        )

        st.plotly_chart(fig, use_container_width=True)

        if "RSI" in indicators:
            rsi_fig = go.Figure()
            rsi_fig.add_trace(go.Scatter(x=df.index, y=df["RSI"], mode="lines", name=f"RSI{rsi_len}"))
            rsi_fig.update_layout(title="RSI Indicator", height=300, template="plotly_white", yaxis=dict(showgrid=False))
            st.plotly_chart(rsi_fig, use_container_width=True)

except Exception as e:
    st.error(f"An error occurred: {e}")
