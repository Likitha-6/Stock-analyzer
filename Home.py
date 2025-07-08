# app.py  – HOME
# ──────────────────────────────────────────────────────────────
import streamlit as st
import pandas as pd
import plotly.express as px
import requests
from bs4 import BeautifulSoup
from common.sql import load_master
from common.data import load_name_lookup

# Page config
st.set_page_config(
    page_title="🏠 Home",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Header
st.title("🏠 Indian Stock Analyzer – Home")
st.markdown("""
Welcome! Use the sidebar to navigate:

- **Fundamentals** – single-stock deep dive, peer comparison  
- **Sector Browser** – explore industries  
- **Index Analysis** – view market indices and trends  
- **News** – daily curated headlines with sentiment  
""")
st.markdown("---")

def fetch_yahoo_table(url, rows=5):
    """Scrape first `rows` from the Yahoo Finance gainers/losers table."""
    headers = {"User-Agent": "Mozilla/5.0"}
    resp = requests.get(url, headers=headers, timeout=5)
    soup = BeautifulSoup(resp.text, "html.parser")
    table = soup.find("table", {"class": "W(100%)"})
    data = []
    if table and table.tbody:
        for tr in table.tbody.find_all("tr")[:rows]:
            cols = [td.get_text(strip=True) for td in tr.find_all("td")]
            # Yahoo columns: Symbol, Name, Price (Intraday), Change, %Change, Volume, ...
            symbol, _, price, _, pct, *_ = cols
            data.append((symbol, price, pct))
    return pd.DataFrame(data, columns=["Symbol", "Last Price", "% Change"])

try:
    # Load data
    master_df = load_master()
    name_df   = load_name_lookup()

    # Snapshot metrics
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Symbols",     f"{len(master_df):,}")
    c2.metric("Unique Sectors",    master_df["Big Sectors"].nunique())
    c3.metric("Unique Industries", master_df["Industry"].nunique())

    # Fetch top gainers & losers from Yahoo
    df_gainers = fetch_yahoo_table("https://finance.yahoo.com/gainers")
    df_losers  = fetch_yahoo_table("https://finance.yahoo.com/losers")

    # Display
    st.markdown("### 📈 Top 5 Gainers & Losers (Past Session)")
    col_g, col_l = st.columns(2)
    col_g.dataframe(df_gainers, use_container_width=True, hide_index=True)
    col_l.dataframe(df_losers,  use_container_width=True, hide_index=True)

    # Sector distribution
    st.markdown("### 📊 Sector Distribution")
    sector_counts = (
        master_df["Big Sectors"]
        .value_counts()
        .reset_index()
        .rename(columns={"index": "Sector", "Big Sectors": "Count"})
    )
    fig = px.pie(
        sector_counts, names="Sector", values="Count",
        title="Companies by Sector", hole=0.3
    )
    st.plotly_chart(fig, use_container_width=True)

except Exception as e:
    st.error(f"Error loading data or scraping top movers: {e}")

# Footer
st.markdown("---")
st.markdown(
    "Built with **Streamlit**, **requests**, **BeautifulSoup**, **yfinance**, **TF-IDF**, and **FinBERT**"
)
