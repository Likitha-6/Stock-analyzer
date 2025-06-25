
from __future__ import annotations
from typing import List
import pandas as pd
import yfinance as yf
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# Cache for fetched descriptions
_description_cache: dict[str, str] = {}

def _get_description(sym: str) -> str:
    if sym in _description_cache:
        return _description_cache[sym]
    try:
        info = yf.Ticker(f"{sym}.NS").info
        desc = info.get("longBusinessSummary", "")
    except Exception:
        desc = ""
    _description_cache[sym] = desc
    return desc

def _ensure_descriptions(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    if "Description" not in df.columns:
        df["Description"] = ""
    missing = df["Description"].isna() | (df["Description"].astype(str).str.strip() == "")
    df.loc[missing, "Description"] = df.loc[missing, "Symbol"].apply(_get_description)
    return df

def _vectorizer_and_matrix(desc_series: pd.Series):
    desc_series = desc_series.fillna("").astype(str)
    tfidf = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), min_df=2)
    matrix = tfidf.fit_transform(desc_series)
    return tfidf, matrix

def top_peers(symbol: str, df: pd.DataFrame, k: int = 5) -> pd.DataFrame:
    df = _ensure_descriptions(df)
    desc_series = df["Description"].fillna("").astype(str)
    tfidf, matrix = _vectorizer_and_matrix(desc_series)

    try:
        idx = df.index[df["Symbol"] == symbol][0]
    except IndexError:
        return pd.DataFrame(columns=["Symbol", "Company Name", "Similarity"])

    sims = cosine_similarity(matrix[idx], matrix).flatten()

    peers = (
        df.assign(Similarity=sims)
        .query("Symbol != @symbol")
        .sort_values("Similarity", ascending=False)
        .head(k)[["Symbol", "Company Name", "Similarity"]]
        .reset_index(drop=True)
    )
    return peers
