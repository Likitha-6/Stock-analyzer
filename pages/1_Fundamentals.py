import streamlit as st
import pandas as pd

from common.sql import load_master
from common.data import load_name_lookup
from common.display import display_metrics


# ─────────────────────────────
# Page config
# ─────────────────────────────
st.set_page_config(page_title="Fundamentals", page_icon="📈", layout="wide")
st.title("Fundamentals – Stock Analysis")


# ─────────────────────────────
# Load and merge data
# ─────────────────────────────
master_df = load_master()
name_df   = load_name_lookup()

# Make sure we have Description for similarity algorithms later on
if "Description" not in master_df.columns:
    master_df = pd.merge(
        master_df,
        name_df[["Symbol", "Description"]],
        on="Symbol",
        how="left",
        validate="1:1",
    )

symbol2name = dict(zip(name_df["Symbol"], name_df["Company Name"]))


# ─────────────────────────────
# 1️⃣ Pick the primary stock
#    a) auto-load from Sector page if present
#    b) otherwise let user search
# ─────────────────────────────
chosen_sym = None  # always define the variable

default_sym = st.session_state.get("compare_symbol")

if default_sym and not st.session_state.get("already_loaded_from_sector"):
    st.success(f"Auto-loaded **{default_sym}** from Sector Analysis")
    chosen_sym = default_sym
    st.session_state["already_loaded_from_sector"] = True
else:
    query = st.text_input("Search by symbol or company name").strip()
    if query:
        mask = (
            name_df["Symbol"].str.contains(query, case=False, na=False) |
            name_df["Company Name"].str.contains(query, case=False, na=False)
        )
        matches = name_df[mask]

        if matches.empty:
            st.warning("No match found.")
        else:
            opts = matches.apply(
                lambda r: f"{r['Symbol']} – {r['Company Name']}", axis=1
            )
            selection = st.selectbox("Select company", opts.tolist())
            chosen_sym = selection.split(" – ")[0]

# stop rendering until a primary ticker is set
if not chosen_sym:
    st.stop()





# ─────────────────────────────
# 3️⃣ Render fundamentals + peers
# ─────────────────────────────
display_metrics(
    chosen_sym,
    master_df,
    name_df,   # your display_metrics signature must accept this
)
