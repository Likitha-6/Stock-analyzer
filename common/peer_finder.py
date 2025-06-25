# common/peer_finder.py
from __future__ import annotations
from typing import List
import functools
import pandas as pd
import yfinance as yf
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# ────────────────────────────────────────────────────────────
# 1.  Description fetch & cache
# ────────────────────────────────────────────────────────────
_desc_cache: dict[str, str] = {}

def _get_description(sym: str) -> str:
    """Fetch and cache the company’s longBusinessSummary from yfinance."""
    if sym in _desc_cache:
        return _desc_cache[sym]

    try:
        info = yf.Ticker(f"{sym}.NS").info      # ← append .NS if you’re using NSE
        desc = info.get("longBusinessSummary") or ""
    except Exception:
        desc = ""

    _desc_cache[sym] = desc
    return desc

def _ensure_descriptions(df: pd.DataFrame) -> pd.DataFrame:
    """
    Guarantee df has a 'Description' column.
    Fills missing values by calling _get_description for each symbol.
    """
    if "Description" not in df.columns:
        df = df.copy()
        df["Description"] = ""

    missing_mask = df["Description"].isna() | (df["Description"] == "")
    if missing_mask.any():
        df.loc[missing_mask, "Description"] = (
            df.loc[missing_mask, "Symbol"].apply(_get_description)
        )

    return df

# ────────────────────────────────────────────────────────────
# 2.  TF-IDF similarity
# ────────────────────────────────────────────────────────────
@functools.lru_cache(maxsize=1)
def _vectorizer_and_matrix(desc_series: pd.Series):
    """Create & cache the TF-IDF matrix for the full description corpus."""
    tfidf = TfidfVectorizer(
        stop_words="english",
        ngram_range=(1, 2),
        min_df=2,
    )
    matrix = tfidf.fit_transform(desc_series.fillna(""))
    return tfidf, matrix

def top_peers(symbol: str, df: pd.DataFrame, k: int = 5) -> pd.DataFrame:
    """
    Return the top-k peers for *symbol* using cosine similarity on TF-IDF vectors.
    df must contain columns ['Symbol', 'Company Name'].
    """
    df_with_desc = _ensure_descriptions(df)

    tfidf, matrix = _vectorizer_and_matrix(df_with_desc["Description"])
    try:
        idx = df_with_desc.index[df_with_desc["Symbol"] == symbol][0]
    except IndexError:
        return pd.DataFrame()  # symbol not in dataframe

    sims = cosine_similarity(matrix[idx], matrix).ravel()
    peers = (
        df_with_desc.assign(Similarity=sims)
        .query("Symbol != @symbol")
        .sort_values("Similarity", ascending=False)
        .head(k)[["Symbol", "Company Name", "Similarity"]]
        .reset_index(drop=True)
    )
    return peers

