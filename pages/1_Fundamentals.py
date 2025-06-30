import streamlit as st
import pandas as pd

from common.sql import load_master
from common.data import load_name_lookup
from common.display import display_metrics, compare_stocks

# ─────────────────────────────
# Page config
# ─────────────────────────────
st.set_page_config(page_title="🔍 Fundamentals", page_icon="📈", layout="wide")
st.title("🔍 Fundamentals – Single-Stock Analysis")

# ─────────────────────────────
# Load data
# ─────────────────────────────
master_df = load_master()
name_df = load_name_lookup()
symbol2name = dict(zip(name_df["Symbol"], name_df["Company Name"]))

# ─────────────────────────────
# Session hand-off from Sector Analysis
# (Auto-load once only)
# ─────────────────────────────
default_sym = st.session_state.pop("compare_symbol", None)
default_peers = st.session_state.get("qual_peers", [])

# ─────────────────────────────
# User Option: Compare Two Stocks?
# ─────────────────────────────
compare_mode = st.checkbox("🔄 Compare Two Stocks")

# ─────────────────────────────
# Stock Selection UI
# ─────────────────────────────
def stock_search(label, key_prefix=""):
    query = st.text_input(f"{label} – Search by symbol or company name", key=f"{key_prefix}_query").strip()
    if query:
        mask = (
            name_df["Symbol"].str.contains(query, case=False, na=False) |
            name_df["Company Name"].str.contains(query, case=False, na=False)
        )
        matches = name_df[mask]
        if matches.empty:
            st.warning("No match found.")
            return None
        else:
            opts = matches.apply(lambda r: f"{r['Symbol']} – {r['Company Name']}", axis=1)
            selected = st.selectbox(f"{label} – Select company", opts.tolist(), key=f"{key_prefix}_select")
            return selected.split(" – ")[0]
    return None

if compare_mode:
    sym1 = stock_search("Stock 1", "s1")
    sym2 = stock_search("Stock 2", "s2")

    if sym1 and sym2:
        st.markdown("### 📊 Side-by-Side Comparison")
        compare_stocks(sym1, sym2, master_df)
    st.stop()  # skip everything else when in compare mode

# Fallback: auto-load or manual single stock selection
chosen_sym = default_sym
if default_sym:
    st.success(f"Auto-loaded **{default_sym}** from Sector Analysis")

manual_sym = stock_search("🔍 Choose a Stock")
if manual_sym:
    chosen_sym = manual_sym

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
# Peer comparison dropdown
# (only if peers were handed off)
# ─────────────────────────────
if default_peers:
    peer_pool = [s for s in default_peers if s != chosen_sym]
    if peer_pool:
        st.markdown("---")
        st.subheader("⚔️ Compare with another qualified peer")
        peer_labels = [f"{symbol2name.get(s, s)} ({s})" for s in peer_pool]
        peer_choice = st.selectbox("Select peer", peer_labels, key="peer_choice")
        peer_sym = peer_pool[peer_labels.index(peer_choice)]

        st.markdown("### Side-by-Side Comparison")
        compare_stocks(chosen_sym, peer_sym, master_df)
    else:
        st.info("No peer list passed from Sector Analysis.")
