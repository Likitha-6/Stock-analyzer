import streamlit as st
import yfinance as yf
import pandas as pd

st.title("📊 Stock Fundamental Analyzer")

# Input from user
ticker = st.text_input("Enter NSE stock symbol (e.g., INFY.NS)", "INFY.NS")

# Fetch stock info
try:
    stock = yf.Ticker(ticker)
    info = stock.info

    st.markdown(f"### {info.get('longName', 'N/A')}")

    # Market Cap with Category
    market_cap = info.get("marketCap", 0)
    if market_cap >= 2_00_00_00_00_000:
        cap_category = "Mega Cap (Strong) ✅"
        color = "green"
    elif market_cap >= 40_00_00_00_000:
        cap_category = "Large Cap (Stable) ✅"
        color = "green"
    elif market_cap >= 8_00_00_00_000:
        cap_category = "Mid Cap (Emerging) 🟡"
        color = "orange"
    elif market_cap >= 1_00_00_00_000:
        cap_category = "Small Cap (Volatile) 🟠"
        color = "orange"
    else:
        cap_category = "Micro Cap (Risky) 🔴"
        color = "red"

    formatted_market_cap = f"₹{market_cap / 1_00_00_00_00_000:.2f}T"
    st.markdown(f"**Market Cap:** {formatted_market_cap}  \nCategory: `{cap_category}`")

    # Revenue & Net Income formatter
    def format_in_trillions(value):
        if not value:
            return "N/A"
        return f"₹{value / 1_00_00_00_00_000:.2f}T"

    revenue = info.get("totalRevenue")
    net_income = info.get("netIncome")

    st.markdown(f"**Revenue:** {format_in_trillions(revenue)}")
    st.markdown(f"**Net Income:** {format_in_trillions(net_income)}")

    # Dividend Yield with tick marks
    dividend_yield = info.get("dividendYield", 0)
    if dividend_yield is None:
        dividend_yield = 0

    if dividend_yield > 0.03:
        div_mark = "✅ Good"
    elif dividend_yield > 0:
        div_mark = "🟠 Low"
    else:
        div_mark = "🔴 None"

    st.markdown(f"**Dividend Yield:** {dividend_yield*100:.2f}% {div_mark}")

except Exception as e:
    st.error("Failed to fetch data. Please check the symbol or try again later.")
    st.exception(e)
