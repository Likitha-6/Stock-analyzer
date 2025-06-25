
from typing import List
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import functools

@functools.lru_cache(maxsize=1)
def _vectorizer_and_matrix(desc_series: pd.Series):
    """Create TF-IDF matrix (cached) for the full description corpus."""
    tfidf = TfidfVectorizer(
        stop_words="english",
        min_df=2,
        ngram_range=(1, 2)
    )
    matrix = tfidf.fit_transform(desc_series)
    return tfidf, matrix

def top_peers(symbol: str, df: pd.DataFrame, k: int = 5) -> pd.DataFrame:
    """
    Return the top-k peer symbols for *symbol* based on description similarity.
    df must contain columns ["Symbol", "Description"].
    """
    descriptions = df_with_desc["Description"].fillna("").astype(str)
    tfidf, matrix = _vectorizer_and_matrix(descriptions)
    symbol_idx = df.index[df["Symbol"] == symbol].tolist()
    if not symbol_idx:
        return pd.DataFrame()
    idx = symbol_idx[0]

    sims = cosine_similarity(matrix[idx], matrix).flatten()
    df = df.copy()
    df["Similarity"] = sims
    peers = (
        df[df["Symbol"] != symbol]
          .sort_values("Similarity", ascending=False)
          .head(k)
          [["Symbol", "Company Name", "Similarity"]]
    )
    return peers.reset_index(drop=True)
