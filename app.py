import streamlit as st
import yfinance as yf
import pandas as pd

# Streamlit setup
st.set_page_config(page_title="Indian Stock Analyzer", page_icon="📊")
st.title("📈 Indian Stock Analyzer (Fundamentals)")

st.markdown("Enter an NSE stock ticker (e.g., RELIANCE, TCS, SBIN, INFY):")

ticker_input = st.text_input("Ticker Symbol", "RELIANCE")
ticker = ticker_input.upper().strip() + ".NS"

# Market cap interpretation
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

# Dividend Yield interpretation with color
def interpret_dividend_yield(dy):
    if dy is None:
        return "N/A"
    dy_percent = round(dy * 1, 2)
    if dy == 0:
        return f"{dy_percent}% 🔴 (No dividends)"
    elif dy < 1:
        return f"{dy_percent}% 🟠 (Low)"
    elif dy < 3:
        return f"{dy_percent}% ✅ (Moderate)"
    else:
        return f"{dy_percent}% ✅ (High)"

# Format INR value to Trillions
def format_in_trillions(value):
    if value is None:
        return "N/A"
    return f"₹{value / 1e12:.2f}T"

# Main app logic
if ticker_input:
    try:
        stock = yf.Ticker(ticker)
        info = stock.get_info()

        # Market Cap
        market_cap = info.get("marketCap")
        if market_cap:
            market_cap_billion = round(market_cap / 1e9, 2)
            cap_category, cap_meaning = get_market_cap_category(market_cap)
            cap_icon = get_category_icon(cap_category)
            market_cap_display = f"{market_cap_billion} B ({cap_icon} {cap_category} – {cap_meaning})"
        else:
            market_cap_display = "N/A"

        # Revenue and Net Income in Trillions
        revenue_trillion = format_in_trillions(info.get("totalRevenue"))
        net_income_trillion = format_in_trillions(info.get("netIncomeToCommon"))

        # Prepare data
        data = {
            "Company Name": info.get("longName"),
            "Sector": info.get("sector"),
            "Market Cap (Billion ₹)": market_cap_display,
            "P/E Ratio": info.get("trailingPE"),
            "EPS": info.get("trailingEps"),
            "Dividend Yield": interpret_dividend_yield(info.get("dividendYield")),
            "Revenue (TTM)": revenue_trillion,
            "Net Income (TTM)": net_income_trillion,
            "Profit Margin": info.get("profitMargins"),
            "Return on Equity (ROE)": info.get("returnOnEquity"),
            "Debt to Equity": info.get("debtToEquity"),
        }

        df = pd.DataFrame(data.items(), columns=["Metric", "Value"])
        st.dataframe(df.set_index("Metric"))

    except Exception as e:
        st.error("⚠️ Could not fetch data. Please check the stock ticker symbol.")
        st.exception(e)

