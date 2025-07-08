# app.py  – HOME (minimal)
import streamlit as st
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
Welcome to the Indian Stock Analyzer!  
Use the sidebar to navigate:

- **Fundamentals** – deep dive on a single stock  
- **Sector Browser** – explore industry groups  
- **Index Analysis** – view market indices and trends  
- **News** – curated headlines with sentiment  
""")
st.markdown("---")

# Dataset statistics
try:
    master_df = load_master()        # your master symbol list
    name_df   = load_name_lookup()   # symbol ↔ company-name mapping

    c1, c2, c3 = st.columns(3)
    c1.metric("Total Symbols",     f"{len(master_df):,}")
    c2.metric("Unique Sectors",    master_df["Big Sectors"].nunique())
    c3.metric("Unique Industries", master_df["Industry"].nunique())

except Exception as e:
    st.error(f"Error loading data: {e}")

st.markdown("---")
st.markdown("Built with **Streamlit**, **yfinance**, **TF-IDF**, and **FinBERT**")
