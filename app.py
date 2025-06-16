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
    # Load the NSE stock list CSV (make sure it has 'Symbol' and 'Company Name' columns)
    @st.cache_data
    def load_stock_data():
        return pd.read_csv("nse_stocks.csv")
    
    nse_df = load_stock_data()
    
    # Combine symbol and company name for search
    nse_df["Searchable"] = nse_df["Symbol"] + " - " + nse_df["Company Name"]
    
    # User input
    user_input = st.text_input("🔍 Search by symbol or company name:")
    
    # Filter matches
    if user_input:
        matches = nse_df[nse_df["Searchable"].str.contains(user_input, case=False, na=False)]
    
        if not matches.empty:
            # Let user select from filtered list
            selected = st.selectbox("Select a company:", matches["Searchable"].tolist())
            selected_symbol = selected.split(" - ")[0]
            st.success(f"✅ Selected: {selected_symbol}")
        else:
            st.warning("❌ No match found. Try typing a different keyword.")
    else:
        selected_symbol = None


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
        if earnings.empty:
            return None, "No EPS data available for PEG calculation"

        # Taking last 5 years for CAGR if available
        if earnings.shape[0] >=5:
            eps_data = earnings['Earnings'].tail(5) # Get last 5 years of earnings
            eps_old = eps_data.iloc[0]
            eps_new = eps_data.iloc[-1]
            periods = len(eps_data) - 1 # Number of periods for CAGR calculation
            cagr = calculate_cagr(eps_old, eps_new, periods)

            if cagr and pe_ratio:
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
    dy_percent = round(dy * 1, 2) # Convert to percentage
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
    de_ratio = round(de / 100, 2)
    if de_ratio < 1:
        return f"{de_ratio} ✅ (Low Debt)"
    elif de_ratio >= 1 and de_ratio < 2:
        return f"{de_ratio} 🟡 (Moderate)"
    else:
        return f"{de_ratio} 🔴 (High Risk)"

