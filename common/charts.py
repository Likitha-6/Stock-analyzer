import yfinance as yf
import altair as alt
import pandas as pd


def _price_chart(symbol: str, period: str):
    """
    Generates an Altair line chart for historical closing prices of a stock.
    Automatically adjusts for splits.
    """
    hist = yf.Ticker(f"{symbol}.NS").history(period=period, auto_adjust=True)
    if hist.empty:
        return None
    price_df = hist[["Close"]].copy()
    price_df.index.name = "Date"

    chart = (
        alt.Chart(price_df.reset_index())
        .mark_line()
        .encode(
            x=alt.X("Date:T", title="Date"),
            y=alt.Y(
                "Close:Q",
                title="Close (\u20B9)",
                scale=alt.Scale(domain=[price_df["Close"].min(), price_df["Close"].max()])
            )
        )
        .properties(height=300)
    )
    return chart


def _rev_pm_fcf_frames(symbol: str):
    """
    Fetches and prepares DataFrames for Revenue, Profit Margin, and Free Cash Flow
    for charting.
    """
    tkr = yf.Ticker(f"{symbol}.NS")
    fin = tkr.financials.T
    if fin.empty:
        return None, None, None

    fin.index = pd.to_datetime(fin.index).year
    fin = fin.sort_index()

    rev_df = (fin["Total Revenue"] / 1e7).to_frame("Revenue (\u20B9 Cr)") if "Total Revenue" in fin.columns else None

    pm_df = None
    if {"Net Income", "Total Revenue"}.issubset(fin.columns) and not fin["Total Revenue"].eq(0).any():
        pm_df = ((fin["Net Income"] / fin["Total Revenue"]) * 100).to_frame("Profit Margin (%)")

    cf = tkr.cashflow
    fcf_df = None
    if not cf.empty and "Free Cash Flow" in cf.index:
        fcf = (cf.loc["Free Cash Flow"] / 1e7).dropna()
        if not fcf.empty:
            fcf.index = pd.to_datetime(fcf.index).year
            fcf_df = fcf.to_frame("Free Cash Flow (\u20B9 Cr)")

    return rev_df, pm_df, fcf_df
