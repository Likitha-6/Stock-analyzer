import streamlit as st, yfinance as yf, pandas as pd, numpy as np
def make_peer_labels(name_df:pd.DataFrame):
    return {f"{r['Symbol']} – {r['Company Name'] or 'Unknown'}":r['Symbol'] for _,r in name_df.iterrows()}
@st.cache_data(ttl=60*60*12)
def _desc(sym):
    try: return yf.Ticker(f"{sym}.NS").info.get("longBusinessSummary","")
    except: return ""
@st.cache_data(ttl=60*60*12)
def similar_description_peers(symbol:str, master_df:pd.DataFrame, k:int=5):
    inds=master_df.loc[master_df['Symbol']==symbol,'Industry']
    if inds.empty: return []
    industry=inds.iat[0]
    peers=[s for s in master_df.loc[master_df['Industry']==industry,'Symbol'] if s!=symbol]
    return peers[:k]