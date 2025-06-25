import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go

# ─────────────────────────────────────────────────────────────
# Page Setup
# ─────────────────────────────────────────────────────────────
st.set_page_config(page_title="📉 Technical Analysis", layout="wide")
st.title("📉 Technical Analysis")

# ─────────────────────────────────────────────────────────────
# 1️⃣ Ticker and Interval Selection
# ─────────────────────────────────────────────────────────────
symbol = st.text_input("Enter NSE Ticker Symbol (e.g., RELIANCE)", "RELIANCE.NS")

interval_map = {
    "5m": "5m", "15m": "15m", "30m": "30m", "1h": "60m", "4h": "240m", "1d": "1d"
}
selected_interval = st.selectbox("Select Interval", list(interval_map.keys()), index=2)
interval = interval_map[selected_interval]

period = "5d" if interval != "1d" else "30d"

# ─────────────────────────────────────────────────────────────
# 2️⃣ Indicator Selection
# ─────────────────────────────────────────────────────────────
indicators = st.multiselect("Indicators", ["SMA", "EMA", "RSI", "Pivot Points"], default=["SMA", "Pivot Points"])
sma_len = st.slider("SMA Length", 5, 50, 20) if "SMA" in indicators else None
ema_len = st.slider("EMA Length", 5, 50, 20) if "EMA" in indicators else None
pivot_type = st.selectbox("Pivot Type", ["classic", "fibonacci", "woodie", "camarilla"]) if "Pivot Points" in indicators else None

# ─────────────────────────────────────────────────────────────
# 3️⃣ Fetch Data
# ─────────────────────────────────────────────────────────────
try:
    df = yf.download(symbol, period=period, interval=interval, progress=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.droplevel(0)

    expected_cols = ["Open", "High", "Low", "Close"]
    if df.empty or not all(col in df.columns for col in expected_cols):
        st.warning("❌ Missing OHLC data.")
        st.dataframe(df)
    else:
        # ────── Indicators ──────
        if "SMA" in indicators:
            df["SMA"] = df["Close"].rolling(sma_len).mean()
        if "EMA" in indicators:
            df["EMA"] = df["Close"].ewm(span=ema_len, adjust=False).mean()
        if "RSI" in indicators:
            delta = df["Close"].diff()
            gain = delta.clip(lower=0)
            loss = -delta.clip(upper=0)
            avg_gain = gain.rolling(14).mean()
            avg_loss = loss.rolling(14).mean()
            rs = avg_gain / avg_loss
            df["RSI"] = 100 - (100 / (1 + rs))

        # ────── Chart ──────
        fig = go.Figure()
        fig.add_trace(go.Candlestick(
            x=df.index, open=df["Open"], high=df["High"],
            low=df["Low"], close=df["Close"], name="Price"
        ))

        if "SMA" in indicators:
            fig.add_trace(go.Scatter(x=df.index, y=df["SMA"], mode="lines", name=f"SMA {sma_len}"))
        if "EMA" in indicators:
            fig.add_trace(go.Scatter(x=df.index, y=df["EMA"], mode="lines", name=f"EMA {ema_len}"))

        if "Pivot Points" in indicators:
            recent = df.iloc[-1]
            high, low, close = recent["High"], recent["Low"], recent["Close"]
            pp = (high + low + close) / 3
            r1, s1 = 2 * pp - low, 2 * pp - high
            fig.add_hline(y=pp, line_color="gray", annotation_text="Pivot")
            fig.add_hline(y=r1, line_color="green", annotation_text="R1")
            fig.add_hline(y=s1, line_color="red", annotation_text="S1")

        fig.update_layout(
            title=f"{symbol} ({interval})",
            xaxis_rangeslider_visible=False,
            xaxis=dict(showgrid=False),
            yaxis=dict(showgrid=False),
        )

        st.plotly_chart(fig, use_container_width=True)

        if "RSI" in indicators:
            st.subheader("📉 RSI")
            st.line_chart(df["RSI"])

except Exception as e:
    st.error(f"⚠️ An error occurred: {e}")
