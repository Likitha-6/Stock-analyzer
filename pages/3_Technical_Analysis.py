import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go

from common.data import load_name_lookup

# ─────────────────────────────
# Page config
# ─────────────────────────────
st.set_page_config(page_title="📉 Technical Analysis", page_icon="📊", layout="wide")
st.title("📉 Technical Analysis – Candlestick Chart")

# ─────────────────────────────
# Load stock names
# ─────────────────────────────
name_df = load_name_lookup()
symbols = name_df["Symbol"].dropna().unique()
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
        opts = matches.apply(lambda r: f"{r['Symbol']} – {r['Company Name']}", axis=1)
        chosen = st.selectbox("Select company", opts.tolist())
        chosen_sym = chosen.split(" – ")[0]

if not chosen_sym:
    st.stop()

# ─────────────────────────────
# Load and plot data
# ─────────────────────────────
st.markdown("---")
st.subheader(f"🕯️ Candlestick Chart – {chosen_sym}")

try:
    df = yf.download(f"{chosen_sym}.NS", period="6mo", interval="1d")

    if df.empty:
        st.warning("No price data available for this stock.")
        st.stop()

    fig = go.Figure(data=[
        go.Candlestick(
            x=df.index,
            open=df['Open'],
            high=df['High'],
            low=df['Low'],
            close=df['Close'],
            name="Price"
        )
    ])

    fig.update_layout(
        xaxis_title="Date",
        yaxis_title="Price (INR)",
        xaxis_rangeslider_visible=False,
        height=600
    )

    st.plotly_chart(fig, use_container_width=True)

except Exception as e:
    st.error(f"Failed to fetch or display data: {e}")

