
from __future__ import annotations
from typing import List
import functools
import pandas as pd
import yfinance as yf
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

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
    if "Description" not in df.columns:
        df = df.copy()
        df["Description"] = ""
    missing_mask = df["Description"].isna() | (df["Description"] == "")
    if missing_mask.any():
        df.loc[missing_mask, "Description"] = (
            df.loc[missing_mask, "Symbol"].apply(_get_description)
        )
    return df

@functools.lru_cache(maxsize=1)
def _vectorizer_and_matrix(desc_series: pd.Series):
    tfidf = TfidfVectorizer(
        stop_words="english",
        ngram_range=(1, 2),
        min_df=2,
    )
    matrix = tfidf.fit_transform(desc_series)
    return tfidf, matrix

def top_peers(symbol: str, df: pd.DataFrame, k: int = 5) -> pd.DataFrame:
    df_with_desc = _ensure_descriptions(df)

    descriptions = df_with_desc["Description"].fillna("").astype(str)
    tfidf, matrix = _vectorizer_and_matrix(descriptions)

    try:
        idx = df_with_desc.index[df_with_desc["Symbol"] == symbol][0]
    except IndexError:
        return pd.DataFrame()

    sims = cosine_similarity(matrix[idx], matrix).ravel()
    peers = (
        df_with_desc.assign(Similarity=sims)
        .query("Symbol != @symbol")
        .sort_values("Similarity", ascending=False)
        .head(k)[["Symbol", "Company Name", "Similarity"]]
        .reset_index(drop=True)
    )
    return peers
