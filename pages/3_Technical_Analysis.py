import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import pandas as pd

st.set_page_config(page_title="📈 Technical Chart", layout="wide")
st.title("📈 Indian Stock – Technical Analysis")

interval_mapping = {
    "5 minutes": ("5m", "1d"),
    "15 minutes": ("15m", "5d"),
    "1 hour": ("60m", "7d"),
    "4 hours": ("240m", "10d"),
    "1 day": ("1d", "3mo")
}

label = st.selectbox("Select Interval", list(interval_mapping.keys()), index=4)
interval, period = interval_mapping[label]

symbol = st.text_input("Enter NSE Symbol (e.g., INFY, RELIANCE):").upper().strip()

if symbol:
    try:
        data = yf.Ticker(symbol + ".NS").history(interval=interval, period=period)

        if data.empty:
            st.error("No data found.")
        else:
            # Format X-axis labels to DD/MM
            data = data.reset_index()
            data["label"] = data["Datetime" if "Datetime" in data.columns else "Date"].dt.strftime("%d/%m")

            fig = go.Figure()

            fig.add_trace(go.Candlestick(
                x=data["label"],  # Shortened date format
                open=data['Open'],
                high=data['High'],
                low=data['Low'],
                close=data['Close'],
                name="Price"
            ))

            fig.update_layout(
                title=f"{symbol}.NS – {label} Chart",
                xaxis_title="Date",
                yaxis_title="Price",
                xaxis_rangeslider_visible=False,
                height=600
            )

            st.plotly_chart(fig, use_container_width=True)

    except Exception as e:
        st.error(f"Error: {e}")

