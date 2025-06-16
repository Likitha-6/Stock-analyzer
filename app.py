import streamlit as st
import yfinance as yf
import pandas as pd
import requests
import difflib # difflib is still imported but not used in the primary search

# Streamlit setup
st.set_page_config(page_title="Indian Stock Analyzer", page_icon="📊")
st.title("📈 Indian Stock Analyzer (Fundamentals)")
st.markdown("---")
compare_mode = st.checkbox("🔄 Compare stocks")

# Load dynamic search CSV
try:
    @st.cache_data
    def load_stock_data():
        # Ensure 'Symbol' and 'Company Name' columns exist
        df = pd.read_csv("nse stocks.csv")
        df.dropna(subset=["Company Name", "Symbol"], inplace=True)
        return df
    
    nse_df = load_stock_data()
    
    # Prepare searchable string combining symbol and company name
    nse_df["Searchable"] = nse_df["Symbol"] + " - " + nse_df["Company Name"]
    
    # Get sorted company names for the comparison selectbox
    company_names = sorted(nse_df["Company Name"].tolist())

    # User input for searching a stock
    user_input = st.text_input("🔍 Search by symbol or company name (e.g., RELIANCE, Infosys):")
    
    selected_symbol = None # Initialize selected_symbol outside the conditional block

    # Filter matches based on user input
    if user_input:
        matches = nse_df[nse_df["Searchable"].str.contains(user_input, case=False, na=False)]
        
        if not matches.empty:
            # Let user select from filtered list
            # We need to ensure the selected value persists across reruns
            selected_searchable = st.selectbox("Select a company:", matches["Searchable"].tolist(), key="main_search_select")
            selected_symbol = selected_searchable.split(" - ")[0]
            st.success(f"✅ Selected: {selected_symbol}")
        else:
            st.warning("❌ No match found. Try typing a different keyword.")
    else:
        st.info("Please enter a company name or symbol in the search box above to get started.")

except FileNotFoundError:
    st.error("Error: 'nse_stocks.csv' not found. Please make sure the file is in the same directory as the app.")
    st.stop()


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
    dy_percent = round(dy * 100, 2) # Corrected: multiply by 100 for percentage
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

@st.cache_data(ttl=3600) # Cache stock data for 1 hour
def get_stock_summary(ticker_symbol):
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
        
        profit_margin = info.get("profitMargins")
        profit_margin_percent = (
            "N/A" if profit_margin is None else
            f"{round(profit_margin * 100, 2)}% ❌ (Loss-Making)" if profit_margin < 0 else
            f"{round(profit_margin * 100, 2)}%"
        )

        # Get All-Time High (ATH)
        hist = stock.history(period="max")
        all_time_high = "N/A"
        if not hist.empty:
            all_time_high = round(hist["High"].max(), 2)
        
        ath_change_display = "N/A"
        if all_time_high != "N/A" and current_price:
            percent_from_ath = round(((current_price - all_time_high) / all_time_high) * 100, 2)
            if percent_from_ath >= 0:
                ath_change_display = f"{all_time_high} (+{percent_from_ath}%) 🟢"
            else:
                ath_change_display = f"{all_time_high} ({percent_from_ath}%) 🔻"
        
        summary = {
            "Company Name": info.get("longName"),
            "Sector": sector,
            "Current Price (₹)": current_price,
            "All-Time High (₹)": ath_change_display,
            "Market Cap": market_cap_display,
            "P/E Ratio": stock_pe, # Include raw PE for single view dataframe
            "P/E vs Industry": interpret_pe_with_industry(stock_pe, industry_pe),
            "PEG Ratio": f"{peg} ({peg_msg})" if peg_msg else peg,
            "EPS": interpret_eps(info.get("trailingEps")),
            "Dividend Yield": interpret_dividend_yield(info.get("dividendYield")),
            "Profit Margin": profit_margin_percent,
            "ROE": interpret_roe(info.get("returnOnEquity")),
            "Debt/Equity": interpret_de_ratio(info.get("debtToEquity")),
        }
        return summary, None
    except Exception as e:
        return None, f"Error processing stock: {ticker_symbol.upper()} - {e}"
    

# --- Main app logic based on selected_symbol ---
if selected_symbol: # Use selected_symbol here
    if compare_mode:
        st.subheader("🆚 Compare With Another Stock (Optional)")
        # Use a unique key for this selectbox if it's within a conditional block that might re-render
        compare_company = st.selectbox("Compare With", company_names, key="compare_stock_select")
        compare_input = nse_df[nse_df["Company Name"] == compare_company]["Symbol"].values[0]
        
        stock1_summary, error1 = get_stock_summary(selected_symbol) # Use selected_symbol
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
                # Create a union of all keys from both summaries
                all_keys = list(set(stock1_summary.keys()) | set(stock2_summary.keys()))
                
                # Create Series from summaries, filling missing keys with None
                s1 = pd.Series(stock1_summary).reindex(all_keys)
                s2 = pd.Series(stock2_summary).reindex(all_keys)

                comparison_data = pd.DataFrame({
                    stock1_summary.get("Company Name", selected_symbol.upper()): s1,
                    stock2_summary.get("Company Name", compare_input.upper()): s2
                })
                # Reorder rows for better readability (optional, but good practice)
                ordered_metrics = [
                    "Company Name", "Sector", "Current Price (₹)", "All-Time High (₹)", 
                    "Market Cap", "P/E Ratio", "P/E vs Industry", "PEG Ratio", "EPS", 
                    "Dividend Yield", "Profit Margin", "ROE", "Debt/Equity"
                ]
                comparison_data = comparison_data.reindex(ordered_metrics)
                
                st.subheader("📊 Stock Comparison")
                st.dataframe(comparison_data)
            elif stock1_summary:
                st.warning("Only the first stock's data is available for comparison.")
                st.subheader(f"📋 Fundamentals Summary for {stock1_summary.get('Company Name', selected_symbol.upper())}")
                df = pd.DataFrame(stock1_summary.items(), columns=["Metric", "Value"])
                st.dataframe(df.set_index("Metric"))
            else:
                st.warning("No stock data available for comparison.")

else:
    # Single stock view logic (when compare_mode is off)
    stock_summary, error = get_stock_summary(selected_symbol) # This will only run if selected_symbol is not None

    if error:
        st.error(error)
    elif stock_summary:
        # Reconstruct the display data from the summary
        data = {
            "Company Name": stock_summary.get("Company Name"),
            "Sector": stock_summary.get("Sector"),
            "Current Price (₹)": stock_summary.get("Current Price (₹)"),
            "All-Time High (₹)": stock_summary.get("All-Time High (₹)"),
            "Market Cap (Billion ₹)": stock_summary.get("Market Cap"),
            "P/E Ratio": stock_summary.get("P/E Ratio"), # Already in summary
            "P/E vs Industry": stock_summary.get("P/E vs Industry"),
            "PEG Ratio": stock_summary.get("PEG Ratio"),
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
            stock_yf = yf.Ticker(selected_symbol + ".NS") # Use selected_symbol here
            # Add a key to the selectbox to avoid conflicts, especially if placed inside a conditional block
            period = st.selectbox("Select period for price chart:", ["1mo", "3mo", "6mo", "1y", "5y", "max"], index=4, key="price_chart_period")
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
            stock_yf = yf.Ticker(selected_symbol + ".NS") # Use selected_symbol here
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
            stock_yf = yf.Ticker(selected_symbol + ".NS") # Use selected_symbol here
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
