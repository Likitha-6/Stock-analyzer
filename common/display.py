# common/display.py – updated
import streamlit as st
import pandas as pd
import yfinance as yf
import numpy as np
from typing import Optional

from common.finance import (
    _fetch_core_metrics,
    get_industry_averages,
    market_cap_label,
    val_with_ind_avg,
    interpret,
    get_stock_description,
    human_market_cap,
)
from common.charts import _price_chart, _rev_pm_fcf_frames
from common.peer_finder import top_peers

# ────────────────────────────────────────────────────────────────
# 1️⃣  Two‑stock comparison block
# ────────────────────────────────────────────────────────────────

def _meta_header(sym: str, data: dict, industry: str):
    """Render basic meta info for a single stock."""
    price = data.get("_price")
    hist  = yf.Ticker(f"{sym}.NS").history("max", auto_adjust=True)
    ath   = hist["Close"].max() if not hist.empty else None
    pct   = ((price - ath) / ath * 100) if price and ath else None

    st.subheader(data.get('_company') or sym)
    meta = [
        f"Sector: {data.get('_sector') or 'N/A'}",
        f"Industry: {industry or 'N/A'}",
        f"Market Cap: {human_market_cap(data.get('_market_cap'))} ({market_cap_label(data.get('_market_cap'))})",
        f"Price: ₹{price:.2f}" if price is not None else "Price: N/A",
        f"ATH: {ath:.2f} ({pct:.2f}% from current)" if ath is not None and pct is not None else "ATH: N/A",
    ]
    st.caption(" | ".join(meta))
    with st.expander("📝 Description"):
        st.write(get_stock_description(sym))


def compare_stocks(sym1: str, sym2: str, master_df: pd.DataFrame):
    """Side‑by‑side comparison view."""
    st.markdown("---")
    st.markdown(f"## 🔄 Comparison: {sym1} vs {sym2}")

    d1, d2 = _fetch_core_metrics(sym1), _fetch_core_metrics(sym2)
    ind1   = master_df.loc[master_df["Symbol"] == sym1, "Industry"].iat[0]
    ind2   = master_df.loc[master_df["Symbol"] == sym2, "Industry"].iat[0]

    c1, c2 = st.columns(2)
    with c1: _meta_header(sym1, d1, ind1)
    with c2: _meta_header(sym2, d2, ind2)

    avg1 = get_industry_averages(ind1, master_df)
    avg2 = get_industry_averages(ind2, master_df)
    metrics = [
        "PE Ratio","EPS","Profit Margin","ROE",
        "Debt to Equity","Dividend Yield","Free Cash Flow"
    ]
    rows = []
    for m in metrics:
        v1, v2 = d1.get(m), d2.get(m)
        cell1 = val_with_ind_avg(m, v1, avg1.get(m))
        cell2 = val_with_ind_avg(m, v2, avg2.get(m))
        t1 = t2 = ""
        if v1 is not None and v2 is not None and np.isfinite(v1) and np.isfinite(v2):
            n1 = v1 * 100 if m in ("Profit Margin","ROE") else v1
            n2 = v2 * 100 if m in ("Profit Margin","ROE") else v2
            if m == "Debt to Equity":
                n1 /= 100; n2 /= 100
            if m == "Free Cash Flow":
                n1 /= 1e7; n2 /= 1e7
            lower_is_better = m in ("Debt to Equity","PE Ratio")
            if lower_is_better:
                t1, t2 = (" ✅", "") if n1 < n2 else ("", " ✅") if n2 < n1 else ("", "")
            else:
                t1, t2 = (" ✅", "") if n1 > n2 else ("", " ✅") if n2 > n1 else ("", "")
        rows.append((m, f"{cell1}{t1}", f"{cell2}{t2}"))
    st.table(pd.DataFrame(rows, columns=["Metric", sym1, sym2]))

    period = st.selectbox("Chart period", ["3mo","6mo","1y","3y","5y","max"], 2, key=f"cmp_{sym1}_{sym2}")
    cc1, cc2 = st.columns(2)
    for col, sym in ((cc1, sym1), (cc2, sym2)):
        ch = _price_chart(sym, period)
        col.altair_chart(ch, use_container_width=True) if ch is not None else col.info("No data")

    rev1, pm1, fcf1 = _rev_pm_fcf_frames(sym1)
    rev2, pm2, fcf2 = _rev_pm_fcf_frames(sym2)
    if rev1 is not None and rev2 is not None:
        st.subheader("📈 Revenue (₹ Cr)"); c1,c2=st.columns(2); c1.bar_chart(rev1); c2.bar_chart(rev2)
    if pm1 is not None and pm2 is not None:
        st.subheader("🧮 Profit Margin (%)"); c1,c2=st.columns(2); c1.line_chart(pm1); c2.line_chart(pm2)
    if fcf1 is not None and fcf2 is not None:
        st.subheader("💰 Free Cash Flow (₹ Cr)"); c1,c2=st.columns(2); c1.bar_chart(fcf1); c2.bar_chart(fcf2)

