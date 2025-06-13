import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(page_title="Indian Stock Analyzer", page_icon="📊")
st.title("📈 Indian Stock Analyzer (Fundamentals)")

st.markdown("Enter an NSE stock ticker (e.g., RELIANCE, TCS, SBIN, INFY):")

ticker_input = st.text_input("Ticker Symbol", "RELIANCE")
ticker = ticker_input.upper().strip() + ".NS"

if ticker_input:
    try:
        stock = yf.Ticker(ticker)
        info = stock.get_info()

        # Format market cap in billions
        market_cap = info.get("marketCap")
        if market_cap:
            market_cap_billion = round(market_cap / 1e9, 2)
            market_cap_display = f"{market_cap_billion} B"
        else:
            market_cap_display = "N/A"

        # Build data dictionary
        data = {
            "Company Name": info.get("longName"),
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

