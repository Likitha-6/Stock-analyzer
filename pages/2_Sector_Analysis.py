# pages/3_📂 Sector Analysis.py
import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf

from common.data import load_master, load_name_lookup
from common.finance import human_market_cap

st.set_page_config(
    page_title="📂 Sector Analysis",
    page_icon="📂",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("📂 Sector & Industry Analysis")

# ────────────────────────────────────────────────────────────
# 1⃣  Data load & sidebar
# ────────────────────────────────────────────────────────────
master_df = load_master()
name_df   = load_name_lookup()

df = pd.merge(master_df, name_df, on="Symbol", how="left")

st.sidebar.header("🏍️ Filter by")
sec_sel = st.sidebar.selectbox("Sector", sorted(df["Big Sectors"].dropna().unique()))
ind_sel = st.sidebar.selectbox(
    "Industry",
    sorted(df[df["Big Sectors"] == sec_sel]["Industry"].dropna().unique())
)
rank_by  = st.sidebar.selectbox("Rank Top-10 by", ["Market Cap", "EPS", "ROE"], index=0)
show_all = st.sidebar.checkbox("Show **all** companies", value=False)

interp_threshold = st.sidebar.selectbox(
    "🎯 Green Criteria",
    ["All ✅", "≥4 ✅", "≥3 ✅", "≥2 ✅"],
    index=0
)
interp_cutoff = {"All ✅": 5, "≥4 ✅": 4, "≥3 ✅": 3, "≥2 ✅": 2}[interp_threshold]

scoped_df = df[(df["Big Sectors"] == sec_sel) & (df["Industry"] == ind_sel)]

# ────────────────────────────────────────────────────────────
# 2⃣  yfinance helpers
# ────────────────────────────────────────────────────────────

def fetch_metrics(sym: str) -> dict:
    try:
        info = yf.Ticker(f"{sym}.NS").info
        d2e_raw = info.get("debtToEquity")
        pm_raw  = info.get("profitMargins")
        return {
            "PE Ratio":      info.get("trailingPE"),
            "EPS":           info.get("trailingEps"),
            "ROE":           info.get("returnOnEquity"),
            "Market Cap":    info.get("marketCap"),
            "Profit Margin": None if pm_raw is None else pm_raw * 100,
            "Debt to Equity":None if d2e_raw is None else d2e_raw / 100,
        }
    except Exception:
        return {
            "PE Ratio": None, "EPS": None, "ROE": None,
            "Market Cap": None, "Profit Margin": None, "Debt to Equity": None,
        }

def fmt_cap(val):
    if val is None or pd.isna(val):
        return "N/A"
    return f"{val/1e9:.2f}B" if val >= 1e9 else f"{val/1e6:.2f}M" if val >= 1e6 else f"{val:.0f}"

# ────────────────────────────────────────────────────────────
# 3⃣  Industry averages & summary
# ────────────────────────────────────────────────────────────

symbols = scoped_df["Symbol"].dropna().unique()
lookup  = {s: fetch_metrics(s) for s in symbols}
avg_df  = pd.DataFrame.from_dict(lookup, orient="index")

st.subheader(f"📊 Summary – {ind_sel}")
st.markdown(f"**Total companies in industry:** {len(scoped_df)}")

if not avg_df.empty:
    avg_vals = avg_df.mean(numeric_only=True)
    cols = st.columns(6)
    cols[0].metric("Avg PE", f"{avg_vals['PE Ratio']:.2f}")
    cols[1].metric("Avg EPS", f"{avg_vals['EPS']:.2f}")
    cols[2].metric("Avg ROE", f"{avg_vals['ROE']*100:.2f}%")
    cols[3].metric("Avg P. Margin", f"{avg_vals['Profit Margin']:.2f}%")
    cols[4].metric("Avg D/E", f"{avg_vals['Debt to Equity']:.2f}")
    cols[5].metric("Avg MCap", fmt_cap(avg_vals["Market Cap"]))
else:
    st.info("No financial data available.")

# ────────────────────────────────────────────────────────────
# 4⃣  Company table & interpretation
# ────────────────────────────────────────────────────────────

sort_key = {"Market Cap": "Market Cap", "EPS": "EPS", "ROE": "ROE"}[rank_by]
ranked   = sorted(symbols, key=lambda s: lookup[s].get(sort_key) or 0, reverse=True)
sel_syms = ranked if show_all else ranked[:10]
header_lbl = (
    f"📋 All Companies in {ind_sel} (sorted by {rank_by})"
    if show_all else
    f"🔢 Top-10 ({rank_by})"
)

rows, qualified = [], []
for sym in sel_syms:
    m = lookup[sym]
    row = {
        "Symbol": sym,
        "Company": name_df.set_index("Symbol").get("Company Name", {}).get(sym, ""),
        "PE": m["PE Ratio"],
        "EPS": m["EPS"],
        "ROE %": None if m["ROE"] is None else m["ROE"] * 100,
        "P. Margin %": m["Profit Margin"],
        "D/E": m["Debt to Equity"],
        "MCap": fmt_cap(m["Market Cap"]),
    }

    def _bad(val):
        return val is None or pd.isna(val)

    def icon_hi(v, a):
        if _bad(v) or _bad(a):
            return "❓"
        return "✅" if v >= a else "🟡" if v >= a * 0.8 else "🔴"

    def icon_lo(v, a):
        if _bad(v) or _bad(a):
            return "❓"
        return "✅" if v <= a else "🟡" if v <= a * 1.1 else "🔴"

    def icon_d2e(v, a):
        if _bad(v) or _bad(a):
            return "❓"
        return "✅" if v <= a else "🟡" if v <= 1.5 else "🔴"

    icons = {
        "PE":  icon_lo(m["PE Ratio"],      avg_vals["PE Ratio"]),
        "EPS": icon_hi(m["EPS"],           avg_vals["EPS"]),
        "ROE": icon_hi(m["ROE"],           avg_vals["ROE"]),
        "PM":  icon_hi(m["Profit Margin"], avg_vals["Profit Margin"]),
        "D/E": icon_d2e(m["Debt to Equity"], avg_vals["Debt to Equity"]),
    }
    row["Interpretation"] = " | ".join([f"{k} {v}" for k, v in icons.items()])
    rows.append(row)

    if sum(v == "✅" for v in icons.values()) >= interp_cutoff:
        qualified.append(row)

st.markdown("---")
st.subheader(header_lbl)
st.dataframe(pd.DataFrame(rows).reset_index(drop=True), use_container_width=True)

# ────────────────────────────────────────────────────────────
# 5⃣  Qualified (green) companies → Fundamentals navigation
# ────────────────────────────────────────────────────────────
if qualified:
    st.markdown("---")
    st.subheader(f"🌟 Companies with ≥{interp_cutoff} Green Checks")
    for r in qualified:
        if st.button(f"Compare {r['Company']} ({r['Symbol']}) on Fundamentals"):
    from common.peer_finder import top_peers
    peer_df = top_peers(r["Symbol"], df, k=5)
    st.session_state.qual_peers = peer_df["Symbol"].tolist()
    st.session_state.compare_symbol = r["Symbol"]
    st.session_state.from_sector_nav = True
    st.switch_page("pages/1_Fundamentals.py")
            st.session_state.compare_symbol  = r["Symbol"]
            st.session_state.qual_peers      = [row["Symbol"] for row in qualified if row["Symbol"] != r["Symbol"]]
            st.session_state.from_sector_nav = True
            st.switch_page("pages/1_Fundamentals.py")
else:
    st.info("No company meets the selected green criteria.")

