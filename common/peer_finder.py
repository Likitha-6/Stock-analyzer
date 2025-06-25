# common/peer_finder.py
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from common.sql import load_master

def top_peers(symbol: str, df: pd.DataFrame = None, k=10, filter_sector: bool = False) -> pd.DataFrame:
    if df is None:
        df = load_master()

    df = df.dropna(subset=["Symbol", "Description"])
    df = df[df["Description"].str.len() > 30]

    if symbol not in df["Symbol"].values:
        return pd.DataFrame()

    # Optionally restrict to same sector
    if filter_sector:
        input_sector = df.loc[df["Symbol"] == symbol, "Big Sectors"].values[0]
        df = df[df["Big Sectors"] == input_sector]

    descriptions = df.set_index("Symbol")["Description"]
    tfidf = TfidfVectorizer(
        stop_words="english",
        ngram_range=(1, 2),
        min_df=2,
        max_df=0.9
    )
    tfidf_matrix = tfidf.fit_transform(descriptions)

    # Compute cosine similarity
    index = descriptions.index.tolist().index(symbol)
    sim_scores = cosine_similarity(tfidf_matrix[index], tfidf_matrix).flatten()

    sim_df = pd.DataFrame({
        "Symbol": descriptions.index,
        "Score": sim_scores
    }).sort_values(by="Score", ascending=False)

    sim_df = sim_df[sim_df["Symbol"] != symbol].head(k)
    return df.set_index("Symbol").loc[sim_df["Symbol"]].reset_index()
