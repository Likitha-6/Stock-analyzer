# app.py  – HOME
# ──────────────────────────────────────────────────────────────
import streamlit as st
import pandas as pd
import plotly.express as px
from nsetools import Nse
from common.sql import load_master          # pulls from SQLite
from common.data import load_name_lookup    # if you still need the CSV helper

# Page-level config
st.set_page_config(
    page_title="🏠 Home",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ──────────────────────────────────────────────────────────────
# Header
# ──────────────────────────────────────────────────────────────
st.title("🏠 Indian Stock Analyzer – Home")

st.markdown(
    """
Welcome! Use the sidebar to navigate:

- **Fundamentals** – single-stock deep dive, peer comparison  
- **Sector Browser** – explore industries  
- **Index Analysis** – view market indices and trends  
- **News** – daily curated headlines with sentiment  
"""
)

st.markdown("---")

# ──────────────────────────────────────────────────────────────
# Quick dataset stats & Top Movers via nsetools
# ──────────────────────────────────────────────────────────────
try:
    # Load your master symbol list
    master_df = load_master()        # Symbol, Industry, Big Sectors, …
    name_df   = load_name_lookup()   # Symbol, Company Name

    # Snapshot metrics
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Symbols",    f"{len(master_df):,}")
    col2.metric("Unique Sectors",   master_df["Big Sectors"].nunique())
    col3.metric("Unique Industries",master_df["Industry"].nunique())

    # Initialize NSE client
    nse = Nse()

    # Fetch top gainers & losers
    raw_gainers = nse.get_top_gainers()[:5]
    raw_losers  = nse.get_top_losers()[:5]

    # Build DataFrames
    df_gainers = pd.DataFrame(raw_gainers)[["symbol", "ltp", "pChange"]]
    df_losers  = pd.DataFrame(raw_losers)[["symbol", "ltp", "pChange"]]

    df_gainers.columns = ["Symbol", "Last Price", "% Change"]
    df_losers.columns  = ["Symbol", "Last Price", "% Change"]

    # Display Top Movers
    st.markdown("### 📈 Top 5 Gainers & Losers (Past Session)")
    gcol, lcol = st.columns(2)
    gcol.dataframe(df_gainers, use_container_width=True, hide_index=True)
    lcol.dataframe(df_losers,  use_container_width=True, hide_index=True)

    # ─────────────────────────────────────────────────────────
    # Sector Distribution Pie Chart
    # ─────────────────────────────────────────────────────────
    st.markdown("### 📊 Sector Distribution")
    sector_counts = (
        master_df["Big Sectors"]
        .value_counts()
        .reset_index()
        .rename(columns={"index": "Sector", "Big Sectors": "Count"})
    )
    fig = px.pie(
        sector_counts,
        names="Sector",
        values="Count",
        title="Companies by Sector",
        hole=0.3
    )
    st.plotly_chart(fig, use_container_width=True)

except Exception as e:
    st.error(f"Unable to load dataset or fetch top movers: {e}")

# ──────────────────────────────────────────────────────────────
# Footer / links
# ──────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown(
    """
Built with **Streamlit**, **nsetools**, **yfinance**, **TF-IDF**, and **FinBERT** | Powered by real-time data updates
"""
)