# ────────────────────────────────────────────────────────────────
# 2️⃣  Single‑stock dashboard
# ────────────────────────────────────────────────────────────────

def display_metrics(symbol: str, master_df: pd.DataFrame, name_df: pd.DataFrame):
    """Render fundamentals for a single stock. If user has not navigated
    from Sector Analysis, show internal peer‑dropdown; otherwise suppress it."""

    coming_from_sector = st.session_state.get("from_sector_nav", False)

    # ── Peer dropdown (hidden when navigated from Sector Analysis) ──
    peer_sym = None
    if not coming_from_sector:
        peer_df = top_peers(symbol, master_df, k=10)
        if not peer_df.empty:
            peer_labels = [f"{row['Company Name']} ({row['Symbol']})" for _, row in peer_df.iterrows()]
            chosen = st.selectbox("🔄 Compare with peer", ["--"] + peer_labels, key=f"peer_{symbol}")
            peer_sym = chosen.split("(")[-1].rstrip(")") if chosen != "--" else None

    if peer_sym:
        compare_stocks(symbol, peer_sym, master_df)
        return  # skip single‑stock details

    # ── Single‑stock fundamentals ──
    data = _fetch_core_metrics(symbol)
    industry = master_df.loc[master_df["Symbol"] == symbol, "Industry"].iat[0]
    ind_avg  = get_industry_averages(industry, master_df)

    st.markdown(f"## {data.get('_company') or symbol}")
    price = data.get("_price")
    hist  = yf.Ticker(f"{symbol}.NS").history("max", auto_adjust=True)
    ath   = hist["Close"].max() if not hist.empty else None
    pct   = ((price - ath) / ath * 100) if price and ath else None

    meta = [
        f"Sector: {data.get('_sector') or 'N/A'}",
        f"Industry: {industry or 'N/A'}",
        f"Market Cap: {human_market_cap(data.get('_market_cap'))} ({market_cap_label(data.get('_market_cap'))})",
        f"Price: ₹{price:.2f}" if price is not None else "Price: N/A",
        f"ATH: {ath:.2f} ({pct:.2f}% from current)" if ath is not None and pct is not None else "ATH: N/A",
    ]
    st.caption(" | ".join(meta))
    with st.expander("📝 Description"):
        st.write(get_stock_description(symbol))
    st.markdown("---")

    metrics = ["PE Ratio","EPS","Profit Margin","ROE","Debt to Equity","Dividend Yield","Free Cash Flow"]
    rows = [
        (m, val_with_ind_avg(m, data.get(m), ind_avg.get(m)), interpret(m, data.get(m), ind_avg.get(m)))
        for m in metrics
    ]
    st.table(pd.DataFrame(rows, columns=["Metric","Value (w/ Avg)","✓"]))

    period = st.selectbox("Price chart period", ["1mo","3mo","6mo","1y","3y","5y","max"], 3, key=f"period_{symbol}")
    ch = _price_chart(symbol, period)
    if ch is not None:
        st.altair_chart(ch, use_container_width=True)

    rev, pm, fcf = _rev_pm_fcf_frames(symbol)
    if fcf is not None and not fcf.empty:
        st.subheader("💰 Free Cash Flow (₹ Cr)"); st.bar_chart(fcf)
    if rev is not None and not rev.empty:
        st.subheader("📈 Revenue (₹ Cr)"); st.bar_chart(rev)
    if pm is not None and not pm.empty:
        st.subheader("🧮 Profit Margin (%)"); st.line_chart(pm)

    # Clear the flag so subsequent manual interactions show the peer dropdown again
    st.session_state.from_sector_nav = False
