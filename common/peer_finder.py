
"""Peer finder limited to same industry with robust safety checks."""
from __future__ import annotations
import pandas as pd
import yfinance as yf
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# In‑memory cache for fetched summaries
_DESC_CACHE: dict[str, str] = {}

def _get_description(sym: str) -> str:
    """Fetch and memoize the company's longBusinessSummary."""
    if sym in _DESC_CACHE:
        return _DESC_CACHE[sym]
    try:
        info = yf.Ticker(f"{sym}.NS").info
        desc = info.get("longBusinessSummary", "")
    except Exception:
        desc = ""
    _DESC_CACHE[sym] = desc
    return desc

def _ensure_descriptions(df: pd.DataFrame) -> pd.DataFrame:
    """Guarantee df has a non‑null 'Description' column."""
    df = df.copy()
    if "Description" not in df.columns:
        df["Description"] = ""
    missing = df["Description"].isna() | (df["Description"].astype(str).str.strip() == "")
    if missing.any():
        df.loc[missing, "Description"] = df.loc[missing, "Symbol"].apply(_get_description)
    return df

def _vectorizer_and_matrix(desc_series: pd.Series):
    """Return TF‑IDF vectorizer and matrix or raise ValueError if insufficient data."""
    desc_series = desc_series.fillna("").astype(str)
    # Drop empty strings
    desc_series = desc_series[desc_series.str.strip() != ""]
    if len(desc_series) < 2:
        raise ValueError("Not enough valid descriptions")
    tfidf = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), min_df=2)
    matrix = tfidf.fit_transform(desc_series)
    return tfidf, matrix

def top_peers(symbol: str, df: pd.DataFrame, k: int = 5) -> pd.DataFrame:
    """Return top‑k peers within the same industry (fallback empty DataFrame)."""
    if "Industry" not in df.columns:
        return pd.DataFrame(columns=["Symbol", "Company Name", "Similarity"])
    try:
        industry = df.loc[df["Symbol"] == symbol, "Industry"].values[0]
    except IndexError:
        return pd.DataFrame(columns=["Symbol", "Company Name", "Similarity"])
    subset = df[df["Industry"] == industry]
    subset = _ensure_descriptions(subset)
    desc_series = subset["Description"]
    try:
        tfidf, matrix = _vectorizer_and_matrix(desc_series)
    except ValueError:
        return pd.DataFrame(columns=["Symbol", "Company Name", "Similarity"])

    try:
        idx = subset.index[subset["Symbol"] == symbol][0]
    except IndexError:
        return pd.DataFrame(columns=["Symbol", "Company Name", "Similarity"])

    sims = cosine_similarity(matrix[idx], matrix).ravel()
    peers = (
        subset.assign(Similarity=sims)
        .query("Symbol != @symbol")
        .sort_values("Similarity", ascending=False)
        .head(k)[["Symbol", "Company Name", "Similarity"]]
        .reset_index(drop=True)
    )
    return peers
