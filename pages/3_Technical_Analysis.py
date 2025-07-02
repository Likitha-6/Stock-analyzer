import streamlit as st
import yfinance as yf
import plotly.graph_objects as go

st.set_page_config(page_title="📈 Technical Chart", layout="wide")
st.title("📈 Indian Stock – Technical Analysis")

# ─────────────────────────────
# Interval Dropdown
# ─────────────────────────────
interval_mapping = {
    "5 minutes": ("5m", "1d"),
    "15 minutes": ("15m", "5d"),
    "1 hour": ("60m", "7d"),
    "4 hours": ("240m", "10d"),
    "1 day": ("1d", "3mo")
}

label = st.selectbox("Select Interval", list(interval_mapping.keys()), index=4)
interval, period = interval_mapping[label]

# ─────────────────────────────
# Symbol Input
# ─────────────────────────────
symbol = st.text_input("Enter NSE Symbol (e.g., INFY, RELIANCE):").upper().strip()

# ─────────────────────────────
# Data Fetch & Chart Display
# ─────────────────────────────
if symbol:
    try:
        data = yf.Ticker(symbol + ".NS").history(interval=interval, period=period)

        if data.empty:
            st.error("No data found.")
        else:
            fig = go.Figure()

            fig.add_trace(go.Candlestick(
                x=data.index.astype(str),  # convert to string to prevent time gaps
                open=data['Open'],
                high=data['High'],
                low=data['Low'],
                close=data['Close'],
                name="Price"
            ))

            fig.update_layout(
                title=f"{symbol}.NS – {label} Chart",
                xaxis_title="Time",
                yaxis_title="Price",
                xaxis_rangeslider_visible=False,
                xaxis=dict(type="category"),  # removes time gaps
                height=600
            )

            st.plotly_chart(fig, use_container_width=True)

    except Exception as e:
        st.error(f"Error: {e}")
