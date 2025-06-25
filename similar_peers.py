"""similar_peers.py
--------------------------------------------------------------------
Industry‑scoped peer selection using **Yahoo Finance longBusinessSummary**.

* Fetches every company description in the target’s industry on first
  call (can be slow; cached for 12 h via Streamlit).
* No external API keys, no FMP – 100 % yfinance.
"""
from __future__ import annotations

from typing import List
import pandas as pd
import yfinance as yf
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# ------------------------------------------------------------------ #
# Streamlit‑aware caching                                             
# ------------------------------------------------------------------ #
try:
    import streamlit as st
    _cache_data = st.cache_data(ttl=12 * 60 * 60, show_spinner=True)
except ModuleNotFoundError:
    def _cache_data(func):
        return func

# ------------------------------------------------------------------ #
# Yahoo Finance description fetch                                     
# ------------------------------------------------------------------ #

def _get_yf_description(sym: str) -> str:
    """Return the company's longBusinessSummary via yfinance."""
    try:
        return yf.Ticker(f"{sym}.NS").info.get("longBusinessSummary", "")
    except Exception:
        return ""

# ------------------------------------------------------------------ #
# Batch‑fetch descriptions for one industry                           
# ------------------------------------------------------------------ #
@_cache_data
def _fetch_industry_descriptions(symbols: List[str]) -> pd.DataFrame:
    rows = [
        {"Symbol": sym, "Description": _get_yf_description(sym)}
        for sym in symbols
    ]
    return pd.DataFrame(rows)

# ------------------------------------------------------------------ #
# Public API                                                          
# ------------------------------------------------------------------ #

def similar_description_peers(
    target_sym: str,
    master_df: pd.DataFrame,
    k: int = 10,
    min_length: int = 30,
) -> List[str]:
    """Return up to *k* peers in the same industry ranked by description similarity.

    • Fetches every description in the industry on first call.
    • Uses TF‑IDF + cosine similarity.
    • Cached for 12 hours to avoid repeated yfinance calls.
    """
    try:
        industry = master_df.loc[master_df["Symbol"] == target_sym, "Industry"].iat[0]
    except IndexError:
        return []

    peer_syms = master_df.loc[master_df["Industry"] == industry, "Symbol"].tolist()
    if target_sym in peer_syms:
        peer_syms.remove(target_sym)

    desc_df = _fetch_industry_descriptions([target_sym] + peer_syms)

    # Drop rows with very short / empty descriptions
    desc_df = desc_df[desc_df["Description"].str.len() >= min_length]
    if desc_df.empty or target_sym not in desc_df["Symbol"].values:
        return []

    tfidf = TfidfVectorizer(stop_words="english", max_features=10_000)
    X     = tfidf.fit_transform(desc_df["Description"].fillna(""))

    idx_target = desc_df.index[desc_df["Symbol"] == target_sym][0]
    sims       = cosine_similarity(X[idx_target], X).flatten()
    ranks      = sims.argsort()[::-1].tolist()
    ranks.remove(idx_target)

    return desc_df.iloc[ranks][:k]["Symbol"].tolist()

# ------------------------------------------------------------------ #
# Pretty label helper                                                 
# ------------------------------------------------------------------ #

def make_peer_labels(master_df: pd.DataFrame) -> dict[str, str]:
    if "Company Name" not in master_df.columns:
        return {row.Symbol: row.Symbol for _, row in master_df.iterrows()}

    return {
        f"{row['Company Name']} ({row['Symbol']})": row["Symbol"]
        for _, row in master_df.dropna(subset=["Company Name"]).iterrows()
    }

__all__ = [
    "similar_description_peers",
    "make_peer_labels",
]
