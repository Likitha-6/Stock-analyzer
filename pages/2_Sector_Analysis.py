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
scoped_df[cols_to_use["Debt to Equity"]] = pd.to_numeric(round(scoped_df[cols_to_use["Debt to Equity"]]/100,2), errors="coerce")


from common.finance import get_industry_averages

# Get cleaned industry-level medians from shared logic
avg_vals = get_industry_averages(ind_sel, df)


# Cleaned versions (same as your old logic)
de = avg_vals.get("Debt to Equity")
pm = avg_vals.get("Profit Margin")

if de is not None and de > 5:  # Heuristic: anything above 5 is probably in %
    avg_vals["Debt to Equity"] = de / 100

if pm is not None and pm < 1:  # Heuristic: 0.18 => 18%
    profit_margin_avg = pm * 100
else:
    profit_margin_avg = pm

avg_vals["ProfitMarginCleaned"] = profit_margin_avg




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
cols[4].metric("Avg D/E", f"{avg_vals.get('Debt to Equity', np.nan):.2f}")

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
    pm_val = row.get(cols_to_use["Profit Margin"])
    profit_margin_clean = pm_val * 100 if pd.notna(pm_val) and pm_val < 1 else pm_val
    de_val = pd.to_numeric(row.get(cols_to_use["Debt to Equity"]), errors="coerce")
    de_avg = pd.to_numeric(avg_vals.get(cols_to_use["Debt to Equity"]), errors="coerce")



    r = {
        "Symbol": sym,
        "Company": name_lookup.get(sym, ""),
        "PE": row[cols_to_use["PE"]],
        "EPS": row[cols_to_use["EPS"]],
        "ROE %": None if pd.isna(row[cols_to_use["ROE"]]) else row[cols_to_use["ROE"]] * 100,
        "P. Margin %": profit_margin_clean,
        "D/E": de_val,
        "MCap": fmt_cap(row[cols_to_use["Market Cap"]]),
        #"Notes": "⚠️ Margin > 100%" if profit_margin_clean and profit_margin_clean > 100 else ""
    }
    icons = {
        "PE": icon_lo(row[cols_to_use["PE"]], avg_vals.get(cols_to_use["PE"])),
        "EPS": icon_hi(row[cols_to_use["EPS"]], avg_vals.get(cols_to_use["EPS"])),
        "ROE": icon_hi(row[cols_to_use["ROE"]], avg_vals.get(cols_to_use["ROE"])),
        "PM": icon_hi(profit_margin_clean, profit_margin_avg),
        "D/E": icon_d2e(de_val, de_avg),

    }
    r["Interpretation"] = " | ".join([f"{k} {v}" for k, v in icons.items()])
    rows.append(r)

    if sum(v == "✅" for v in icons.values()) >= interp_cutoff:
        qualified.append(r)

st.markdown("---")
header_lbl = "📋 All Companies" if show_all else f"🔢 Top-10 – {rank_by}"
st.subheader(header_lbl)
df = pd.DataFrame(rows)
df.index = df.index + 1  # Start index from 1
st.dataframe(df, use_container_width=True)


# Qualified companies navigation
if qualified:
    qual_df = pd.DataFrame(qualified).reset_index(drop=True)
    st.markdown("---")
    st.subheader(f"🌟 Companies with ≥{interp_cutoff} Green Checks")
    qual_df.index = qual_df.index + 1
    st.dataframe(qual_df, use_container_width=True)


   
else:
    st.info("No company meets the selected green criteria.")

