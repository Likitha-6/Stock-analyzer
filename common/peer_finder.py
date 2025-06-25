# common/peer_finder.py
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import functools

@functools.lru_cache(maxsize=1)
def _vectorizer_and_matrix(desc_series: pd.Series):
    """Create TF-IDF matrix (cached) for the full description corpus."""
    tfidf = TfidfVectorizer(
        stop_words="english",
        min_df=2,          # ignore very rare words
        ngram_range=(1, 2) # unigrams + bigrams
    )
    matrix = tfidf.fit_transform(desc_series.fillna(""))
    return tfidf, matrix

def top_peers(symbol: str, df: pd.DataFrame, k: int = 5):
    """
    Return the top-k peer symbols for *symbol* based on description similarity.
    
    df must contain columns ["Symbol", "Description"].
    """
    tfidf, matrix = _vectorizer_and_matrix(df["Description"])
    symbol_idx = df.index[df["Symbol"] == symbol].tolist()
    if not symbol_idx:
        return []
    idx = symbol_idx[0]

    # Cosine similarity of the selected row against all others
    sims = cosine_similarity(matrix[idx], matrix).flatten()
    df["__sim"] = sims
    peers = (
        df[df["Symbol"] != symbol]        # exclude self
          .sort_values("__sim", ascending=False)
          .head(k)
          [["Symbol", "Company Name", "__sim"]]
          .rename(columns={"__sim": "Similarity"})
    )
    return peers.reset_index(drop=True)
