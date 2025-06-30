# pages/1_Fundamentals.py

import streamlit as st
import pandas as pd

from common.sql import load_master          # ← now pulls from SQLite
from common.data import load_name_lookup
from common.display import display_metrics, compare_stocks

# ─────────────────────────────
# Safe refresh if new stock is selected
# ─────────────────────────────
if "compare_symbol" in st.session_state:
    current_symbol = st.session_state.compare_symbol
    last_symbol = st.session_state.get("last_symbol", None)

    if current_symbol != last_symbol:
        st.session_state.last_symbol = current_symbol
        # Clear old peers and sector navigation flags
        if "qual_peers" in st.session_state:
            del st.session_state["qual_peers"]
        if "from_sector_nav" in st.session_state:
            del st.session_state["from_sector_nav"]
        # Set flag to rerun after safe render
        st.session_state._defer_rerun = True

# ─────────────────────────────
# Page config
# ─────────────────────────────
st.set_page_config(page_title="🔍 Fundamentals", page_icon="📈", layout="wide")
st.title("🔍 Fundamentals – Single-Stock Analysis")

# ✅ Safe rerun after render
if st.session_state.pop("_defer_rerun", False):
    st.experimental_rerun()

# ─────────────────────────────
# Load data
# ─────────────────────────────
master_df = load_master()
name_df   = load_name_lookup()
symbol2name = dict(zip(name_df["Symbol"], name_df["Company Name"]))

# ─────────────────────────────
# Session hand-off from Sector Analysis
# ─────────────────────────────
default_sym   = st.session_state.get("compare_symbol")
default_peers = st.session_state.get("qual_peers", [])

# ─────────────────────────────
# Symbol selection UI
# ─────────────────────────────
if default_sym:
    st.success(f"Auto-loaded **{default_sym}** from Sector Analysis")
    chosen_sym = default_sym
else:
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
# Display main fundamentals
# ─────────────────────────────
if chosen_sym in master_df["Symbol"].values:
    display_metrics(chosen_sym, master_df, name_df)
else:
    st.error("Symbol not found in master dataset.")
    st.stop()

# ─────────────────────────────
# Peer comparison (only if from Sector Analysis)
# ─────────────────────────────
if st.session_state.get("from_sector_nav"):
    if default_peers:
        peer_pool = [s for s in default_peers if s != chosen_sym]
        if peer_pool:
            st.markdown("---")
            st.subheader("⚔️ Compare with another qualified peer")
            peer_labels = [f"{symbol2name.get(s, s)} ({s})" for s in peer_pool]
            peer_choice = st.selectbox("Select peer", peer_labels, key="peer_choice")
            peer_sym = peer_pool[peer_labels.index(peer_choice)]

            # Render side-by-side comparison
            st.markdown("### Side-by-Side Comparison")
            compare_stocks(chosen_sym, peer_sym, master_df)
        else:
            st.info("No peer list passed from Sector Analysis.")

    # Clear after use
    del st.session_state["from_sector_nav"]
