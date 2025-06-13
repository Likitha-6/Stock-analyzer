import streamlit as st
import yfinance as yf
import pandas as pd

st.title("📊 Stock Fundamental Analyzer")

ticker = st.text_input("Enter NSE stock symbol (e.g., INFY.NS)", "INFY.NS")

def format_in_trillions(value):
    if not value:
        return "N/A"
    return f"₹{value / 1_00_00_00_00_000:.2f}T"

if ticker:
    try:
        stock = yf.Ticker(ticker)
        info = stock.info

        name = info.get("longName", "N/A")
        market_cap = info.get("marketCap", 0)
        revenue = info.get("totalRevenue")
        net_income = info.get("netIncome")
        pe_ratio = info.get("trailingPE", "N/A")
        dividend_yield = info.get("dividendYield", 0) or 0

        # Interpretations
        if market_cap >= 2_00_00_00_00_000:
            cap_category = "Mega Cap (Strong) ✅"
        elif market_cap >= 40_00_00_00_000:
            cap_category = "Large Cap (Stable) ✅"
        elif market_cap >= 8_00_00_00_000:
            cap_category = "Mid Cap (Emerging) 🟡"
        elif market_cap >= 1_00_00_00_000:
            cap_category = "Small Cap (Volatile) 🟠"
        else:
            cap_category = "Micro Cap (Risky) 🔴"

        if dividend_yield > 0.03:
            dividend_note = f"{dividend_yield*100:.2f}% ✅ Good"
        elif dividend_yield > 0:
            dividend_note = f"{dividend_yield*100:.2f}% 🟠 Low"
        else:
            dividend_note = f"{dividend_yield*100:.2f}% 🔴 None"

        data = {
            "Metric": [
                "Company Name",
                "Market Cap",
                "Market Cap Category",
                "Revenue",
                "Net Income",
                "P/E Ratio",
                "Dividend Yield"
            ],
            "Value": [
                name,
                f"₹{market_cap / 1_00_00_00_00_000:.2f}T" if market_cap else "N/A",
                cap_category,
                format_in_trillions(revenue),
                format_in_trillions(net_income),
                f"{pe_ratio}" if pe_ratio else "N/A",
                dividend_note
            ]
        }

        df = pd.DataFrame(data)
        st.table(df)

    except Exception as e:
        st.error("❌ Error fetching data.")
        st.exception(e)
