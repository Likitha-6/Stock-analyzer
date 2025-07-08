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

# Helper: scrape top movers from Moneycontrol
def fetch_movers(url, max_rows=5):
    resp = requests.get(url, headers={"User-Agent":"Mozilla/5.0"})
    soup = BeautifulSoup(resp.text, "html.parser")
    table = soup.find("table", {"class": "tbldata14"})
    rows = table.tbody.find_all("tr")[:max_rows]
    data = []
    for tr in rows:
        cols = [td.get_text(strip=True) for td in tr.find_all("td")]
        # cols: [#, Symbol, LTP, Change, %Change, Volume]
        symbol    = cols[1]
        price      = cols[2]
        pct_change = cols[4]
        data.append((symbol, price, pct_change))
    return pd.DataFrame(data, columns=["Symbol", "Last Price", "% Change"])

try:
    # Load master data
    master_df = load_master()
    name_df   = load_name_lookup()

    # Snapshot metrics
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Symbols",     f"{len(master_df):,}")
    c2.metric("Unique Sectors",    master_df["Big Sectors"].nunique())
    c3.metric("Unique Industries", master_df["Industry"].nunique())

    # Fetch top 5 gainers & losers
    gainers_url = "https://www.moneycontrol.com/stocks/marketstats/nsegainer/index.html"
    losers_url  = "https://www.moneycontrol.com/stocks/marketstats/nseloser/index.html"

    df_gainers = fetch_movers(gainers_url, max_rows=5)
    df_losers  = fetch_movers(losers_url,  max_rows=5)

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
        .rename(columns={"index":"Sector","Big Sectors":"Count"})
    )
    fig = px.pie(
        sector_counts, names="Sector", values="Count",
        title="Companies by Sector", hole=0.3
    )
    st.plotly_chart(fig, use_container_width=True)

except Exception as e:
    st.error(f"Error loading data or scraping movers: {e}")

# Footer
st.markdown("---")
st.markdown(
    "Built with **Streamlit**, **requests**, **BeautifulSoup**, **yfinance**, **TF-IDF**, and **FinBERT**"
)
