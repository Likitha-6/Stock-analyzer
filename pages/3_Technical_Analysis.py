import streamlit as st
from streamlit_lightweight_charts import Chart
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

        chart = Chart()
        chart.set(candlestick=[
            {
                "time": row["time"],
                "open": row["Open"],
                "high": row["High"],
                "low": row["Low"],
                "close": row["Close"]
            }
            for _, row in df.iterrows()
        ])
        chart.set(volume=[
            {
                "time": row["time"],
                "value": row["Volume"],
                "color": "green" if row["Close"] >= row["Open"] else "red"
            }
            for _, row in df.iterrows()
        ])
        st.components.v1.html(chart.render(), height=500)
