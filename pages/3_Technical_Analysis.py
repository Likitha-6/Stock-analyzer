import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# ── Page setup ──
st.set_page_config(page_title="📉 Technical Analysis", page_icon="📉")
st.title("📉 Technical Analysis")

# ── User input ──
symbol = st.text_input("Enter NSE Symbol (e.g. RELIANCE)", "RELIANCE")
period = st.selectbox("Select period", ["1mo", "3mo", "6mo", "1y", "3y", "5y", "max"], index=2)

if symbol:
    df = yf.download(f"{symbol}.NS", period=period, interval="1d")

    if df.empty:
        st.error("⚠️ No data returned for the given symbol and period.")
        st.stop()

    # Ensure required columns exist
    expected_cols = ["Open", "High", "Low", "Close", "Volume"]
    if not all(col in df.columns for col in expected_cols):
        st.error(f"⚠️ Missing expected columns in data: {df.columns.tolist()}")
        st.stop()

    df = df.dropna(subset=expected_cols)
    df["SMA20"] = df["Close"].rolling(20).mean()

    st.success("✅ Data loaded successfully.")
    st.write(df.head())


# ── Create figure with secondary y-axis ──
fig = make_subplots(
    rows=2, cols=1,
    shared_xaxes=True,
    vertical_spacing=0.05,
    row_heights=[0.7, 0.3],
    specs=[[{"secondary_y": True}], [{}]],
    subplot_titles=["Candlestick Chart with SMA", "Volume"]
)

# ── Candlestick chart ──
fig.add_trace(go.Candlestick(
    x=df.index,
    open=df["Open"],
    high=df["High"],
    low=df["Low"],
    close=df["Close"],
    name="OHLC",
    increasing_line_color="#26a69a",
    decreasing_line_color="#ef5350"
), row=1, col=1, secondary_y=False)

# ── SMA line ──
fig.add_trace(go.Scatter(
    x=df.index, y=df["SMA20"],
    name="SMA20", mode="lines",
    line=dict(color="orange", width=1)
), row=1, col=1, secondary_y=False)

# ── Volume bars ──
fig.add_trace(go.Bar(
    x=df.index, y=df["Volume"],
    name="Volume", marker_color="lightblue"
), row=2, col=1)

# ── Layout ──
fig.update_layout(
    height=700,
    xaxis_rangeslider_visible=False,
    showlegend=False,
    margin=dict(t=50, b=40),
)

st.plotly_chart(fig, use_container_width=True)
