
import pandas as pd
import streamlit as st

@st.cache_data(ttl=60*60*6)
def load_master():
    return pd.read_csv("data/nse_stocks_with industries.csv")

@st.cache_data(ttl=60*60*6)
def load_name_lookup():
    return pd.read_csv("data/nse_stocks_.csv")
