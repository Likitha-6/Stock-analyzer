# common/peer_finder.py

from __future__ import annotations
from typing import List
import pandas as pd
import yfinance as yf
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# Cache for descriptions
_desc_cache: dict[str, str] = {}

def _get_description(sym: str) -> str:
    if sym in _desc_cache:
        return _desc_cache[sym]
    try:
        info = yf.Ticker(f"{sym}.NS").info
        desc = info.get("longBusinessSummary") or ""
    except Exception:
        desc = ""
    _desc_cache[sym] = desc
    return desc

def _ensure_descriptions(df: pd.DataFrame) -> pd.DataFrame:
    """Ensure 'Description' column exists with valid text."""
    df = df.copy()
    if "Description" not in df.columns:
        df["Description"] = ""
    missing = df["Description"].isna() | (df["Description"].str.strip() == "")
    df.loc[missing, "Description"] = df.loc[missing, "Symbol"].apply(_get_description)
    return df

def _vectorizer_and_matrix(desc_series: pd.Series):
    """Create TF-IDF matrix from company descriptions."""
    desc_series = desc_series.fillna("").astype(str)
    tfidf = TfidfVectorizer(
        stop_words="english",
        ngram_range=(1, 2),
        min_df=2
    )
    matrix = tfidf.fit_transform(desc_series)
    return tfidf, matrix

def top_peers(symbol: str, df: pd.DataFrame, k: int = 5) -> pd.DataFrame:
    """Return top-k peers based on business description similarity."""
    df = _ensure_descriptions(df)
    descriptions = df["Description"].fillna("").astype(str)

    tfidf, matrix = _vectorizer_and_matrix(descriptions)

    try:
        idx = df.index[df["Symbol"] == symbol][0]
    except IndexError:
        return pd.DataFrame(columns=["Symbol", "Company Name", "Similarity"])

    sims = cosine_similarity(matrix[idx], matrix).ravel()
    peers = (
        df.assign(Similarity=sims)
        .query("Symbol != @symbol")
        .sort_values("Similarity", ascending=False)
        .head(k)[["Symbol", "Company Name", "Similarity"]]
        .reset_index(drop=True)
    )
    return peers
