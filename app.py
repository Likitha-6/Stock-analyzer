import streamlit as st
import yfinance as yf
import pandas as pd
import requests

# Streamlit setup
st.set_page_config(page_title="Indian Stock Analyzer", page_icon="📊")
st.title("📈 Indian Stock Analyzer (Fundamentals)")

st.markdown("Enter an NSE stock ticker (e.g., RELIANCE, TCS, SBIN, INFY):")

compare_mode = st.checkbox("🔁 Compare Two Stocks (Optional)", value=False)

NEWS_API_KEY = "9802d49649194f36b4577221a7bd499c"

INDUSTRY_PE = {
    "Technology": 25.4,
    "Energy": 13.1,
    "Financial Services": 15.2,
    "Consumer Defensive": 28.3,
    "Healthcare": 24.5,
    "Utilities": 10.9,
    "Industrials": 20.7,
    "Consumer Cyclical": 22.1,
    "Basic Materials": 14.6,
    "Communication Services": 18.4,
    "Real Estate": 16.0,
}

def get_market_cap_category(market_cap_inr):
    if market_cap_inr >= 2e12:
        return "Mega Cap", "Strong, stable"
    elif market_cap_inr >= 5e11:
        return "Large Cap", "Strong, stable"
    elif market_cap_inr >= 1e11:
        return "Mid Cap", "Growing, moderate risk"
    elif market_cap_inr >= 1e10:
        return "Small Cap", "Emerging, higher risk"
    else:
        return "Micro Cap", "Very small, high risk"

def get_category_icon(category):
    return {
        "Mega Cap": "✅",
        "Large Cap": "✅",
        "Mid Cap": "🟡",
        "Small Cap": "🟠",
        "Micro Cap": "🔴"
    }.get(category, "")

def interpret_eps(eps):
    try:
        eps = float(eps)
    except (TypeError, ValueError):
        return "N/A"
    if eps is None:
        return "N/A"
    elif eps < 0:
        return f"{round(eps, 2)} 🔴 (Negative)"
    elif eps < 10:
        return f"{round(eps, 2)} 🟠 (Low)"
    else:
        return f"{round(eps, 2)} ✅"

def interpret_pe_with_industry(pe, industry_pe):
    if pe is None or industry_pe is None:
        return "N/A"
    diff = pe - industry_pe
    if diff > 10:
        interpretation = "🔺 Overvalued"
    elif diff > 2:
        interpretation = "🟠 Slightly Overvalued"
    elif diff < -2:
        interpretation = "✅ Undervalued"
    else:
        interpretation = "✅ Fairly Priced"
    return f"{pe} vs {industry_pe} ({interpretation})"

def interpret_dividend_yield(dy):
    if dy is None:
        return f"{0}% 🔴 (No dividends)"
    dy_percent = round(dy * 1, 2)
    if dy == 0:
        return f"{dy_percent}% 🔴 (No dividends)"
    elif dy < 1:
        return f"{dy_percent}% 🟠 (Low)"
    elif dy < 3:
        return f"{dy_percent}% ✅ (Moderate)"
    else:
        return f"{dy_percent}% ✅ (High)"

def interpret_roe(roe):
    if roe is None:
        return "N/A"
    roe_percent = round(roe * 100, 2)
    if roe_percent < 10:
        return f"{roe_percent}% 🟠 (Low)"
    elif roe_percent < 20:
        return f"{roe_percent}% 🟡 (Moderate)"
    else:
        return f"{roe_percent}% ✅ (High)"

def interpret_de_ratio(de):
    de = round(de / 100, 2) if de else 0
    if de is None:
        return "N/A"
    elif de < 1:
        return f"{de} ✅ (Low Debt)"
    elif de > 1 and de < 2:
        return f"{de} 🟡 (Moderate)"
    else:
        return f"{de} 🔴 (High Risk)"

# Use single or comparison mode
if compare_mode:
    symbol1 = st.text_input("Enter First Stock Symbol", "RELIANCE").upper().strip()
    symbol2 = st.text_input("Enter Second Stock Symbol", "INFY").upper().strip()

    ticker1 = yf.Ticker(symbol1 + ".NS")
    ticker2 = yf.Ticker(symbol2 + ".NS")

    try:
        info1 = ticker1.get_info()
        info2 = ticker2.get_info()

        col1, col2 = st.columns(2)
        with col1:
            st.subheader(f"📊 {info1.get('longName')} ({symbol1})")
            st.write("**Price:**", info1.get("currentPrice"))
            st.write("**P/E Ratio:**", info1.get("trailingPE"))
            st.write("**EPS:**", interpret_eps(info1.get("trailingEps")))
            st.write("**ROE:**", interpret_roe(info1.get("returnOnEquity")))
            st.write("**Dividend Yield:**", interpret_dividend_yield(info1.get("dividendYield")))

        with col2:
            st.subheader(f"📊 {info2.get('longName')} ({symbol2})")
            st.write("**Price:**", info2.get("currentPrice"))
            st.write("**P/E Ratio:**", info2.get("trailingPE"))
            st.write("**EPS:**", interpret_eps(info2.get("trailingEps")))
            st.write("**ROE:**", interpret_roe(info2.get("returnOnEquity")))
            st.write("**Dividend Yield:**", interpret_dividend_yield(info2.get("dividendYield")))

        st.subheader("📈 Price Comparison")
        period = st.selectbox("Select period for comparison", ["1mo", "3mo", "6mo", "1y", "5y", "max"], index=3)

        hist1 = ticker1.history(period=period)
        hist2 = ticker2.history(period=period)

        if not hist1.empty and not hist2.empty:
            price_df = pd.DataFrame({
                symbol1: hist1["Close"],
                symbol2: hist2["Close"]
            })
            st.line_chart(price_df)
        else:
            st.warning("Could not load historical data for one or both tickers.")

    except Exception as e:
        st.error("⚠️ Error comparing stocks. Please check the symbols and try again.")

else:
    ticker_input = st.text_input("Ticker Symbol", "RELIANCE")
    ticker = ticker_input.upper().strip() + ".NS"
    # ... [Insert original single stock analysis logic here from your current app] ...
