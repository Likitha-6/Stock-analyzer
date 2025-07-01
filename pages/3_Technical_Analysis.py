import streamlit as st
from streamlit_lightweight_charts import Chart
import yfinance as yf
import pandas as pd
from common.data import load_name_lookup

# ─────────────────────────────
# Page config
# ─────────────────────────────
st.set_page_config(page_title="📉 Technical Analysis", page_icon="📊", layout="wide")
st.title("📉 Technical Analysis – TradingView-style Chart")

# ─────────────────────────────
# Load stock names
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
        chosen_sym = st.selectbox("Select Stock", matches["Symbol"] + " - " + matches["Company Name"])
        chosen_sym = chosen_sym.split(" - ")[0]

# ─────────────────────────────
# Fetch and show chart
# ─────────────────────────────
if chosen_sym:
    stock = yf.Ticker(chosen_sym + ".NS")
    df = stock.history(period="3mo", interval="1d")

    if df.empty:
        st.error("No data available for this stock.")
    else:
        df = df.reset_index()
        df["time"] = df["Date"].dt.strftime("%Y-%m-%d")
        chart_data = [
            {
                "time": row["time"],
                "open": row["Open"],
                "high": row["High"],
                "low": row["Low"],
                "close": row["Close"],
            }
            for _, row in df.iterrows()
        ]

        volume_data = [
            {
                "time": row["time"],
                "value": row["Volume"],
                "color": "green" if row["Close"] >= row["Open"] else "red",
            }
            for _, row in df.iterrows()
        ]

        st.subheader(f"📊 {symbol2name.get(chosen_sym, chosen_sym)} – {chosen_sym}.NS")
        chart = Chart()
        chart.set(candlestick=chart_data)
        chart.set(volume=volume_data)
        st.components.v1.html(chart.render(), height=500)

