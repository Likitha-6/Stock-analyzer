import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from common.data import load_name_lookup

# ────────────────────────────────────────
# Page config
# ────────────────────────────────────────
st.set_page_config(page_title="📉 Technical Analysis", page_icon="📈", layout="wide")
st.title("📉 Technical Analysis – Candlestick Chart")

# ────────────────────────────────────────
# Load stock names
# ────────────────────────────────────────
name_df = load_name_lookup()
symbols = name_df["Symbol"].dropna().unique()
symbol2name = dict(zip(name_df["Symbol"], name_df["Company Name"]))

# ────────────────────────────────────────
# Symbol search
# ────────────────────────────────────────
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

# ────────────────────────────────────────
# Load and plot data
# ────────────────────────────────────────
st.markdown("---")
st.subheader(f"🔧 Candlestick Chart – {chosen_sym}")

symbol = chosen_sym.strip().upper()
yf_symbol = f"{symbol}.NS"

try:
    df = yf.download(yf_symbol, period="6mo", interval="1d")

    if df.empty or df.isna().all().all():
        st.warning("No price data available or symbol not valid on Yahoo Finance.")
        st.stop()

    df.reset_index(inplace=True)
    df['Date'] = pd.to_datetime(df['Date'])

    fig = make_subplots(
        rows=2, cols=1, shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=[0.7, 0.3],
        subplot_titles=("Price Candlesticks", "Volume")
    )

    fig.add_trace(go.Candlestick(
        x=df['Date'],
        open=df['Open'],
        high=df['High'],
        low=df['Low'],
        close=df['Close'],
        name='Candles',
        increasing_line_color='green',
        decreasing_line_color='red',
        line_width=1
    ), row=1, col=1)

    fig.add_trace(go.Bar(
        x=df['Date'],
        y=df['Volume'],
        marker_color='rgba(0, 100, 255, 0.4)',
        name='Volume'
    ), row=2, col=1)

    fig.update_layout(
        height=700,
        xaxis_rangeslider_visible=False,
        plot_bgcolor='#f5f5f5',
        paper_bgcolor='#f5f5f5',
        hovermode='x unified',
        xaxis=dict(showgrid=True, gridcolor='lightgray'),
        yaxis=dict(showgrid=True, gridcolor='lightgray'),
        margin=dict(l=20, r=20, t=40, b=30)
    )

    st.plotly_chart(fig, use_container_width=True)

except Exception as e:
    st.error(f"Failed to fetch or display data: {e}")
