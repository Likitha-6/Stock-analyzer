"""
common.finance
~~~~~~~~~~~~~~
Financial-data helpers for the Indian Stock Analyzer.

Functions
---------
_fetch_core_metrics(symbol: str) -> dict
    Grab key ratios + meta-data for a single NSE ticker.
get_industry_averages(industry, master_df, max_peers=None) -> dict
    Mean of each metric across peers in the same industry.
get_stock_description(symbol) -> str
    Long business summary from Yahoo Finance.
market_cap_label(mcap) -> str
    Mega / Large / Mid / Small / Micro or N/A.
human_market_cap(mcap) -> str
    Pretty-prints market-cap in T, B, M.
val_with_ind_avg(metric, value, ind_avg) -> str
    “123.4 (Ind Avg: 98.7)” helper.
interpret(metric, value, ind_avg) -> ✅/🟡/🔴
    Simple emoji scoring vs. industry average.
"""

from __future__ import annotations

from typing import Optional

import numpy as np
import pandas as pd
import streamlit as st
import yfinance as yf

# ────────────────────────────────────────────────────────────────────
# 1.  Core single-stock metrics
# ────────────────────────────────────────────────────────────────────


@st.cache_data(ttl=60 * 60 * 6, show_spinner=False)
def _fetch_core_metrics(symbol: str) -> dict:
    """
    Fetch trailing PE, EPS, margin, etc. for *symbol* (no '.NS' suffix).
    """
    try:
        tkr = yf.Ticker(f"{symbol}.NS")
        info = tkr.info or {}
        raw_fcf = info.get("freeCashflow")

        if raw_fcf is None:
            cf = tkr.cashflow
            if not cf.empty and "Free Cash Flow" in cf.index:
                raw_fcf = cf.loc["Free Cash Flow"].iloc[0]

    except Exception as exc:
        # Handle rate-limit separately so caller may decide what to do.
        if "rate" in str(exc).lower():
            raise RuntimeError("Yahoo Finance rate-limit hit") from exc
        info, raw_fcf = {}, None

    return {
        "PE Ratio": info.get("trailingPE"),
        "EPS": info.get("trailingEps"),
        "Profit Margin": info.get("profitMargins"),
        "ROE": info.get("returnOnEquity"),
        "Debt to Equity": info.get("debtToEquity"),
        "Dividend Yield": info.get("dividendYield"),
        "Free Cash Flow": raw_fcf,
        # meta for UI
        "_company": info.get("longName"),
        "_sector": info.get("sector"),
        "_market_cap": info.get("marketCap"),
        "_price": info.get("currentPrice"),
    }


# ────────────────────────────────────────────────────────────────────
# 2.  Industry averages
# ────────────────────────────────────────────────────────────────────


@st.cache_data(ttl=60 * 60 * 6, show_spinner=True)
def get_industry_averages(
    industry: str,
    master_df: pd.DataFrame,
    max_peers: Optional[int] = None,
) -> dict:
    """
    Compute mean value of each metric across all tickers in *industry*.
    """
    peer_syms = (
        master_df.loc[master_df["Industry"] == industry, "Symbol"]
        .head(max_peers)  # head(None) is safe
        .tolist()
    )

    buckets = {m: [] for m in [
        "PE Ratio",
        "EPS",
        "Profit Margin",
        "ROE",
        "Debt to Equity",
        "Dividend Yield",
        "Free Cash Flow",
    ]}

    for sym in peer_syms:
        try:
            data = _fetch_core_metrics(sym)  # cached – usually instant
        except RuntimeError:
            st.warning("⚠️ Yahoo Finance rate-limit reached – partial peer data.")
            break
        for m, v in data.items():
            if m.startswith("_"):
                continue
            if v is not None and isinstance(v, (int, float)) and np.isfinite(v):
                buckets[m].append(float(v))

    return {
        m: (None if not vals else round(float(np.mean(vals)), 2))
        for m, vals in buckets.items()
    }


# ────────────────────────────────────────────────────────────────────
# 3.  Utility helpers used by UI code
# ────────────────────────────────────────────────────────────────────


def get_stock_description(symbol: str) -> str:
    try:
        return yf.Ticker(f"{symbol}.NS").info.get(
            "longBusinessSummary", "No description available."
        )
    except Exception:
        return "Description could not be fetched at this time."


def market_cap_label(mc: Optional[float]) -> str:
    if mc is None:
        return "N/A"
    if mc >= 2e12:
        return "Mega Cap"
    if mc >= 5e11:
        return "Large Cap"
    if mc >= 1e11:
        return "Mid Cap"
    if mc >= 1e10:
        return "Small Cap"
    return "Micro Cap"


def human_market_cap(mc: Optional[float]) -> str:
    if mc is None:
        return "N/A"
    if mc >= 1e12:
        return f"{mc / 1e12:.2f} T"
    if mc >= 1e9:
        return f"{mc / 1e9:.2f} B"
    if mc >= 1e6:
        return f"{mc / 1e6:.2f} M"
    return f"{mc:.0f}"


def val_with_ind_avg(metric: str, raw_val: Optional[float], ind_avg: Optional[float]) -> str:
    if raw_val is None:
        return "N/A"

    # Unit conversions for display only
    if metric == "Debt to Equity":
        raw_val /= 100
        ind_avg = ind_avg / 100 if ind_avg is not None else None
    elif metric == "Free Cash Flow":
        raw_val /= 1e7
        ind_avg = ind_avg / 1e7 if ind_avg is not None else None
    elif metric in ("Profit Margin", "ROE"):
        raw_val *= 100
        ind_avg = ind_avg * 100 if ind_avg is not None else None

    base = f"{raw_val:.2f}"
    avg = f"{ind_avg:.2f}" if ind_avg is not None else "N/A"
    return f"{base} (Ind Avg: {avg})"


def interpret(metric: str, value: Optional[float], ind_avg: Optional[float]) -> str:
    """
    Return ✅ (good), 🟡 (slightly bad), 🔴 (bad) vs. industry average.
    """
    if (
        value is None
        or ind_avg is None
        or not isinstance(value, (int, float))
        or not isinstance(ind_avg, (int, float))
        or not np.isfinite(value)
        or not np.isfinite(ind_avg)
    ):
        return ""

    # Align units for fair comparison
    if metric == "Free Cash Flow":
        value /= 1e7
        ind_avg /= 1e7
    elif metric in ("Profit Margin", "ROE"):
        value *= 100
        ind_avg *= 100
    elif metric == "Debt to Equity":
        value /= 100
        ind_avg /= 100

    if ind_avg == 0:
        return ""

    delta_pct = (value - ind_avg) / abs(ind_avg) * 100
    lower_is_better = metric in ("Debt to Equity", "PE Ratio")

    if lower_is_better:
        if delta_pct <= 0:
            return "✅"
        if delta_pct >= 10:
            return "🔴"
        return "🟡"
    else:
        if delta_pct >= 0:
            return "✅"
        if delta_pct <= -10:
            return "🔴"
        return "🟡"
