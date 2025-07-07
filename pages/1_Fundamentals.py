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
# Optional “compare stocks” panel (super-simple)
# ─────────────────────────────

# ─────────────────────────────
# Display fundamentals
# ─────────────────────────────
display_metrics(
    chosen_sym,
    master_df,
    name_df,
    manual_compares=compare_symbols
)


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
show_compare = st.checkbox(
    "🔄 Compare stocks manually",
    help="Tick to choose extra tickers for side-by-side comparison"
)

compare_symbols = []
if show_compare:
    compare_symbols = st.multiselect(
        label="Type a ticker or company name",
        options=name_df["Symbol"].sort_values(),   # searchable list
        default=[],
        key="manual_compare"
    )
    # make sure the primary symbol isn’t duplicated
    compare_symbols = [s for s in compare_symbols if s != chosen_sym]

# ─────────────────────────────
# Display fundamentals + similar peers
# ─────────────────────────────
if chosen_sym in master_df["Symbol"].values:
    display_metrics(chosen_sym, master_df, name_df)
else:
    st.error("Symbol not found in master dataset.")
