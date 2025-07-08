import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from common.sql import load_master
from common.data import load_name_lookup

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

# Load Data
master_df = load_master()
name_df = load_name_lookup()

# Snapshot metrics
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Symbols", f"{len(master_df):,}")
col2.metric("Unique Sectors", master_df["Big Sectors"].nunique())
col3.metric("Unique Industries", master_df["Industry"].nunique())
# Compute top movers (using random returns as placeholder)
master_df["Return"] = np.random.randn(len(master_df))  # replace with actual returns
top_gainers = master_df.nlargest(5, "Return")[["Symbol", "Return"]]
top_losers = master_df.nsmallest(5, "Return")[["Symbol", "Return"]]
col4.metric("Top Gainer", f"{top_gainers.iloc[0]['Symbol']} ({top_gainers.iloc[0]['Return']:+.2%})")

st.markdown("### 📊 Sector Distribution")
sector_counts = master_df["Big Sectors"].value_counts().reset_index()
sector_counts.columns = ["Sector", "Count"]
fig = px.pie(sector_counts, names="Sector", values="Count", title="Companies by Sector")
st.plotly_chart(fig, use_container_width=True)

st.markdown("### 📈 Top 5 Gainers & Losers (Past Session)")
g_c, l_c = st.columns(2)
g_c.dataframe(top_gainers.rename(columns={"Return": "% Return"}).assign(**{"% Return": lambda df: df["% Return"].map("{:+.2%}".format)}), use_container_width=True)
l_c.dataframe(top_losers.rename(columns={"Return": "% Return"}).assign(**{"% Return": lambda df: df["% Return"].map("{:+.2%}".format)}), use_container_width=True)

st.markdown("---")
st.markdown("Built with **Streamlit**, **yfinance**, **TF-IDF**, and **FinBERT** | Powered by real-time data updates")

