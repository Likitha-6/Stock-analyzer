import streamlit as st
from streamlit_lightweight_charts import renderLightweightCharts
import yfinance as yf
import pandas as pd

st.set_page_config(page_title="📉 Technical Analysis", layout="wide")
st.title("📉 Technical Analysis – TradingView-style")

symbol = st.text_input("Enter NSE Symbol (e.g., INFY, RELIANCE):").upper().strip()

if symbol:
    stock = yf.Ticker(symbol + ".NS")
    df = stock.history(period="3mo", interval="1d")

    if df.empty:
        st.error("No data available for this stock.")
    else:
        df = df.reset_index()
        df["time"] = df["Date"].dt.strftime("%Y-%m-%d")

        ohlc_data = [
            {
                "time": row["time"],
                "open": round(row["Open"], 2),
                "high": round(row["High"], 2),
                "low": round(row["Low"], 2),
                "close": round(row["Close"], 2)
            }
            for _, row in df.iterrows()
        ]

        volume_data = [
            {
                "time": row["time"],
                "value": int(row["Volume"]),
                "color": "green" if row["Close"] >= row["Open"] else "red"
            }
            for _, row in df.iterrows()
        ]

        chart_config = [
            {
                "type": "Candlestick",
                "data": ohlc_data
            },
            {
                "type": "Histogram",
                "data": volume_data,
                "options": {
                    "color": "rgba(76,175,80,0.5)",
                    "priceFormat": {"type": "volume"},
                    "priceScaleId": ""
                },
                "priceScale": {
                    "scaleMargins": {"top": 0.8, "bottom": 0}
                }
            }
        ]

        with st.container():
            renderLightweightCharts(chart_config)

