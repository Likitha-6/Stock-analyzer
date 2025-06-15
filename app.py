import streamlit as st
import yfinance as yf
import pandas as pd
import requests

# Streamlit setup
st.set_page_config(page_title="Indian Stock Analyzer", page_icon="📊")
st.title("📈 Indian Stock Analyzer (Fundamentals)")

st.markdown("Enter an NSE stock ticker (e.g., RELIANCE, TCS, SBIN, INFY):")

# ✨ Comparison Feature Start
compare_mode = st.checkbox("🔁 Compare with another stock")
ticker_input = st.text_input("Primary Ticker Symbol", "RELIANCE")
second_ticker_input = None

if compare_mode:
    second_ticker_input = st.text_input("Secondary Ticker Symbol (for comparison)", "TCS")
# ✨ Comparison Feature End

# Helper Functions (same as before)
# ... [keep all helper functions like get_market_cap_category, interpret_eps, etc.]

# Fetch and display data for a single stock
def fetch_stock_data(ticker_input):
    ticker = ticker_input.upper().strip() + ".NS"
    try:
        stock = yf.Ticker(ticker)
        info = stock.get_info()
        sector = info.get("sector")
        industry_pe = INDUSTRY_PE.get(sector)
        stock_pe = info.get("trailingPE")
        current_price = info.get("currentPrice")

        market_cap = info.get("marketCap")
        if market_cap:
            market_cap_billion = round(market_cap / 1e9, 2)
            cap_category, cap_meaning = get_market_cap_category(market_cap)
            cap_icon = get_category_icon(cap_category)
            market_cap_display = f"{market_cap_billion} B ({cap_icon} {cap_category} – {cap_meaning})"
        else:
            market_cap_display = "N/A"

        hist = stock.history(period="max")
        if not hist.empty:
            all_time_high = round(hist["High"].max(), 2)
        else:
            all_time_high = "N/A"
        if all_time_high != "N/A" and current_price:
            percent_from_ath = round(((current_price - all_time_high) / all_time_high) * 100, 2)
            if percent_from_ath >= 0:
                ath_change_display = f"{all_time_high} (+{percent_from_ath}%) 🟢"
            else:
                ath_change_display = f"{all_time_high} ({percent_from_ath}%) 🔻"
        else:
            ath_change_display = "N/A"

        profit_margin = info.get("profitMargins")
        if profit_margin is None:
            profit_margin_percent = "N/A"
        elif profit_margin < 0:
            profit_margin_percent = f"{round(profit_margin * 100, 2)}% ❌ (Loss-Making)"
        else:
            profit_margin_percent = f"{round(profit_margin * 100, 2)}%"

        data = {
            "Company Name": info.get("longName"),
            "Sector": sector,
            "Current Price (₹)": current_price,
            "All-Time High (₹)": ath_change_display,
            "Market Cap (Billion ₹)": market_cap_display,
            "P/E Ratio": stock_pe,
            "P/E vs Industry": interpret_pe_with_industry(stock_pe, industry_pe),
            "EPS": interpret_eps(info.get("trailingEps")),
            "Dividend Yield": interpret_dividend_yield(info.get("dividendYield")),
            "Profit Margin": profit_margin_percent,
            "Return on Equity (ROE)": interpret_roe(info.get("returnOnEquity")),
            "Debt to Equity": interpret_de_ratio(info.get("debtToEquity")),
        }

        return pd.DataFrame(data.items(), columns=["Metric", "Value"]), info.get("longName", ticker_input)
    except Exception as e:
        st.error(f"⚠️ Could not fetch data for {ticker_input.upper()}.")
        return None, ticker_input.upper()

# ✨ Conditional UI Based on Compare Mode
if ticker_input:
    df1, name1 = fetch_stock_data(ticker_input)

    if compare_mode and second_ticker_input:
        df2, name2 = fetch_stock_data(second_ticker_input)

        if df1 is not None and df2 is not None:
            st.subheader("📊 Comparison Table")
            combined_df = pd.merge(df1, df2, on="Metric", how="outer", suffixes=(f" ({name1})", f" ({name2})"))
            st.dataframe(combined_df.set_index("Metric"))
    elif df1 is not None:
        st.subheader("📊 Stock Metrics")
        st.dataframe(df1.set_index("Metric"))

# You can continue with historical charts, news, etc., only for the primary ticker if needed.