def get_stock_summary(ticker_symbol):
    # Appending ".NS" within this function, so it's only done once
    full_ticker = ticker_symbol + ".NS" 
    stock = yf.Ticker(full_ticker)
    
    try:
        info = stock.get_info()
        
        if not info or "longName" not in info:
            return None, f"⚠️ Could not fetch data for {ticker_symbol.upper()}. Please check the symbol."
        
        sector = info.get("sector")
        industry_pe = INDUSTRY_PE.get(sector)
        stock_pe = info.get("trailingPE")
        peg, peg_msg = get_eps_cagr_based_peg(full_ticker)
        
        current_price = info.get("currentPrice")
        
        market_cap = info.get("marketCap")
        market_cap_display = (
            f"{round(market_cap / 1e9, 2)} B ({get_category_icon(get_market_cap_category(market_cap)[0])} {get_market_cap_category(market_cap)[0]})"
            if market_cap else "N/A"
        )
        
        revenue = info.get("totalRevenue")
        net_income = info.get("netIncomeToCommon")
        
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
            #"PEG Ratio": f"{peg} ({peg_msg})" if peg_msg else peg,
            "EPS": interpret_eps(info.get("trailingEps")),
            "Dividend Yield": interpret_dividend_yield(info.get("dividendYield")),
            "Profit Margin": profit_margin_percent,
            "ROE": interpret_roe(info.get("returnOnEquity")),
            "Debt/Equity": interpret_de_ratio(info.get("debtToEquity")),
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
        
        stock1_summary, error1 = get_stock_summary(ticker_input)
        stock2_summary, error2 = (None, None)
        
        if compare_input:
            stock2_summary, error2 = get_stock_summary(compare_input)
        
        if error1:
            st.error(error1)
        elif compare_input and error2:
            st.error(error2)
        else:
            if stock1_summary and stock2_summary:
                # Align keys for DataFrame creation
                common_keys = list(set(stock1_summary.keys()) & set(stock2_summary.keys()))
                
                # Create dictionaries with only common keys for DataFrame
                dict1_aligned = {k: stock1_summary[k] for k in common_keys}
                dict2_aligned = {k: stock2_summary[k] for k in common_keys}

                comparison_data = pd.DataFrame({
                    stock1_summary.get("Company Name", ticker_input.upper()): pd.Series(dict1_aligned),
                    stock2_summary.get("Company Name", compare_input.upper()): pd.Series(dict2_aligned)
                })
                
                st.subheader("📊 Stock Comparison")
                st.dataframe(comparison_data)
            elif stock1_summary:
                st.warning("Only the first stock's data is available for comparison.")
                st.subheader(f"📋 Fundamentals Summary for {stock1_summary.get('Company Name', ticker_input.upper())}")
                df = pd.DataFrame(stock1_summary.items(), columns=["Metric", "Value"])
                st.dataframe(df.set_index("Metric"))
            else:
                st.warning("No stock data available for comparison.")

    else:
        # Single stock view
        stock_summary, error = get_stock_summary(ticker_input)

        if error:
            st.error(error)
        elif stock_summary:
            # Reconstruct the display data from the summary
            # We fetch trailingPE separately here if it's not part of the summary you want to display directly
            # If "P/E Ratio" is not directly in summary and you want to show it, fetch it here
            stock_pe_for_display = yf.Ticker(ticker_input + ".NS").info.get("trailingPE")
            
            data = {
                "Company Name": stock_summary.get("Company Name"),
                "Sector": stock_summary.get("Sector"),
                "Current Price (₹)": stock_summary.get("Current Price (₹)"),
                "All-Time High (₹)": stock_summary.get("All-Time High (₹)"),
                "Market Cap (Billion ₹)": stock_summary.get("Market Cap"),
                "P/E Ratio": stock_pe_for_display, # Use the directly fetched PE
                "P/E vs Industry": stock_summary.get("P/E vs Industry"),
                #"PEG Ratio": stock_summary.get("PEG Ratio"),
                "EPS": stock_summary.get("EPS"),
                "Dividend Yield": stock_summary.get("Dividend Yield"),
                "Profit Margin": stock_summary.get("Profit Margin"),
                "Return on Equity (ROE)": stock_summary.get("ROE"),
                "Debt to Equity": stock_summary.get("Debt/Equity"),
            }
            
            df = pd.DataFrame(data.items(), columns=["Metric", "Value"])
            
            st.subheader("📋 Stock Fundamentals Summary")
            st.dataframe(df.set_index("Metric"))
            
            # ---
            # 📉 Stock Price Chart
            st.subheader("📉 Historical Stock Price Chart")
            
            try:
                stock_yf = yf.Ticker(ticker_input + ".NS")
                period = st.selectbox("Select period for price chart:", ["1mo", "3mo", "6mo", "1y", "5y", "max"], index=4)
                hist_price = stock_yf.history(period=period)
                if not hist_price.empty:
                    st.line_chart(hist_price["Close"].round(2))
                else:
                    st.warning("No historical stock data available for the selected period.")
            except Exception as e:
                st.warning(f"Could not load stock price chart. Error: {e}")
            
            # ---
            # 📊 Historical Profit After Tax (PAT)
            st.subheader("📊 Historical Profit After Tax (PAT in ₹ Crores)")
            
            try:
                stock_yf = yf.Ticker(ticker_input + ".NS")
                financials = stock_yf.financials
                if not financials.empty and "Net Income" in financials.index:
                    pat_df = financials.loc[["Net Income"]].transpose()
                    pat_df.index = pat_df.index.year
                    pat_df["PAT"] = (pat_df["Net Income"] / 1e7)  # Convert to ₹ Cr
                    st.line_chart(pat_df[["PAT"]].round(2))
                else:
                    st.warning("Net Income data not available in financials to calculate PAT.")
            except Exception as e:
                st.warning(f"Could not retrieve PAT (Profit) data. Error: {e}")
            
            # ---
            # 📈 Historical Revenue (₹ in Crores)
            st.subheader("📈 Historical Revenue (₹ in Crores)")
            
            try:
                stock_yf = yf.Ticker(ticker_input + ".NS")
                financials = stock_yf.financials
                if not financials.empty and "Total Revenue" in financials.index:
                    revenue_df = financials.loc[["Total Revenue"]].transpose()
                    revenue_df.index = revenue_df.index.year
                    revenue_df["Total Revenue"] = (revenue_df["Total Revenue"] / 1e7)  # Convert from ₹ to Crores
                    st.bar_chart(revenue_df[["Total Revenue"]].round(2))
                else:
                    st.warning("Total Revenue data not available in financials.")
            except Exception as e:
                st.warning(f"Could not retrieve historical revenue data. Error: {e}")
    elif not user_input:
        st.info("Please enter a company name in the search box above to get started.")
