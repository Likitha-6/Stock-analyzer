# app.py  – HOME
# ──────────────────────────────────────────────────────────────
import streamlit as st
import pandas as pd

from common.sql import load_master          # ← now pulls from SQLite
from common.data import load_name_lookup    # (if you still need the CSV helper)


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

* **Fundamentals** – single-stock deep dive, peer comparison  
* **Sector Browser** – explore industries
"""
)

st.markdown("---")

# ──────────────────────────────────────────────────────────────
# Quick dataset stats
# ──────────────────────────────────────────────────────────────
try:
    master_df = load_master()        # Symbol, Industry, Big Sectors, …
    name_df   = load_name_lookup()   # Symbol, Company Name

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Symbols", f"{len(master_df):,}")
    col2.metric("Unique Sectors", master_df["Big Sectors"].nunique())
    col3.metric("Unique Industries", master_df["Industry"].nunique())

    #st.markdown("### 📋 Sample of dataset (first 10 rows)")
    #st.dataframe(master_df.head(10), use_container_width=True)

except Exception as e:
    st.error(f"Unable to load dataset: {e}")

# ──────────────────────────────────────────────────────────────
# Footer / links
# ──────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown(
    """
Built with **Streamlit**, **yfinance**, and a sprinkle of TF-IDF magic  

"""
)
