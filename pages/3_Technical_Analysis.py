import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(page_title="📈 Technical Analysis", layout="wide")
st.title("📈 Technical Analysis")

symbol = st.text_input("Enter NSE Symbol", "RELIANCE")
period = st.selectbox("Select period", ["1mo", "3mo", "6mo", "1y", "3y", "5y", "max"], index=2)

if symbol:
    df = yf.download(f"{symbol}.NS", period=period, interval="1d")

    if df.empty:
        st.warning("⚠️ No data available for this symbol.")
    else:
        expected_cols = ["Open", "High", "Low", "Close", "Volume"]
        missing_cols = [col for col in expected_cols if col not in df.columns]

        if missing_cols:
            st.error(f"❌ Missing columns in data: {missing_cols}")
            st.stop()

        df = df.dropna(subset=expected_cols)

            # Compute SMA for demo
        df["SMA20"] = df["Close"].rolling(window=20).mean()

            # Create figure with candlesticks and volume
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                                specs=[[{"secondary_y": False}],
                                       [{"secondary_y": False}]],
                                row_heights=[0.7, 0.3],
                                vertical_spacing=0.05)

        fig.add_trace(go.Candlestick(
            x=df.index,
            open=df["Open"],
            high=df["High"],
            low=df["Low"],
            close=df["Close"],
            name="Candlesticks"
        ), row=1, col=1)

        fig.add_trace(go.Scatter(
            x=df.index,
            y=df["SMA20"],
            mode="lines",
            name="SMA 20",
            line=dict(width=1.5, dash="dot")
        ), row=1, col=1)

        fig.add_trace(go.Bar(
            x=df.index,
            y=df["Volume"],
            name="Volume",
            marker=dict(color="lightgray")
        ), row=2, col=1)

        fig.update_layout(height=700, title=f"{symbol.upper()} Technical Chart", xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)
