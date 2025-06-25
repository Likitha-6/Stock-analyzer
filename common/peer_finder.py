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


def top_peers(symbol: str, df: pd.DataFrame = None, k=10) -> pd.DataFrame:
    if df is None:
        df = load_master()

    # Clean descriptions
    df = df.dropna(subset=["Symbol", "Description"])
    df = df[df["Description"].str.len() > 30]  # filter very short descriptions

    if symbol not in df["Symbol"].values:
        return pd.DataFrame()

    descriptions = df.set_index("Symbol")["Description"]
    tfidf = TfidfVectorizer(
        stop_words="english",
        ngram_range=(1, 2),  # bigrams
        min_df=2,
        max_df=0.9
    )
    tfidf_matrix = tfidf.fit_transform(descriptions)

    # Compute similarity scores
    index = descriptions.index.tolist().index(symbol)
    sim_scores = cosine_similarity(tfidf_matrix[index], tfidf_matrix).flatten()

    # Create similarity DataFrame
    sim_df = pd.DataFrame({
        "Symbol": descriptions.index,
        "Score": sim_scores
    }).sort_values(by="Score", ascending=False)

    sim_df = sim_df[sim_df["Symbol"] != symbol].head(k)
    return df.set_index("Symbol").loc[sim_df["Symbol"]].reset_index()
