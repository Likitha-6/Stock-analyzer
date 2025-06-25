# pages/3_📂 Sector Analysis.py
import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf

from common.data import load_master, load_name_lookup
from common.finance import human_market_cap

# ────────────────────────────────────────────────────────────
# Page setup
# ────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="📂 Sector Analysis",
    page_icon="📂",
    layout="wide",
    initial_sidebar_state="expanded"
)
st.title("📂 Sector & Industry Analysis")

# ────────────────────────────────────────────────────────────
# 0⃣  Helpers
# ────────────────────────────────────────────────────────────
def _to_float(x):
    """Safely coerce any value to float; returns np.nan on failure."""
    try:
        return float(x)
    except Exception:
        return np.nan

def _bad(val):
    """True if val can’t be compared (None, nan, inf, str)."""
    return np.isnan(_to_float(val))

def icon_hi(v, a):
    v, a = _to_float(v), _to_float(a)
    if _bad(v) or _bad(a):
        return "❓"
    return "✅" if v >= a else "🟡" if v >= a * 0.8 else "🔴"

def icon_lo(v, a):
    v, a = _to_float(v), _to_float(a)
    if _bad(v) or _bad(a):
        return "❓"
    return "✅" if v <= a else "🟡" if v <= a * 1.1 else "🔴"

def icon_d2e(v, a):
    v, a = _to_float(v), _to_float(a)
    if _bad(v) or _bad(a):
        return "❓"
    return "✅" if v <= a else "🟡" if v <= 1.5 else "🔴"

def fmt_cap(val):
    if val is None or pd.isna(val):
        return "N/A"
    return (
        f"{val/1e9:.2f}B" if val >= 1e9 else
        f"{val/1e6:.2f}M" if val >= 1e6 else
        f"{val:.0f}"
    )

# ────────────────────────────────────────────────────────────
# 1⃣  Data load & sidebar
# ────────────────────────────────────────────────────────────
master_df = load_master()
name_df   = load_name_lookup()
df = pd.merge(master_df, name_df, on="Symbol", how="left")

st.sidebar.header("🏍️ Filter by")
sec_sel = st.sidebar.selectbox("Sector",  sorted(df["Big Sectors"].dropna().unique()))
ind_sel = st.sidebar.selectbox(
    "Industry", sorted(df[df["Big Sectors"] == sec_sel]["Industry"].dropna().unique())
)
rank_by  = st.sidebar.selectbox("Rank Top-10 by", ["Market Cap", "EPS", "ROE"])
show_all = st.sidebar.checkbox("Show **all** companies", value=False)

interp_threshold = st.sidebar.selectbox(
    "🎯 Green Criteria", ["All ✅", "≥4 ✅", "≥3 ✅", "≥2 ✅"], index=0
)
interp_cutoff = {"All ✅": 5, "≥4 ✅": 4, "≥3 ✅": 3, "≥2 ✅": 2}[interp_threshold]

scoped_df = df[(df["Big Sectors"] == sec_sel) & (df["Industry"] == ind_sel)]

# ────────────────────────────────────────────────────────────
# 2⃣  yFinance fetch
# ────────────────────────────────────────────────────────────
def fetch_metrics(sym: str) -> dict:
    try:
        info = yf.Ticker(f"{sym}.NS").info
        d2e_raw = info.get("debtToEquity")
        pm_raw  = info.get("profitMargins")
        return {
            "PE Ratio": info.get("trailingPE"),
            "EPS":      info.get("trailingEps"),
            "ROE":      info.get("returnOnEquity"),
            "Market Cap": info.get("marketCap"),
            # cap profit margin to 100 % and discard absurd values
            "Profit Margin": (
                None if pm_raw is None else
                min(pm_raw * 100, 100) if pm_raw < 1.5 else None
            ),
            "Debt to Equity": None if d2e_raw is None else d2e_raw / 100,
        }
    except Exception:
        return {k: None for k in
            ["PE Ratio", "EPS", "ROE", "Market Cap", "Profit Margin", "Debt to Equity"]}

# ────────────────────────────────────────────────────────────
# 3⃣  Industry averages
# ────────────────────────────────────────────────────────────
symbols = scoped_df["Symbol"].dropna().unique()
lookup  = {s: fetch_metrics(s) for s in symbols}
avg_df  = pd.DataFrame.from_dict(lookup, orient="index")

st.subheader(f"📊 Summary – {ind_sel}")
st.markdown(f"**Total companies in industry:** {len(scoped_df)}")

if not avg_df.empty:
    num_cols = ["PE Ratio", "EPS", "ROE", "Profit Margin", "Debt to Equity", "Market Cap"]
    avg_df[num_cols] = avg_df[num_cols].apply(pd.to_numeric, errors="coerce")
    clean_df = avg_df.replace([np.inf, -np.inf], np.nan)
    avg_vals = clean_df[num_cols].mean()

    cols = st.columns(6)
    cols[0].metric("Avg PE",        f"{avg_vals.get('PE Ratio', np.nan):.2f}")
    cols[1].metric("Avg EPS",       f"{avg_vals.get('EPS', np.nan):.2f}")
    cols[2].metric("Avg ROE",       f"{avg_vals.get('ROE', np.nan) * 100:.2f}%")
    cols[3].metric("Avg P. Margin", f"{avg_vals.get('Profit Margin', np.nan):.2f}%")
    cols[4].metric("Avg D/E",       f"{avg_vals.get('Debt to Equity', np.nan):.2f}")
    cols[5].metric("Avg MCap",      fmt_cap(avg_vals.get("Market Cap")))
else:
    st.info("No financial data available.")

# ────────────────────────────────────────────────────────────
# 4⃣  Company table & interpretation
# ──────────────────
    st.switch_page("pages/1_Fundamentals.py")
else:
    st.info("No company meets the selected green criteria.")
