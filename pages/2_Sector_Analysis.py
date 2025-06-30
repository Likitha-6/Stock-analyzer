import streamlit as st
import pandas as pd
import numpy as np

from common.sql import load_master
from common.data import load_name_lookup
from common.finance import human_market_cap

st.set_page_config(
    page_title="📂 Sector Analysis",
    page_icon="📂",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("📂 Sector & Industry Analysis")

# Load data
master_df = load_master()
name_df = load_name_lookup()
df = pd.merge(master_df, name_df, on="Symbol", how="left")

# Sidebar filters
st.sidebar.header("🏍️ Filter by")
sec_sel = st.sidebar.selectbox("Sector", sorted(df["Big Sectors"].dropna().unique()))
ind_sel = st.sidebar.selectbox("Industry", sorted(df[df["Big Sectors"] == sec_sel]["Industry"].dropna().unique()))
rank_by = st.sidebar.selectbox("Rank Top-10 by", ["Market Cap", "EPS", "ROE"])
show_all = st.sidebar.checkbox("Show **all** companies", value=False)
interp_threshold = st.sidebar.selectbox("🎯 Green Criteria", ["All ✅", "≥4 ✅", "≥3 ✅", "≥2 ✅"], index=0)
interp_cutoff = {"All ✅": 5, "≥4 ✅": 4, "≥3 ✅": 3, "≥2 ✅": 2}[interp_threshold]

# Scope the data
scoped_df = df[df["Industry"] == ind_sel].copy()

st.subheader(f"📊 Summary – {ind_sel}")
st.markdown(f"**Total companies in industry:** {len(scoped_df)}")

# Correct column name mapping
cols_to_use = {
    "PE": "PE Ratio",
    "EPS": "EPS",
    "ROE": "ROE",
    "Profit Margin": "ProfitMargin",
    "Debt to Equity": "DebtToEquity",
    "Market Cap": "MarketCap"
}

existing_cols = [v for v in cols_to_use.values() if v in scoped_df.columns]
scoped_df[existing_cols] = scoped_df[existing_cols].apply(pd.to_numeric, errors="coerce")

# Clean profit margin values
def clean_profit_margin(val):
    if pd.isna(val):
        return None
    return val * 100 if val < 1 else val

scoped_df["ProfitMarginCleaned"] = scoped_df[cols_to_use["Profit Margin"]].apply(clean_profit_margin)

# Average values
avg_vals = scoped_df[existing_cols].mean()
profit_margin_avg = scoped_df["ProfitMarginCleaned"].mean()

def fmt_cap(val):
    if val is None or pd.isna(val): return "N/A"
    return f"{val/1e9:.2f}B" if val >= 1e9 else f"{val/1e6:.2f}M" if val >= 1e6 else f"{val:.0f}"

def icon_hi(v, a):
    if pd.isna(v) or pd.isna(a): return "❓"
    return "✅" if v >= a else "🟡" if v >= a * 0.8 else "🔴"

def icon_lo(v, a):
    if pd.isna(v) or pd.isna(a): return "❓"
    return "✅" if v <= a else "🟡" if v <= a * 1.1 else "🔴"

def icon_d2e(v, a):
    if pd.isna(v) or pd.isna(a): return "❓"
    return "✅" if v <= a else "🟡" if v <= 1.5 else "🔴"

# Industry-level metrics
cols = st.columns(6)
cols[0].metric("Avg PE", f"{avg_vals.get(cols_to_use['PE'], np.nan):.2f}")
cols[1].metric("Avg EPS", f"{avg_vals.get(cols_to_use['EPS'], np.nan):.2f}")
cols[2].metric("Avg ROE", f"{avg_vals.get(cols_to_use['ROE'], np.nan) * 100:.2f}%")
cols[3].metric("Avg P. Margin", f"{profit_margin_avg:.2f}%")
cols[4].metric("Avg D/E", f"{avg_vals.get(cols_to_use['Debt to Equity'], np.nan):.2f}")
cols[5].metric("Avg MCap", fmt_cap(avg_vals.get(cols_to_use["Market Cap"])))

# Rank and interpret companies
sort_map = {
    "Market Cap": cols_to_use["Market Cap"],
    "EPS": cols_to_use["EPS"],
    "ROE": cols_to_use["ROE"]
}
sort_key = sort_map[rank_by]
scoped_df = scoped_df.sort_values(by=sort_key, ascending=False)
sel_df = scoped_df if show_all else scoped_df.head(10)

rows, qualified = [], []
name_lookup = name_df.set_index("Symbol")["Company Name"].to_dict()

for _, row in sel_df.iterrows():
    sym = row["Symbol"]
    profit_margin_clean = row["ProfitMarginCleaned"]
    r = {
        "Symbol": sym,
        "Company": name_lookup.get(sym, ""),
        "PE": row[cols_to_use["PE"]],
        "EPS": row[cols_to_use["EPS"]],
        "ROE %": None if pd.isna(row[cols_to_use["ROE"]]) else row[cols_to_use["ROE"]] * 100,
        "P. Margin %": profit_margin_clean,
        "D/E": row[cols_to_use["Debt to Equity"]],
        "MCap": fmt_cap(row[cols_to_use["Market Cap"]]),
        "Notes": "⚠️ Margin > 100%" if profit_margin_clean and profit_margin_clean > 100 else ""
    }
    icons = {
        "PE": icon_lo(row[cols_to_use["PE"]], avg_vals.get(cols_to_use["PE"])),
        "EPS": icon_hi(row[cols_to_use["EPS"]], avg_vals.get(cols_to_use["EPS"])),
        "ROE": icon_hi(row[cols_to_use["ROE"]], avg_vals.get(cols_to_use["ROE"])),
        "PM": icon_hi(profit_margin_clean, profit_margin_avg),
        "D/E": icon_d2e(row[cols_to_use["Debt to Equity"]], avg_vals.get(cols_to_use["Debt to Equity"])),
    }
    r["Interpretation"] = " | ".join([f"{k} {v}" for k, v in icons.items()])
    rows.append(r)

    if sum(v == "✅" for v in icons.values()) >= interp_cutoff:
        qualified.append(r)

st.markdown("---")
header_lbl = "📋 All Companies" if show_all else f"🔢 Top-10 – {rank_by}"
st.subheader(header_lbl)
st.dataframe(pd.DataFrame(rows), use_container_width=True)

# Qualified companies navigation
if qualified:
    qual_df = pd.DataFrame(qualified).reset_index(drop=True)
    st.markdown("---")
    st.subheader(f"🌟 Companies with ≥{interp_cutoff} Green Checks")
    st.dataframe(qual_df, use_container_width=True)

    csv = qual_df.to_csv(index=False).encode()
    st.download_button("⬇️ Download list as CSV", csv, f"green_stocks_{ind_sel}.csv")

    for _, r in qual_df.iterrows():
        if st.button(f"View Fundamentals →  {r['Company']} ({r['Symbol']})", key=f"q_{r['Symbol']}"):
            st.session_state.compare_symbol = r["Symbol"]
            st.session_state.qual_peers = qual_df["Symbol"].drop(r.name).tolist()
            st.session_state.from_sector_nav = True
            st.switch_page("pages/1_Fundamentals.py")
else:
    st.info("No company meets the selected green criteria.")

