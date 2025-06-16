import streamlit as st
import yfinance as yf
import pandas as pd
import requests
import difflib

# Streamlit setup
st.set_page_config(page_title="Indian Stock Analyzer", page_icon="📊")
st.title("📈 Indian Stock Analyzer (Fundamentals)")
st.markdown("---")
compare_mode = st.checkbox("🔄 Compare stocks")
# Load dynamic search CSV
try:
    nse_df = pd.read_csv("nse stocks.csv")  # Ensure this file is present in the app directory
    nse_df.dropna(subset=["Company Name", "Symbol"], inplace=True)
    company_names = sorted(nse_df["Company Name"].tolist())
except FileNotFoundError:
    st.error("Error: 'nse stocks.csv' not found. Please make sure the file is in the same directory as the app.")
    st.stop() # Stop the app if the CSV is not found


user_input = st.text_input("Search by Company Name (e.g., Infosys, Reliance, TCS):")
ticker_input = None

# Only proceed if user has typed something
if user_input:
    # Find close matches
    matches = difflib.get_close_matches(user_input.strip().lower(),
                                        nse_df["Company Name"].str.lower().tolist(),
                                        n=5, cutoff=0.3)
    
    if matches:
        matched_names = [nse_df[nse_df["Company Name"].str.lower() == name]["Company Name"].values[0]
                         for name in matches]
        
        selected_name = st.selectbox("Select matching company:", matched_names)
        ticker_input = nse_df[nse_df["Company Name"] == selected_name]["Symbol"].values[0]
        st.caption(f"Selected Ticker: `{ticker_input}.NS`")
    else:
        st.warning("No matching company found. Please try again.")

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

    return f"{round(pe,2)} (Industry Avg: {industry_pe}) {interpretation}"

def calculate_cagr(start_value, end_value, periods):
    if start_value <= 0 or end_value <= 0:
        return None  # Avoid division by zero or log of negative
    return (end_value / start_value) ** (1 / periods) - 1

def get_eps_cagr_based_peg(ticker):
    stock = yf.Ticker(ticker)
    pe_ratio = stock.info.get("trailingPE")

    # Get earnings history
    try:
        earnings = stock.earnings  # Returns a DataFrame: 'Revenue' and 'Earnings'
        if earnings.shape[0] < 5:
            return None, "Not enough EPS data for 5-year CAGR"

        # Assume EPS = Earnings / Shares Outstanding (proxy: net income)
        # It's better to use 'basicEPS' if available in stock.info or calculate from financial statements
        # For simplicity, if earnings are directly fetched, you might need to adjust.
        # Yahoo Finance 'earnings' usually gives Net Income.
        # To get EPS, you'd need shares outstanding which is often in 'info' as 'sharesOutstanding'.
        # For now, let's just use 'Earnings' as a proxy for growth, assuming 'Earnings' here refers to Net Income.
        
        # Taking last 5 years for CAGR if available
        if earnings.shape[0] >=5:
            eps_data = earnings['Earnings'].tail(5) # Get last 5 years of earnings
            eps_old = eps_data.iloc[0]
            eps_new = eps_data.iloc[-1]
            periods = len(eps_data) - 1 # Number of periods for CAGR calculation
            cagr = calculate_cagr(eps_old, eps_new, periods)

            if cagr and pe_ratio:
                # PEG Ratio = PE Ratio / (Annual EPS Growth Rate * 100)
                # If CAGR is negative or zero, PEG calculation is not meaningful
                if cagr <= 0:
                    return None, "EPS CAGR is non-positive, PEG not meaningful"
                peg = pe_ratio / (cagr * 100)  # Convert CAGR to %
                return round(peg, 2), None
            else:
                return None, "CAGR or PE unavailable"
        else:
            return None, "Not enough EPS data for 5-year CAGR"

    except Exception as e:
        return None, f"Error calculating PEG: {e}"


def interpret_dividend_yield(dy):
    if dy is None:
        return f"{0}% 🔴 (No dividends)"
    dy_percent = round(dy * 100, 2) # Convert to percentage
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
    if de is None:
        return "N/A"
    # Ensure de is treated as a ratio if it comes as a percentage (e.g., 100 for 1:1)
    # Yahoo Finance's debtToEquity is usually in percentage, e.g., 50 for 0.5
    de_ratio = round(de / 100, 2)
    if de_ratio < 1:
        return f"{de_ratio} ✅ (Low Debt)"
    elif de_ratio >= 1 and de_ratio < 2:
        return f"{de_ratio} 🟡 (Moderate)"
    else:
        return f"{de_ratio} 🔴 (High Risk)"

def get_stock_summary(ticker_symbol):
    stock = yf.Ticker(ticker_symbol + ".NS")
    
    try:
        info = stock.get_info()
        
        if not info or "longName" not in info:
            return None, f"⚠️ Could not fetch data for {ticker_symbol.upper()}. Please check the symbol."
        
        sector = info.get("sector")
        industry_pe = INDUSTRY_PE.get(sector)
        stock_pe = info.get("trailingPE")
        #eps_growth = info.get("earningsQuarterlyGrowth") # This might be None or not what's needed for PEG
        peg, peg_msg = get_eps_cagr_based_peg(ticker_symbol + ".NS") # Pass full ticker for yfinance
        
        current_price = info.get("currentPrice")
        
        market_cap = info.get("marketCap")
        market_cap_display = (
            f"{round(market_cap / 1e9, 2)} B ({get_category_icon(get_market_cap_category(market_cap)[0])} {get_market_cap_category(market_cap)[0]})"
            if market_cap else "N/A"
        )
        
        revenue = info.get("totalRevenue")
        net_income = info.get("netIncomeToCommon")
        revenue_billion = f"{round(revenue / 1e9, 2)} B" if revenue else "N/A"
        net_income_billion = f"{round(net_income / 1e9, 2)} B" if net_income else "N/A"
        
        # Get All-Time High (ATH)
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
        profit_margin_percent = (
            "N/A" if profit_margin is None else
            f"{round(profit_margin * 100, 2)}% ❌ (Loss-Making)" if profit_margin < 0 else
            f"{round(profit_margin * 100, 2)}%"
        )
        
        summary = {
            "Company Name": info.get("longName"),
            "Sector": sector,
            "Current Price (₹)": current_price,
            "All-Time High (₹)": ath_change_display,
            "Market Cap": market_cap_display,
            "P/E vs Industry": interpret_pe_with_industry(stock_pe, industry_pe),
            "PEG Ratio": f"{peg} ({peg_msg})" if peg_msg else peg, # Uncommented this based on original intention
            "EPS": interpret_eps(info.get("trailingEps")),
            "Dividend Yield": interpret_dividend_yield(info.get("dividendYield")),
            "Profit Margin": profit_margin_percent,
            "ROE": interpret_roe(info.get("returnOnEquity")),
            "Debt/Equity": interpret_de_ratio(info.get("debtToEquity")),
            #"Revenue": revenue_billion, # These were commented out in original code, keeping them that way.
            #"Net Income": net_income_billion,
        }
        return summary, None
    except Exception as e:
        return None, f"Error processing stock: {ticker_symbol.upper()} - {e}"
    

# Main app logic
if ticker_input:
    if compare_mode:
        
        st.subheader("🆚 Compare With Another Stock (Optional)")
        compare_company = st.selectbox("Compare With", company_names, index=0)
        compare_input = nse_df[nse_df["Company Name"] == compare_company]["Symbol"].values[0]
        
        
        stock
