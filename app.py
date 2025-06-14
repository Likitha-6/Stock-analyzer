import streamlit as st
import yfinance as yf
import pandas as pd

# Streamlit setup
st.set_page_config(page_title="Indian Stock Analyzer", page_icon="📊")
st.title("📈 Indian Stock Analyzer (Fundamentals)")

st.markdown("Enter an NSE stock ticker (e.g., RELIANCE, TCS, SBIN, INFY):")

ticker_input = st.text_input("Ticker Symbol", "RELIANCE")
ticker = ticker_input.upper().strip() + ".NS"


INDUSTRY_PE = {
    "Information Technology": 25.4,
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
    # Add more as needed
}

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
    elif de < 0.5:
        return f"{de} ✅ (Low Debt)"
    elif de < 1.5:
        return f"{de} 🟡 (Moderate)"
    else:
        return f"{de} 🔴 (High Risk)"

# Main app logic
if ticker_input:
    try:
        stock = yf.Ticker(ticker)
        info = stock.get_info()

        market_cap = info.get("marketCap")
        if market_cap:
            market_cap_billion = round(market_cap / 1e9, 2)
            cap_category, cap_meaning = get_market_cap_category(market_cap)
            cap_icon = get_category_icon(cap_category)
            market_cap_display = f"{market_cap_billion} B ({cap_icon} {cap_category} – {cap_meaning})"
        else:
            market_cap_display = "N/A"
        # Get All-Time High (ATH)
        hist = stock.history(period="max")
        if not hist.empty:
            all_time_high = round(hist["High"].max(), 2)
        else:
            all_time_high = "N/A"


        revenue = info.get("totalRevenue")
        net_income = info.get("netIncomeToCommon")
        revenue_billion = f"{round(revenue / 1e9, 2)} B" if revenue else "N/A"
        net_income_billion = f"{round(net_income / 1e9, 2)} B" if net_income else "N/A"
        industry_pe = INDUSTRY_PE.get(sector)


        # Convert profit margin to % format
        profit_margin = info.get("profitMargins")
        profit_margin_percent = f"{round(profit_margin * 100, 2)}%" if profit_margin else "N/A"

        data = {
            "Company Name": info.get("longName"),
            "Sector": info.get("sector"),
            "Current Price (₹)": info.get("currentPrice"),
            "All-Time High (₹)": all_time_high,
            "Market Cap (Billion ₹)": market_cap_display,
            "P/E Ratio": info.get("trailingPE"),
            "Industry_PE":industry_pe
            "EPS": info.get("trailingEps"),
            "Dividend Yield": interpret_dividend_yield(info.get("dividendYield")),
            "Revenue (TTM)": revenue_billion,
            "Net Income (TTM)": net_income_billion,
            "Profit Margin": profit_margin_percent,
            "Return on Equity (ROE)": interpret_roe(info.get("returnOnEquity")),
            "Debt to Equity": interpret_de_ratio(info.get("debtToEquity")),
        }

        df = pd.DataFrame(data.items(), columns=["Metric", "Value"])
        st.dataframe(df.set_index("Metric"))

        # 📉 Stock Price Chart
        st.subheader("📉 Historical Stock Price Chart")
        
        try:
            period = st.selectbox("Select period for price chart:", ["1mo", "3mo", "6mo", "1y", "5y", "max"], index=4)
            hist_price = stock.history(period=period)
              # You can change to "1y", "max", etc.
            if not hist_price.empty:
                st.line_chart(hist_price["Close"].round(2))
            else:
                st.warning("No historical stock data available.")
        except Exception as e:
            st.warning(f"Could not load stock price chart. Error: {e}")


        # 📊 Historical Profit After Tax (PAT)
        st.subheader("📊 Historical Profit After Tax (PAT in ₹ Crores)")
        
        try:
            financials = stock.financials
            financials = financials.loc[["Net Income"]].transpose()
            financials.index = financials.index.year
            financials["PAT"] = (financials["Net Income"] / 1e7)  # Convert to ₹ Cr
            pm_df=financials[["PAT"]].round(2)
            
            #st.dataframe(pm_df)
            st.line_chart(pm_df)
        except Exception as e:
            st.warning("Could not retrieve PAT (Profit) data.")


        # Historical Revenue Chart
        # 📊 Revenue Over the Years
        st.subheader("📈 Historical Revenue (₹ in Crores)")
        
        try:
            financials = stock.financials
            financials = financials.loc[["Total Revenue"]].transpose()
            financials.index = financials.index.year
            financials["Total Revenue"] = (financials["Total Revenue"] / 1e7)  # Convert from ₹ to Crores
            rm_df = financials[["Total Revenue"]].round(2)
        
            
            st.bar_chart(rm_df)
        
        except Exception as e:
            st.warning("Could not retrieve historical revenue data.")
    except Exception as e:
        st.error("⚠️ Could not fetch data. Please check the stock ticker symbol.")
        
