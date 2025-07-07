import streamlit as st
import pandas as pd

from common.sql import load_master
from common.data import load_name_lookup
from common.display import display_metrics

# ─────────────────────────────
# Page config
# ─────────────────────────────
st.set_page_config(page_title="🔍 Fundamentals", page_icon="📈", layout="wide")
st.title("🔍 Fundamentals – Single-Stock Analysis")

# ─────────────────────────────
# Load and merge data
# ─────────────────────────────
master_df = load_master()
name_df   = load_name_lookup()

# Ensure Description is included for peer comparison
if "Description" not in master_df.columns:
    master_df = pd.merge(master_df, name_df[["Symbol", "Description"]], on="Symbol", how="left")

symbol2name = dict(zip(name_df["Symbol"], name_df["Company Name"]))

# ─────────────────────────────
# Sector navigation handoff
# ─────────────────────────────
default_sym = st.session_state.get("compare_symbol")
# ─────────────────────────────
# NEW: optional manual-compare panel
# ─────────────────────────────
# ─────────────────────────────
# Manual “compare stocks” workflow
# ─────────────────────────────
show_compare = st.checkbox(
    "🔄 Compare stocks manually",
    help="Tick to add one or more extra tickers for side-by-side comparison"
)

# initialise the persistent list once per session
if "compare_list" not in st.session_state:
    st.session_state.compare_list = []

if show_compare:
    # --- search bar ---
    add_query = st.text_input(
        "Search ticker or company name to add",
        key="cmp_query"
    ).strip()

    if add_query:
        # same fuzzy-match logic you use for the primary search
        mask = (
            name_df["Symbol"].str.contains(add_query, case=False, na=False) |
            name_df["Company Name"].str.contains(add_query, case=False, na=False)
        )
        matches = name_df[mask]

        if not matches.empty:
            opts = matches.apply(lambda r: f"{r['Symbol']} – {r['Company Name']}", axis=1)
            sel = st.selectbox("Select match to add", opts.tolist(), key="cmp_sel")
            if st.button("Add stock"):
                sym_to_add = sel.split(" – ")[0]
                if sym_to_add != chosen_sym and sym_to_add not in st.session_state.compare_list:
                    st.session_state.compare_list.append(sym_to_add)
        else:
            st.info("No matches for that query.")

    # show current list & allow removal
    if st.session_state.compare_list:
        to_remove = st.multiselect(
            "Currently comparing",
            options=st.session_state.compare_list,
            default=[]
        )
        if st.button("Remove selected"):
            st.session_state.compare_list = [
                s for s in st.session_state.compare_list if s not in to_remove
            ]

# final list to feed into display_metrics
compare_symbols = st.session_state.compare_list


if default_sym and not st.session_state.get("already_loaded_from_sector"):
    st.success(f"Auto-loaded **{default_sym}** from Sector Analysis")
    chosen_sym = default_sym
    st.session_state["already_loaded_from_sector"] = True
else:
    # Regular search
    query = st.text_input("Search by symbol or company name").strip()
    chosen_sym = None
    if query:
        mask = (
            name_df["Symbol"].str.contains(query, case=False, na=False) |
            name_df["Company Name"].str.contains(query, case=False, na=False)
        )
        matches = name_df[mask]
        if matches.empty:
            st.warning("No match found.")
        else:
            opts = matches.apply(lambda r: f"{r['Symbol']} – {r['Company Name']}", axis=1)
            chosen = st.selectbox("Select company", opts.tolist())
            chosen_sym = chosen.split(" – ")[0]

if not chosen_sym:
    st.stop()

# ─────────────────────────────
# Display fundamentals + similar peers
# ─────────────────────────────
if chosen_sym in master_df["Symbol"].values:
    display_metrics(chosen_sym, master_df, name_df)
else:
    st.error("Symbol not found in master dataset.")
