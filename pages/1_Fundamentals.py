# pages/1_Fundamentals.py
import streamlit as st
import pandas as pd

from common.sql import load_master          # ← now pulls from SQLite
from common.data import load_name_lookup    # (if you still need the CSV helper)

from common.display import display_metrics, compare_stocks
if "compare_symbol" in st.session_state:
    if "last_symbol" not in st.session_state:
        st.session_state.last_symbol = None

    if st.session_state.compare_symbol != st.session_state.last_symbol:
        # symbol has changed — reset peers
        st.session_state.last_symbol = st.session_state.compare_symbol
        st.session_state.qual_peers = []
        st.experimental_rerun()
# ─────────────────────────────
# Page config
# ─────────────────────────────
st.set_page_config(page_title="🔍 Fundamentals", page_icon="📈", layout="wide")
st.title("🔍 Fundamentals – Single-Stock Analysis")
if st.session_state.pop("_needs_rerun", False):
    st.experimental_rerun()


# ─────────────────────────────
# Data
# ─────────────────────────────
master_df = load_master()
name_df   = load_name_lookup()
symbol2name = dict(zip(name_df["Symbol"], name_df["Company Name"]))


# ─────────────────────────────
# Checkbox to enable manual comparison
# ─────────────────────────────
compare_mode = st.checkbox("🔁 Compare two stocks manually")

# ─────────────────────────────
# Symbol selection UI (first stock)
# ─────────────────────────────
chosen_sym = None
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
        opts = matches.apply(lambda r: f"{r['Symbol']} – {r['Company Name']}", axis=1)
        chosen = st.selectbox("Select company", opts.tolist())
        chosen_sym = chosen.split(" – ")[0]

# Fallback from Sector Analysis
if not chosen_sym and not compare_mode:
    default_sym = st.session_state.get("compare_symbol")
    if default_sym:
        st.success(f"Auto-loaded **{default_sym}** from Sector Analysis")
        chosen_sym = default_sym

if not chosen_sym:
    st.stop()

# ─────────────────────────────
# Display either single or comparison
# ─────────────────────────────
if compare_mode:
    st.markdown("---")
    st.subheader("📘 Compare with a second stock")

    second_sym = None
    query2 = st.text_input("Search second stock by symbol or name", key="second_query").strip()

    if query2:
        mask2 = (
            name_df["Symbol"].str.contains(query2, case=False, na=False) |
            name_df["Company Name"].str.contains(query2, case=False, na=False)
        )
        matches2 = name_df[mask2]
        if matches2.empty:
            st.warning("No match found.")
        else:
            opts2 = matches2.apply(lambda r: f"{r['Symbol']} – {r['Company Name']}", axis=1)
            chosen2 = st.selectbox("Select second company", opts2.tolist(), key="second_select")
            second_sym = chosen2.split(" – ")[0]

    if second_sym:
        if second_sym == chosen_sym:
            st.info("Please select a different stock for comparison.")
        else:
            st.markdown("### Side-by-Side Manual Comparison")
            compare_stocks(chosen_sym, second_sym, master_df)
else:
    # ─────────────────────────────
    # Display main fundamentals
    # ─────────────────────────────
    if chosen_sym in master_df["Symbol"].values:
        display_metrics(chosen_sym, master_df, name_df)
    else:
        st.error("Symbol not found in master dataset.")
        st.stop()

# ─────────────────────────────
# Peer comparison dropdown
# (only if peers were handed off and not in compare mode)
# ─────────────────────────────
if not compare_mode:
    default_peers = st.session_state.get("qual_peers", [])
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
