"""
Peer-finder: global search across all companies using TF-IDF on the
`Description` column fetched from sqlite (via load_master).

Usage
-----
from common.peer_finder import top_peers
master_df = load_master()
peer_df = top_peers("TCS", master_df, k=5)
"""

from __future__ import annotations
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

_MIN_LEN = 30          # ignore descriptions shorter than this


def _prepare_corpus(df: pd.DataFrame) -> pd.DataFrame:
    """
    Return a DataFrame with non-empty, printable descriptions only.
    """
    desc = (
        df["Description"]
        .fillna("")
        .astype(str)
        .str.strip()
    )
    mask = desc.str.len() >= _MIN_LEN
    return df.loc[mask].reset_index(drop=True)


def _build_tfidf(desc_series: pd.Series):
    """Fit a TF-IDF vectorizer and return (vectorizer, matrix)."""
    vec = TfidfVectorizer(
        stop_words="english",
        ngram_range=(1, 2),
        max_features=20_000
    )
    mat = vec.fit_transform(desc_series)
    return vec, mat


def top_peers(symbol: str, master_df: pd.DataFrame, k: int = 10) -> pd.DataFrame:
    """
    Compute top-k peers for *symbol* among ALL companies with valid descriptions.

    Returns a DataFrame with columns:
        Symbol | Company Name | Similarity
    """
    corpus_df = _prepare_corpus(master_df)

    # Bail if target symbol is missing after filtering
    if symbol not in corpus_df["Symbol"].values:
        return pd.DataFrame(columns=["Symbol", "Company Name", "Similarity"])

    _, matrix = _build_tfidf(corpus_df["Description"])

    idx_target = corpus_df.index[corpus_df["Symbol"] == symbol][0]
    sims = cosine_similarity(matrix[idx_target], matrix).flatten()

    peers = (
        corpus_df.assign(Similarity=sims)
        .query("Symbol != @symbol")
        .sort_values("Similarity", ascending=False)
        .head(k)[["Symbol", "Company Name", "Similarity"]]
        .reset_index(drop=True)
    )
    return peers
