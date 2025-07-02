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
        df = yf.Ticker(symbol + ".NS").history(interval=interval, period=period)

        if df.empty:
            st.error("No data found.")
        else:
            df = df.reset_index()
            x_col = "Datetime" if "Datetime" in df.columns else "Date"

            # Format x-values as strings: "01/07 13:45" or "01/07"
            if "m" in interval or "h" in interval:
                df["x_label"] = df[x_col].dt.strftime("%d/%m %H:%M")
            else:
                df["x_label"] = df[x_col].dt.strftime("%d/%m")

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
                title=f"{symbol}.NS – {label} Chart",
                xaxis_title="Date/Time",
                yaxis_title="Price",
                xaxis=dict(
                    type="category",  # This trims non-trading gaps
                    tickangle=-45
                ),
                xaxis_rangeslider_visible=False,
                height=600
            )

            st.plotly_chart(fig, use_container_width=True)

    except Exception as e:
        st.error(f"Error: {e}")

