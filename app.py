import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(page_title="Indian Stock Analyzer", page_icon="📊")
st.title("📈 Indian Stock Analyzer (Fundamentals)")

st.markdown("Enter an NSE stock ticker (e.g., RELIANCE, TCS, SBIN, INFY):")

# User input
ticker_input = st.text_input("Ticker Symbol", "RELIANCE")
ticker = ticker_input.upper().strip() + ".NS"

# Category classification
def get_market_cap_category(market_cap_inr):
    if market_cap_inr >= 2e12:
        return "Mega Cap"
    elif market_cap_inr >= 5e11:
        return "Large Cap"
    elif market_cap_inr >= 1e11:
        return "Mid Cap"
    elif market_cap_inr >= 1e10:
        return "Small Cap"
    else:
        return "Micro Cap"

# Icon based on category
def get_category_icon(category):
    if category in ["Mega Cap", "Large Cap"]:
        return "✅"
    elif category == "Mid Cap":
        return "🟡"
    elif category == "Small Cap":
        return "🟠"
    else:
        return "🔴"

# Main app logic
if ticker_input:
    try:
        stock = yf.Ticker(ticker)
        info = stock.get_info()

        # Market cap formatting
        market_cap = info.get("marketCap")
        if market_cap:
            market_cap_billion = round(market_cap / 1e9, 2)
            cap_category = get_market_cap_category(market_cap)
            cap_icon = get_category_icon(cap_category)
            market_cap_display = f"{market_cap_billion} B ({cap_category})"
            company_name_display = f"{cap_icon} {info.get('longName')}"
        else:
            market_cap_display = "N/A"
            company_name_display = info.get("longName")

        # Display table
        data = {
            "Company Name": company_name_display,
            "Sector": info.get("sector"),
            "Market Cap (Billion ₹)": market_cap_display,
            "P/E Ratio": info.get("trailingPE"),
            "EPS": info.get("trailingEps"),
            "Dividend Yield": info.get("dividendYield"),
            "Revenue (TTM)": info.get("totalRevenue"),
            "Net Income (TTM)": info.get("netIncomeToCommon"),
            "Profit Margin": info.get("profitMargins"),
            "Return on Equity (ROE)": info.get("returnOnEquity"),
            "Debt to Equity": info.get("debtToEquity"),
        }

        df = pd.DataFrame(data.items(), columns=["Metric", "Value"])
        st.dataframe(df)

    except Exception as e:
        st.error("⚠️ Could not fetch data. Please check the stock ticker symbol.")
