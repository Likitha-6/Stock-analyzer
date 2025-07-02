import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import pandas as pd

st.set_page_config(page_title="📈 Technical Chart", layout="wide")
st.title("📈 Indian Stock – Technical Analysis")

interval_mapping = {
    "5 minutes": "5m",
    "15 minutes": "15m",
    "1 hour": "60m",
    "4 hours": "240m",
    "1 day": "1d"
}

label = st.selectbox("Select Interval", list(interval_mapping.keys()), index=0)
interval = interval_mapping[label]

symbol = st.text_input("Enter NSE Symbol (e.g., INFY, RELIANCE):").upper().strip()

# Session state for period tracking
if "candle_days" not in st.session_state:
    st.session_state.candle_days = 1

# Adjust period based on interval
if interval == "1d":
    period = "3mo"
else:
    period = f"{st.session_state.candle_days}d"

# Button to increment days shown
if interval != "1d":
    if st.button("🔁 Load older candles"):
        st.session_state.candle_days += 1  # Don't rerun, just update

# Display how many days we're loading
if interval != "1d":
    st.caption(f"Showing: **{st.session_state.candle_days} day(s)** of data")

# Load and display chart
if symbol:
    try:
        df = yf.Ticker(symbol + ".NS").history(interval=interval, period=period)

        if df.empty:
            st.error("No data found.")
        else:
            df = df.reset_index()
            x_col = "Datetime" if "Datetime" in df.columns else "Date"

            df["x_label"] = df[x_col].dt.strftime("%d/%m %H:%M") if "m" in interval or "h" in interval else df[x_col].dt.strftime("%d/%m")

            fig = go.Figure()
            fig.add_trace(go.Candlestick(
                x=df["x_label"],
                open=df["Open"],
                high=df["High"],
                low=df["Low"],
                close=df["Close"],
                name="Price"
            ))

            fig.update_layout(
                title=f"{symbol}.NS – {label} Chart ({period})",
                xaxis_title="Date/Time",
                yaxis_title="Price",
                xaxis=dict(type="category", tickangle=-45),
                xaxis_rangeslider_visible=False,
                height=600
            )

            st.plotly_chart(fig, use_container_width=True)

    except Exception as e:
        st.error(f"Error: {e}")
