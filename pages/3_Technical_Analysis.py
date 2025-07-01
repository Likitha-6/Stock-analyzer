import streamlit as st
from streamlit_lightweight_charts import renderLightweightCharts
import yfinance as yf
import pandas as pd
from common.data import load_name_lookup  # Make sure this exists and returns a DataFrame with 'Symbol' and 'Company Name'

st.set_page_config(page_title="📉 Technical Analysis", page_icon="📊", layout="wide")
st.title("📉 Technical Analysis – TradingView-style Chart")

# ─────────────────────────────
# Load stock list
# ─────────────────────────────
name_df = load_name_lookup()
symbol2name = dict(zip(name_df["Symbol"], name_df["Company Name"]))

# ─────────────────────────────
# Symbol search
# ─────────────────────────────
query = st.text_input("Search by symbol or company name").strip()
chosen_sym = None

if query:
    mask = (
        name_df["Symbol"].str.contains(query, case=False, na=False) |
        name_df["Company Name"].str.contains(query, case=False, na=False)
    )
    matches = name_df[mask]
    if matches.empty:
        st.warning("No match found.")
    else:
        chosen_option = st.selectbox(
            "Select Stock",
            matches["Symbol"] + " - " + matches["Company Name"]
        )
        chosen_sym = chosen_option.split(" - ")[0]

# ─────────────────────────────
# Chart Rendering
# ─────────────────────────────
if chosen_sym:
    stock = yf.Ticker(chosen_sym + ".NS")
    df = stock.history(period="3mo", interval="1d")

    if df.empty:
        st.error("No data available for this stock.")
    else:
        df = df.reset_index()
        df["time"] = df["Date"].dt.strftime("%Y-%m-%d")

        ohlc = [
            {
                "time": row["time"],
                "open": row["Open"],
                "high": row["High"],
                "low": row["Low"],
                "close": row["Close"]
            }
            for _, row in df.iterrows()
        ]

        volume = [
            {
                "time": row["time"],
                "value": row["Volume"],
                "color": "green" if row["Close"] >= row["Open"] else "red"
            }
            for _, row in df.iterrows()
        ]

        chart_config = [
            {
                "type": "Candlestick",
                "data": ohlc,
            },
            {
                "type": "Histogram",
                "data": volume,
                "options": {
                    "color": "rgba(0,150,136,0.5)",
                    "priceFormat": {"type": "volume"},
                    "priceScaleId": "",
                },
                "priceScale": {
                    "scaleMargins": {
                        "top": 0.8,
                        "bottom": 0,
                    },
                },
            }
        ]

        st.subheader(f"📊 {symbol2name.get(chosen_sym, chosen_sym)} – {chosen_sym}.NS")
        renderLightweightCharts(chart_config, height=500)
