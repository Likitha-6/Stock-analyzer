import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf

from common.data import load_master, load_name_lookup
from common.finance import human_market_cap

import streamlit as st

st.set_page_config(page_title="Sector Analysis", layout="wide")

st.title("📂 Sector & Industry Analysis")

st.write("If you're seeing this, your file is loading correctly.")


# Helper functions
def _to_float(x):
    try:
        return float(x)
    except Exception:
        return np.nan

def _bad(val):
    return np.isnan(_to_float(val))

def icon_hi(v, a):
    v, a = _to_float(v), _to_float(a)
    if _bad(v) or _bad(a): return "❓"
    return "✅" if v >= a else "🟡" if v >= a * 0.8 else "🔴"

def icon_lo(v, a):
    v, a = _to_float(v), _to_float(a)
    if _bad(v) or _bad(a): return "❓"
    return "✅" if v <= a else "🟡" if v <= a * 1.1 else "🔴"

def icon_d2e(v, a):
    v, a = _to_float(v), _to_float(a)
    if _bad(v) or _bad(a): return "❓"
    return "✅" if v <= a else "🟡" if v <= 1.5 else "🔴"

def fmt_cap(val):
    if val is None or pd.isna(val): return "N/A"
    return f"{val/1e9:.2f}B" if val >= 1e9 else f"{val/1e6:.2f}M" if val >= 1e6 else f"{val:.0f}"

# Load data
master_df = load_master()
name_df = load_name_lookup()
df = pd.merge(master_df, name_df, on="Symbol", how="left")

st.sidebar.header("🏍️ Filter by")
sec_sel = st.sidebar.selectbox("Sector", sorted(df["Big Sectors"].dropna().unique()))
ind_sel = st.sidebar.selectbox("Industry", sorted(df[df["Big Sectors"] == sec_sel]["Industry"].dropna().unique()))
rank_by = st.sidebar.selectbox("Rank Top-10 by", ["Market Cap", "EPS", "ROE"])
show_all = st.sidebar.checkbox("Show **all** companies", value=False)

interp_threshold = st.sidebar.selectbox("🎯 Green Criteria", ["All ✅", "≥4 ✅", "≥3 ✅", "≥2 ✅"], index=0)
interp_cutoff = {"All ✅": 5, "≥4 ✅": 4, "≥3 ✅": 3, "≥2 ✅": 2}[interp_threshold]

scoped_df = df[(df["Big Sectors"] == sec_sel) & (df["Industry"] == ind_sel)]

def fetch_metrics(sym):
    try:
        info = yf.Ticker(f"{sym}.NS").info
        d2e = info.get("debtToEquity")
        pm = info.get("profitMargins")
        return {
            "PE Ratio": info.get("trailingPE"),
            "EPS": info.get("trailingEps"),
            "ROE": info.get("returnOnEquity"),
            "Market Cap": info.get("marketCap"),
            "Profit Margin": None if pm is None else min(pm * 100, 100) if pm < 1.5 else None,
            "Debt to Equity": None if d2e is None else d2e / 100,
        }
    except Exception:
        return {k: None for k in ["PE Ratio", "EPS", "ROE", "Market Cap", "Profit Margin", "Debt to Equity"]}

symbols = scoped_df["Symbol"].dropna().unique()
lookup = {s: fetch_metrics(s) for s in symbols}
avg_df = pd.DataFrame.from_dict(lookup, orient="index")

st.subheader(f"📊 Summary – {ind_sel}")
st.markdown(f"**Total companies in industry:** {len(scoped_df)}")

if not avg_df.empty:
    numeric_cols = ["PE Ratio", "EPS", "ROE", "Profit Margin", "Debt to Equity", "Market Cap"]
    avg_df[numeric_cols] = avg_df[numeric_cols].apply(pd.to_numeric, errors="coerce")
    avg_df = avg_df.replace([np.inf, -np.inf], np.nan)
    avg_vals = avg_df[numeric_cols].mean()

    cols = st.columns(6)
    cols[0].metric("Avg PE", f"{avg_vals.get('PE Ratio', np.nan):.2f}")
    cols[1].metric("Avg EPS", f"{avg_vals.get('EPS', np.nan):.2f}")
    cols[2].metric("Avg ROE", f"{avg_vals.get('ROE', np.nan) * 100:.2f}%")
    cols[3].metric("Avg P. Margin", f"{avg_vals.get('Profit Margin', np.nan):.2f}%")
    cols[4].metric("Avg D/E", f"{avg_vals.get('Debt to Equity', np.nan):.2f}")
    cols[5].metric("Avg MCap", fmt_cap(avg_vals.get("Market Cap")))
else:
    st.info("No financial data available.")

# Rank companies
sort_key = {"Market Cap": "Market Cap", "EPS": "EPS", "ROE": "ROE"}[rank_by]
ranked = sorted(symbols, key=lambda s: lookup[s].get(sort_key) or 0, reverse=True)
sel_syms = ranked if show_all else ranked[:10]
header_lbl = "📋 All Companies" if show_all else f"🔢 Top-10 – {rank_by}"

rows, qualified = [], []
name_lookup = name_df.set_index("Symbol")["Company Name"].to_dict()

for sym in sel_syms:
    m = lookup[sym]
    row = {
        "Symbol": sym,
        "Company": name_lookup.get(sym, ""),
        "PE": m["PE Ratio"],
        "EPS": m["EPS"],
        "ROE %": None if m["ROE"] is None else m["ROE"] * 100,
        "P. Margin %": m["Profit Margin"],
        "D/E": m["Debt to Equity"],
        "MCap": fmt_cap(m["Market Cap"]),
    }
    icons = {
        "PE": icon_lo(m["PE Ratio"], avg_vals.get("PE Ratio")),
        "EPS": icon_hi(m["EPS"], avg_vals.get("EPS")),
        "ROE": icon_hi(m["ROE"], avg_vals.get("ROE")),
        "PM": icon_hi(m["Profit Margin"], avg_vals.get("Profit Margin")),
    }

