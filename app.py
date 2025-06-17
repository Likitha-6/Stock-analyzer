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

# Cache for 1 hour to avoid re-reading on every rerun
def load_stock_data():
    try:
        # Changed filename from "nse stocks.csv" to "nse_stocks.csv" for better practice
        # Ensure this file is present in your app directory
        df = pd.read_csv("nse stocks.csv")
        df["Searchable"] = df["Symbol"] + " - " + df["Company Name"]
        return df
    except FileNotFoundError:
        st.error("Error: 'nse stocks.csv' not found. Please make sure the file is in the same directory as the app.")
        st.stop()
        return pd.DataFrame() # Return empty DataFrame to avoid further errors


nse_df = load_stock_data()


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
    "Automotive": 22.1, # Added for Tata Motors example
    # Add more as needed based on your nse_stocks.csv
}

def get_market_cap_category(market_cap_inr):
    if market_cap_inr is None: return "N/A", "N/A" # Handle None
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
    if start_value is None or end_value is None or periods is None: return None
    try:
        start_value = float(start_value)
        end_value = float(end_value)
        periods = int(periods)
        if start_value <= 0 or end_value <= 0 or periods == 0:
            return None
        return (end_value / start_value) ** (1 / periods) - 1
    except (ValueError, TypeError):
        return None


def get_eps_cagr_based_peg(ticker):
    stock = yf.Ticker(ticker)
    pe_ratio = stock.info.get("trailingPE")

    try:
        earnings = stock.earnings
        if earnings.empty:
            return None, "No EPS data available for PEG calculation"

        # Limit to last 5 years of annual earnings for CAGR
        # Ensure earnings DataFrame is sorted by index (year)
        annual_earnings = earnings.reset_index().set_index('periodType').loc['ANNUAL'].sort_index()

        if annual_earnings.shape[0] >= 5:
            eps_data = annual_earnings['Earnings'].tail(5)
            eps_old = eps_data.iloc[0]
            eps_new = eps_data.iloc[-1]
            periods = len(eps_data) - 1

            if periods <= 0:
                return None, "Not enough data points for CAGR calculation"

            cagr = calculate_cagr(eps_old, eps_new, periods)

            if cagr is not None and pe_ratio is not None:
                if cagr <= 0: # Cannot calculate meaningful PEG with non-positive growth
                    return None, "EPS CAGR is non-positive, PEG not meaningful"
                peg = pe_ratio / (cagr * 100) # CAGR is typically decimal, PE is absolute
                return round(peg, 2), None
            else:
                return None, "CAGR or PE unavailable"
        else:
            return None, "Not enough EPS data (need at least 5 years) for 5-year CAGR"

    except Exception as e:
        return None, f"Error calculating PEG: {e}"


def interpret_dividend_yield(dy):
    if dy is None:
        return f"{0}% 🔴 (No dividends)"
    dy_percent = round(dy * 1, 2) # Multiply by 100 for percentage display
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

    # Attempt to convert to float
    try:
        de = float(de)
    except (ValueError, TypeError):
        return "N/A"

    # Heuristic: If the debtToEquity value is significantly greater than 2,
    # and it's an Indian stock (where yfinance often gives percentages),
    # assume it's a percentage and convert it to a ratio.
    #if de > 2.0 and de > 10: # If it's something like 50 or 100, treat as percentage
        #de_ratio = round(de / 100, 2)
    #else: # Otherwise, treat it as a ratio
        #de_ratio = round(de, 2)
    de_ratio=round(de/100,2)

    if de_ratio < 1:
        return f"{de_ratio} ✅ (Low Debt)"
    elif 1 <= de_ratio < 2:
        return f"{de_ratio} 🟡 (Moderate)"
    else: # de_ratio is 2 or higher
        return f"{de_ratio} 🔴 (High Risk)"

 # Cache for 1 hour (3600 seconds)
def get_stock_summary(ticker_symbol):
    full_ticker = ticker_symbol + ".NS"
    stock = yf.Ticker(full_ticker)

    try:
        info = stock.info
        
        if not info or "longName" not in info:
            return None, f"⚠️ Could not fetch data for **{ticker_symbol.upper()}**. Please check the symbol."
        
        sector = info.get("sector")
        # Handle cases where sector might not directly map to INDUSTRY_PE
        industry_pe = INDUSTRY_PE.get(sector, None)
        if industry_pe is None: # Try to find a broader category if direct match fails
            if "Financial" in sector:
                industry_pe = INDUSTRY_PE.get("Financial Services")
            elif "Consumer" in sector:
                industry_pe = INDUSTRY_PE.get("Consumer Cyclical") # Default to cyclial or defensive
            # Add more heuristics as needed

        stock_pe = info.get("trailingPE")
        peg, peg_msg = get_eps_cagr_based_peg(full_ticker)
        
        current_price = info.get("currentPrice")
        
        market_cap = info.get("marketCap")
        
        hist = stock.history(period="max")
        all_time_high = None
        percent_from_ath = None
        
        if not hist.empty:
            all_time_high = round(hist["High"].max(), 2)
            # Ensure all_time_high is not 0 to avoid division by zero and current_price is available
            if current_price is not None and all_time_high is not None and all_time_high != 0:
                percent_from_ath = round(((current_price - all_time_high) / all_time_high) * 100, 2)
        
        free_cash_flow = None
        try:
            cash_flow_statement = stock.cashflow
            if not cash_flow_statement.empty and 'Free Cash Flow' in cash_flow_statement.index:
                # Get the most recent FCF value
                fcf_value = cash_flow_statement.loc['Free Cash Flow'].iloc[0]
                free_cash_flow = fcf_value / 1e7 # Convert to Crores (1 Crore = 10 million)
        except Exception:
            free_cash_flow = None # Set to None on error or missing data
            
        profit_margin = info.get("profitMargins")
        
        summary = {
            "Company Name": info.get("longName"),
            "Sector": sector,
            "Current Price": current_price,
            # Store ATH info as a dictionary for easy access to both values
            "All-Time High Info": {"ath": all_time_high, "percent_from_ath": percent_from_ath},
            "Market Cap": market_cap,
            "PE Ratio": stock_pe, # Raw PE
            "Industry PE": industry_pe, # Raw industry PE
            "EPS": info.get("trailingEps"),
            "Dividend Yield": info.get("dividendYield"),
            "Profit Margin": profit_margin,
            "Free Cash Flow": free_cash_flow, # Already in Crores
            "ROE": info.get("returnOnEquity"),
            "Debt to Equity": info.get("debtToEquity"),
            "PEG Ratio Raw": peg, # Keep PEG raw for potential future use, though not directly used in comparison display as per request
            "PEG Msg": peg_msg # Keep PEG message for single stock display
        }
        return summary, None
    except Exception as e:
        return None, f"Error processing stock: **{ticker_symbol.upper()}** - {e}"


# --- New Helper function for comparison formatting and tick logic ---
def get_formatted_comparison_value(metric_name, value1, value2, industry_pe1=None, industry_pe2=None):
    tick_stock1 = ""
    tick_stock2 = ""
    formatted_value1 = "N/A"
    formatted_value2 = "N/A"

    # Convert to float for numerical comparison if possible
    try:
        float_value1 = float(value1) if isinstance(value1, (int, float)) else None
    except (ValueError, TypeError):
        float_value1 = None
    try:
        float_value2 = float(value2) if isinstance(value2, (int, float)) else None
    except (ValueError, TypeError):
        float_value2 = None

    # Determine which is "better" for tick mark
    # These metrics prefer higher values
    if metric_name in ["Market Cap", "EPS", "Dividend Yield", "Profit Margin", "Free Cash Flow", "ROE"]:
        if float_value1 is not None and float_value2 is not None:
            if float_value1 > float_value2:
                tick_stock1 = " ✅"
            elif float_value2 > float_value1:
                tick_stock2 = " ✅"
        # If only one has a valid value, it's considered "better" by default if it's not None
        elif float_value1 is not None:
            tick_stock1 = " ✅"
        elif float_value2 is not None:
            tick_stock2 = " ✅"
    # This metric prefers lower values
    elif metric_name == "Debt to Equity":
        # Special handling for Debt to Equity to correctly compare ratio vs ratio/percentage
        # Convert to ratio if it seems to be a percentage (e.g., 50 -> 0.5)
        val1_ratio = value1 / 100 if value1 is not None and value1 > 2 else value1
        val2_ratio = value2 / 100 if value2 is not None and value2 > 2 else value2
        
        try:
            float_val1_ratio = float(val1_ratio) if val1_ratio is not None else None
        except (ValueError, TypeError):
            float_val1_ratio = None
        try:
            float_val2_ratio = float(val2_ratio) if val2_ratio is not None else None
        except (ValueError, TypeError):
            float_val2_ratio = None

        if float_val1_ratio is not None and float_val2_ratio is not None:
            if float_val1_ratio < float_val2_ratio:
                tick_stock1 = " ✅"
            elif float_val2_ratio < float_val1_ratio:
                tick_stock2 = " ✅"
        elif float_val1_ratio is not None:
            tick_stock1 = " ✅"
        elif float_val2_ratio is not None:
            tick_stock2 = " ✅"

    elif metric_name == "P/E vs Industry":
        # Lower P/E relative to industry average is better
        # Calculate relative P/E (stock_PE / industry_PE)
        rel_pe1 = float('inf')
        if float_value1 is not None and industry_pe1 is not None and industry_pe1 != 0:
            rel_pe1 = float_value1 / industry_pe1

        rel_pe2 = float('inf')
        if float_value2 is not None and industry_pe2 is not None and industry_pe2 != 0:
            rel_pe2 = float_value2 / industry_pe2
        
        # Determine tick based on relative P/E
        if rel_pe1 < rel_pe2:
            if float_value1 is not None: tick_stock1 = " ✅"
        elif rel_pe2 < rel_pe1:
            if float_value2 is not None: tick_stock2 = " ✅"
        # If relative P/Es are equal, no tick

    # --- Format values based on metric type ---
    if metric_name == "Current Price":
        formatted_value1 = f"{round(value1, 2)}" if value1 is not None else "N/A"
        formatted_value2 = f"{round(value2, 2)}" if value2 is not None else "N/A"
    elif metric_name == "All-Time High":
        # value1/value2 here are the dictionaries from "All-Time High Info"
        ath1 = value1.get("ath")
        pct_from_ath1 = value1.get("percent_from_ath")
        formatted_value1 = f"{round(ath1, 2)} ({round(pct_from_ath1, 2)}%)" if ath1 is not None and pct_from_ath1 is not None else "N/A"
        
        ath2 = value2.get("ath")
        pct_from_ath2 = value2.get("percent_from_ath")
        formatted_value2 = f"{round(ath2, 2)} ({round(pct_from_ath2, 2)}%)" if ath2 is not None and pct_from_ath2 is not None else "N/A"
    elif metric_name == "Market Cap":
        formatted_value1 = f"{round(float_value1 / 1e9, 2)} B" if float_value1 is not None else "N/A"
        formatted_value2 = f"{round(float_value2 / 1e9, 2)} B" if float_value2 is not None else "N/A"
    elif metric_name == "EPS":
        formatted_value1 = f"{round(float_value1, 2)}" if float_value1 is not None else "N/A"
        formatted_value2 = f"{round(float_value2, 2)}" if float_value2 is not None else "N/A"
    elif metric_name == "Dividend Yield":
        formatted_value1 = f"{round(float_value1 * 1, 2)}%" if float_value1 is not None else "0%"
        formatted_value2 = f"{round(float_value2 *1, 2)}%" if float_value2 is not None else "0%"
    elif metric_name == "Profit Margin":
        formatted_value1 = f"{round(float_value1 * 100, 2)}%" if float_value1 is not None else "N/A"
        formatted_value2 = f"{round(float_value2 * 100, 2)}%" if float_value2 is not None else "N/A"
    elif metric_name == "Free Cash Flow":
        # Assuming value is already in Crores from get_stock_summary
        formatted_value1 = f"{round(float_value1, 2)}" if float_value1 is not None else "N/A"
        formatted_value2 = f"{round(float_value2, 2)}" if float_value2 is not None else "N/A"
    elif metric_name == "ROE":
        formatted_value1 = f"{round(float_value1 * 100, 2)}%" if float_value1 is not None else "N/A"
        formatted_value2 = f"{round(float_value2 * 100, 2)}%" if float_value2 is not None else "N/A"
    elif metric_name == "Debt to Equity":
        # Re-apply the ratio conversion for display, as comparison was done on ratios
        val1_display = round(value1 / 100, 2) if value1 is not None and value1 > 2 else (round(value1,2) if value1 is not None else None)
        val2_display = round(value2 / 100, 2) if value2 is not None and value2 > 2 else (round(value2,2) if value2 is not None else None)

        formatted_value1 = f"{val1_display}" if val1_display is not None else "N/A"
        formatted_value2 = f"{val2_display}" if val2_display is not None else "N/A"
    elif metric_name == "P/E vs Industry":
        pe1_str = f"{round(float_value1, 2)}" if float_value1 is not None else "N/A"
        industry_pe1_str = f"{round(industry_pe1, 2)}" if industry_pe1 is not None else "N/A"
        formatted_value1 = f"{pe1_str} (Industry Avg: {industry_pe1_str})"
        
        pe2_str = f"{round(float_value2, 2)}" if float_value2 is not None else "N/A"
        industry_pe2_str = f"{round(industry_pe2, 2)}" if industry_pe2 is not None else "N/A"
        formatted_value2 = f"{pe2_str} (Industry Avg: {industry_pe2_str})"
    else: # For Company Name, Sector (no special formatting or ticks)
        formatted_value1 = value1 if value1 is not None else "N/A"
        formatted_value2 = value2 if value2 is not None else "N/A"

    return formatted_value1 + tick_stock1, formatted_value2 + tick_stock2

# User input for primary stock search
user_input = st.text_input("🔍 Search by symbol or company name for the primary stock:")

selected_symbol = None

if user_input:
    # 1. Try to find a match in the CSV first
    if not nse_df.empty:
        matches = nse_df[nse_df["Searchable"].str.contains(user_input, case=False, na=False)]

        if not matches.empty:
            selected = st.selectbox("Select a company (Primary):", matches["Searchable"].tolist(), key="main_stock_select")
            selected_symbol = selected.split(" - ")[0]
            st.success(f"✅ Primary Stock Selected: **{selected_symbol}.NS** ")
        else:
            # 2. If no match in CSV, try to use user_input directly as a symbol
            potential_symbol = user_input.strip().upper()

            st.info(f"Trying to fetch data directly for **{potential_symbol}.NS**...")
            try:
                temp_ticker = yf.Ticker(potential_symbol + ".NS")
                temp_info = temp_ticker.info
                if temp_info and "longName" in temp_info:
                    selected_symbol = potential_symbol
                    st.success(f"✅ Primary Stock Selected: **{temp_info['longName']} ({selected_symbol}.NS)** (Direct Search)")
                else:
                    st.warning("❌ No match found in CSV or as a direct symbol. Try typing a different keyword.")
            except Exception:
                st.warning("❌ No match found in CSV or as a direct symbol. Try typing a different keyword.")
    else:
        st.warning("CSV data not loaded. Please check 'nse stocks.csv' file.")
else:
    st.info("Please enter a company name or symbol to search for the primary stock.")


# Main app logic
if selected_symbol:
    if compare_mode:
        st.subheader("🆚 Compare With Another Stock")

        # --- NEW SEARCH BAR FOR SECOND STOCK ---
        compare_user_input = st.text_input("🔍 Search by symbol or company name for the second stock:")
        compare_symbol = None

        if compare_user_input:
            if not nse_df.empty:
                compare_matches = nse_df[nse_df["Searchable"].str.contains(compare_user_input, case=False, na=False)]

                if not compare_matches.empty:
                    compare_selected_full = st.selectbox(
                        "Select a company (Second Stock):",
                        compare_matches["Searchable"].tolist(),
                        key="compare_stock_select"
                    )
                    compare_symbol = compare_selected_full.split(" - ")[0]
                    st.success(f"✅ Second Stock Selected: **{compare_symbol}.NS** ")
                else:
                    potential_compare_symbol = compare_user_input.strip().upper()
                    st.info(f"Trying to fetch data directly for **{potential_compare_symbol}.NS**...")
                    try:
                        temp_compare_ticker = yf.Ticker(potential_compare_symbol + ".NS")
                        temp_compare_info = temp_compare_ticker.info
                        if temp_compare_info and "longName" in temp_compare_info:
                            compare_symbol = potential_compare_symbol
                            st.success(f"✅ Second Stock Selected: **{temp_compare_info['longName']} ({compare_symbol}.NS)** (Direct Search)")
                        else:
                            st.warning("❌ No match found for second stock. Try typing a different keyword or valid symbol.")
                    except Exception:
                        st.warning("❌ No match found for second stock. Try typing a different keyword or valid symbol.")
            else:
                st.warning("CSV data not loaded. Cannot search for second stock.")
        else:
            st.info("Please enter a company name or symbol to search for the second stock.")
        # --- END NEW SEARCH BAR ---

        stock1_raw_summary, error1 = get_stock_summary(selected_symbol)
        stock2_raw_summary, error2 = (None, None) # Initialize

        if error1:
            st.error(error1)

        if compare_symbol:
            stock2_raw_summary, error2 = get_stock_summary(compare_symbol)
            if error2:
                st.error(error2)

        # Display comparison only if both summaries are successfully retrieved
        if stock1_raw_summary and stock2_raw_summary:
            # Define the order of metrics for display in the comparison table
            display_metrics_order = [
                "Company Name", "Sector", "Current Price", "All-Time High", "Market Cap",
                "P/E vs Industry", "EPS", "Dividend Yield", "Profit Margin",
                "Free Cash Flow", "ROE", "Debt to Equity"
            ]
            
            comparison_display_dict = {}

            # Populate the dictionary for the DataFrame
            for metric in display_metrics_order:
                value1 = None
                value2 = None
                industry_pe1 = None
                industry_pe2 = None

                # Map display metric names to raw summary keys for retrieval
                if metric == "Company Name":
                    value1 = stock1_raw_summary.get("Company Name")
                    value2 = stock2_raw_summary.get("Company Name")
                elif metric == "Sector":
                    value1 = stock1_raw_summary.get("Sector")
                    value2 = stock2_raw_summary.get("Sector")
                elif metric == "Current Price":
                    value1 = stock1_raw_summary.get("Current Price")
                    value2 = stock2_raw_summary.get("Current Price")
                elif metric == "All-Time High":
                    value1 = stock1_raw_summary.get("All-Time High Info", {})
                    value2 = stock2_raw_summary.get("All-Time High Info", {})
                elif metric == "Market Cap":
                    value1 = stock1_raw_summary.get("Market Cap")
                    value2 = stock2_raw_summary.get("Market Cap")
                elif metric == "P/E vs Industry":
                    value1 = stock1_raw_summary.get("PE Ratio")
                    value2 = stock2_raw_summary.get("PE Ratio")
                    industry_pe1 = stock1_raw_summary.get("Industry PE")
                    industry_pe2 = stock2_raw_summary.get("Industry PE")
                elif metric == "EPS":
                    value1 = stock1_raw_summary.get("EPS")
                    value2 = stock2_raw_summary.get("EPS")
                elif metric == "Dividend Yield":
                    value1 = stock1_raw_summary.get("Dividend Yield")
                    value2 = stock2_raw_summary.get("Dividend Yield")
                elif metric == "Profit Margin":
                    value1 = stock1_raw_summary.get("Profit Margin")
                    value2 = stock2_raw_summary.get("Profit Margin")
                elif metric == "Free Cash Flow":
                    value1 = stock1_raw_summary.get("Free Cash Flow")
                    value2 = stock2_raw_summary.get("Free Cash Flow")
                elif metric == "ROE":
                    value1 = stock1_raw_summary.get("ROE")
                    value2 = stock2_raw_summary.get("ROE")
                elif metric == "Debt to Equity":
                    value1 = stock1_raw_summary.get("Debt to Equity")
                    value2 = stock2_raw_summary.get("Debt to Equity")
                
                # Use the new helper function for dynamic formatting and tick logic
                formatted_val1, formatted_val2 = get_formatted_comparison_value(
                    metric, value1, value2, industry_pe1, industry_pe2
                )
                
                comparison_display_dict[metric] = {
                    stock1_raw_summary.get("Company Name", selected_symbol.upper()): formatted_val1,
                    stock2_raw_summary.get("Company Name", compare_symbol.upper()): formatted_val2
                }

            # Convert the processed dictionary to a DataFrame for display
            comparison_data = pd.DataFrame.from_dict(comparison_display_dict, orient='index')
            comparison_data.index.name = "Metric" # Set the index name

            st.subheader("📊 Stock Comparison")
            # Using st.dataframe for better display control and formatting
            st.dataframe(comparison_data)

            # --- START CHART COMPARISON (Existing Code - No Changes for functionality) ---
            st.markdown("---")
            st.subheader("📈 Historical Data Comparison")

            # Chart Period Selector for Comparison Mode
            compare_chart_period = st.selectbox(
                "Select period for historical charts:",
                ["1mo", "3mo", "6mo", "1y", "3y", "5y", "max"],
                index=4, # Default to 5 years
                key="compare_chart_period"
            )

            # --- Historical Price Chart Comparison ---
            st.markdown("##### 📉 Historical Price Chart")
            col1_price, col2_price = st.columns(2)
            with col1_price:
                try:
                    stock1_yf = yf.Ticker(selected_symbol + ".NS")
                    hist_price1 = stock1_yf.history(period=compare_chart_period)
                    if not hist_price1.empty:
                        st.line_chart(hist_price1["Close"].round(2).rename(stock1_raw_summary.get('Company Name', selected_symbol.upper())))
                    else:
                        st.warning(f"No price data for {stock1_raw_summary.get('Company Name', selected_symbol.upper())}")
                except Exception as e:
                    st.warning(f"Could not load price chart for {stock1_raw_summary.get('Company Name', selected_symbol.upper())}. Error: {e}")

            with col2_price:
                try:
                    stock2_yf = yf.Ticker(compare_symbol + ".NS")
                    hist_price2 = stock2_yf.history(period=compare_chart_period)
                    if not hist_price2.empty:
                        st.line_chart(hist_price2["Close"].round(2).rename(stock2_raw_summary.get('Company Name', compare_symbol.upper())))
                    else:
                        st.warning(f"No price data for {stock2_raw_summary.get('Company Name', compare_symbol.upper())}")
                except Exception as e:
                    st.warning(f"Could not load price chart for {stock2_raw_summary.get('Company Name', compare_symbol.upper())}. Error: {e}")

            # --- Historical Profit After Tax (PAT) Chart Comparison ---
            st.markdown("##### 📊 Historical Profit After Tax (PAT in ₹ Crores)")
            col1_pat, col2_pat = st.columns(2)
            with col1_pat:
                try:
                    stock1_yf = yf.Ticker(selected_symbol + ".NS")
                    financials1 = stock1_yf.financials
                    # Ensure 'ANNUAL' data is selected if available
                    annual_financials1 = financials1.reset_index().set_index('periodType').loc['ANNUAL'].sort_index() if 'periodType' in financials1.index.names else financials1.sort_index()
                    
                    if not annual_financials1.empty and "Net Income" in annual_financials1.columns: # Changed .index to .columns
                        pat_df1 = annual_financials1[["Net Income"]].copy() # Use .copy() to avoid SettingWithCopyWarning
                        pat_df1.index = pat_df1.index.year # Use the year from the DatetimeIndex
                        pat_df1["PAT"] = (pat_df1["Net Income"] / 1e7).round(2) # Convert and round
                        st.bar_chart(pat_df1[["PAT"]].rename(columns={'PAT': stock1_raw_summary.get('Company Name', selected_symbol.upper()) + ' PAT'}))
                    else:
                        st.warning(f"No PAT data for {stock1_raw_summary.get('Company Name', selected_symbol.upper())}")
                except Exception as e:
                    st.warning(f"Could not retrieve PAT data for {stock1_raw_summary.get('Company Name', selected_symbol.upper())}. Error: {e}")

            with col2_pat:
                try:
                    stock2_yf = yf.Ticker(compare_symbol + ".NS")
                    financials2 = stock2_yf.financials
                    annual_financials2 = financials2.reset_index().set_index('periodType').loc['ANNUAL'].sort_index() if 'periodType' in financials2.index.names else financials2.sort_index()

                    if not annual_financials2.empty and "Net Income" in annual_financials2.columns:
                        pat_df2 = annual_financials2[["Net Income"]].copy()
                        pat_df2.index = pat_df2.index.year
                        pat_df2["PAT"] = (pat_df2["Net Income"] / 1e7).round(2)
                        st.bar_chart(pat_df2[["PAT"]].rename(columns={'PAT': stock2_raw_summary.get('Company Name', compare_symbol.upper()) + ' PAT'}))
                    else:
                        st.warning(f"No PAT data for {stock2_raw_summary.get('Company Name', compare_symbol.upper())}")
                except Exception as e:
                    st.warning(f"Could not retrieve PAT data for {stock2_raw_summary.get('Company Name', compare_symbol.upper())}. Error: {e}")

            # --- Historical Revenue Chart Comparison ---
            st.markdown("##### 📈 Historical Revenue (₹ in Crores)")
            col1_rev, col2_rev = st.columns(2)
            with col1_rev:
                try:
                    stock1_yf = yf.Ticker(selected_symbol + ".NS")
                    financials1 = stock1_yf.financials
                    annual_financials1 = financials1.reset_index().set_index('periodType').loc['ANNUAL'].sort_index() if 'periodType' in financials1.index.names else financials1.sort_index()

                    if not annual_financials1.empty and "Total Revenue" in annual_financials1.columns:
                        revenue_df1 = annual_financials1[["Total Revenue"]].copy()
                        revenue_df1.index = revenue_df1.index.year
                        revenue_df1["Total Revenue"] = (revenue_df1["Total Revenue"] / 1e7).round(2)
                        st.bar_chart(revenue_df1[["Total Revenue"]].rename(columns={'Total Revenue': stock1_raw_summary.get('Company Name', selected_symbol.upper()) + ' Revenue'}))
                    else:
                        st.warning(f"No Revenue data for {stock1_raw_summary.get('Company Name', selected_symbol.upper())}")
                except Exception as e:
                    st.warning(f"Could not retrieve revenue data for {stock1_raw_summary.get('Company Name', selected_symbol.upper())}. Error: {e}")

            with col2_rev:
                try:
                    stock1_yf = yf.Ticker(selected_symbol + ".NS")
                    financials1 = stock1_yf.financials
                    annual_financials1 = financials1.reset_index().set_index('periodType').loc['ANNUAL'].sort_index() if 'periodType' in financials1.index.names else financials1.sort_index()

                    if not annual_financials1.empty and "Total Revenue" in annual_financials1.columns:
                        revenue_df1 = annual_financials1[["Total Revenue"]].copy()
                        revenue_df1.index = revenue_df1.index.year
                        revenue_df1["Total Revenue"] = (revenue_df1["Total Revenue"] / 1e7).round(2)
                        st.bar_chart(revenue_df1[["Total Revenue"]].rename(columns={'Total Revenue': stock1_raw_summary.get('Company Name', selected_symbol.upper()) + ' Revenue'}))
                    else:
                        st.warning(f"No Revenue data for {stock1_raw_summary.get('Company Name', selected_symbol.upper())}")
                
                except Exception as e:
                    st.warning(f"Could not retrieve PAT data for {stock2_raw_summary.get('Company Name', compare_symbol.upper())}. Error: {e}")


            # --- Historical Free Cash Flow (FCF) Chart Comparison ---
            st.markdown("##### 💰 Historical Free Cash Flow (₹ in Crores)")
            col1_fcf, col2_fcf = st.columns(2)
            with col1_fcf:
                try:
                    stock1_yf = yf.Ticker(selected_symbol + ".NS")
                    cash_flow_statement1 = stock1_yf.cashflow
                    annual_cash_flow1 = cash_flow_statement1.reset_index().set_index('periodType').loc['ANNUAL'].sort_index() if 'periodType' in cash_flow_statement1.index.names else cash_flow_statement1.sort_index()

                    if not annual_cash_flow1.empty and 'Free Cash Flow' in annual_cash_flow1.columns:
                        fcf_df1 = annual_cash_flow1[['Free Cash Flow']].copy()
                        fcf_df1.index = fcf_df1.index.year
                        fcf_df1['Free Cash Flow (₹ Cr)'] = (fcf_df1['Free Cash Flow'] / 1e7).round(2)
                        st.bar_chart(fcf_df1[['Free Cash Flow (₹ Cr)']].rename(columns={'Free Cash Flow (₹ Cr)': stock1_raw_summary.get('Company Name', selected_symbol.upper()) + ' FCF'}))
                    else:
                        st.warning(f"No FCF data for {stock1_raw_summary.get('Company Name', selected_symbol.upper())}")
                except Exception as e:
                    st.warning(f"Could not retrieve FCF data for {stock1_raw_summary.get('Company Name', selected_symbol.upper())}. Error: {e}")

            with col2_fcf:
                try:
                    stock2_yf = yf.Ticker(compare_symbol + ".NS")
                    cash_flow_statement2 = stock2_yf.cashflow
                    annual_cash_flow2 = cash_flow_statement2.reset_index().set_index('periodType').loc['ANNUAL'].sort_index() if 'periodType' in cash_flow_statement2.index.names else cash_flow_statement2.sort_index()

                    if not annual_cash_flow2.empty and 'Free Cash Flow' in annual_cash_flow2.columns:
                        fcf_df2 = annual_cash_flow2[['Free Cash Flow']].copy()
                        fcf_df2.index = fcf_df2.index.year
                        fcf_df2['Free Cash Flow (₹ Cr)'] = (fcf_df2['Free Cash Flow'] / 1e7).round(2)
                        st.bar_chart(fcf_df2[['Free Cash Flow (₹ Cr)']].rename(columns={'Free Cash Flow (₹ Cr)': stock2_raw_summary.get('Company Name', compare_symbol.upper()) + ' FCF'}))
                    else:
                        st.warning(f"No FCF data for {stock2_raw_summary.get('Company Name', compare_symbol.upper())}")
                except Exception as e:
                    st.warning(f"Could not retrieve FCF data for {stock2_raw_summary.get('Company Name', compare_symbol.upper())}. Error: {e}")
            # --- END CHART COMPARISON ---

        elif stock1_raw_summary: # Only primary stock available, in compare mode but second not selected/found
            if compare_user_input and not compare_symbol:
                 st.warning("Please select a valid second stock from the dropdown or try a different search term.")
            else:
                st.info("Please search and select a second stock to enable full comparison view. Displaying primary stock details below.")
            
            # Fallback to display single stock if only one is found in compare mode
            st.subheader(f"📋 Fundamentals Summary for {stock1_raw_summary.get('Company Name', selected_symbol.upper())}")
            # For single stock display, we still use the old interpret functions for rich text
            single_stock_display_summary = {
                "Company Name": stock1_raw_summary["Company Name"],
                "Sector": stock1_raw_summary["Sector"],
                "Current Price (₹)": stock1_raw_summary["Current Price"],
                "All-Time High (₹)": (
                    f"{round(stock1_raw_summary['All-Time High Info']['ath'], 2)} ({round(stock1_raw_summary['All-Time High Info']['percent_from_ath'], 2)}%) 🔻" 
                    if stock1_raw_summary['All-Time High Info']['ath'] is not None and stock1_raw_summary['All-Time High Info']['percent_from_ath'] is not None and stock1_raw_summary['All-Time High Info']['percent_from_ath'] < 0 
                    else (
                        f"{round(stock1_raw_summary['All-Time High Info']['ath'], 2)} (+{round(stock1_raw_summary['All-Time High Info']['percent_from_ath'], 2)}%) 🟢" 
                        if stock1_raw_summary['All-Time High Info']['ath'] is not None and stock1_raw_summary['All-Time High Info']['percent_from_ath'] is not None 
                        else "N/A"
                    )
                ),
                "Market Cap": f"{round(stock1_raw_summary['Market Cap'] / 1e9, 2)} B ({get_category_icon(get_market_cap_category(stock1_raw_summary['Market Cap'])[0])} {get_market_cap_category(stock1_raw_summary['Market Cap'])[0]})" if stock1_raw_summary['Market Cap'] else "N/A",
                "P/E vs Industry": interpret_pe_with_industry(stock1_raw_summary["PE Ratio"], stock1_raw_summary["Industry PE"]),
                "EPS": interpret_eps(stock1_raw_summary["EPS"]),
                "Dividend Yield": interpret_dividend_yield(stock1_raw_summary["Dividend Yield"]),
                "Profit Margin": f"{round(stock1_raw_summary['Profit Margin'] * 100, 2)}%" if stock1_raw_summary['Profit Margin'] is not None and stock1_raw_summary['Profit Margin'] >= 0 else (f"{round(stock1_raw_summary['Profit Margin'] * 100, 2)}% ❌ (Loss-Making)" if stock1_raw_summary['Profit Margin'] is not None else "N/A"),
                "Free Cash Flow (₹ Cr)": f"{round(stock1_raw_summary['Free Cash Flow'], 2)}" if stock1_raw_summary['Free Cash Flow'] is not None else "N/A",
                "ROE": interpret_roe(stock1_raw_summary["ROE"]),
                "Debt to Equity": interpret_de_ratio(stock1_raw_summary["Debt to Equity"]),
            }
            df = pd.DataFrame(single_stock_display_summary.items(), columns=["Metric", "Value"])
            st.dataframe(df.set_index("Metric"))

        else: # No primary stock selected at all
            st.warning("No primary stock selected. Please select a primary stock to begin analysis.")

    else: # Not in compare mode (single stock view)
        stock_summary, error = get_stock_summary(selected_symbol)

        if error:
            st.error(error)
        elif stock_summary:
            # Reconstruct for single display using original interpretation functions
            display_summary_for_single_mode = {
                "Company Name": stock_summary.get("Company Name"),
                "Sector": stock_summary.get("Sector"),
                "Current Price (₹)": stock_summary.get("Current Price"),
                "All-Time High (₹)": (
                    f"{round(stock_summary['All-Time High Info']['ath'], 2)} ({round(stock_summary['All-Time High Info']['percent_from_ath'], 2)}%) 🔻" 
                    if stock_summary['All-Time High Info']['ath'] is not None and stock_summary['All-Time High Info']['percent_from_ath'] is not None and stock_summary['All-Time High Info']['percent_from_ath'] < 0 
                    else (
                        f"{round(stock_summary['All-Time High Info']['ath'], 2)} (+{round(stock_summary['All-Time High Info']['percent_from_ath'], 2)}%) 🟢" 
                        if stock_summary['All-Time High Info']['ath'] is not None and stock_summary['All-Time High Info']['percent_from_ath'] is not None 
                        else "N/A"
                    )
                ),
                "Market Cap": f"{round(stock_summary['Market Cap'] / 1e9, 2)} B ({get_category_icon(get_market_cap_category(stock_summary['Market Cap'])[0])} {get_market_cap_category(stock_summary['Market Cap'])[0]})" if stock_summary['Market Cap'] else "N/A",
                "P/E vs Industry": interpret_pe_with_industry(stock_summary["PE Ratio"], stock_summary["Industry PE"]),
                "EPS": interpret_eps(stock_summary["EPS"]),
                "Dividend Yield": interpret_dividend_yield(stock_summary["Dividend Yield"]),
                "Profit Margin": f"{round(stock_summary['Profit Margin'] * 100, 2)}%" if stock_summary['Profit Margin'] is not None and stock_summary['Profit Margin'] >= 0 else (f"{round(stock_summary['Profit Margin'] * 100, 2)}% ❌ (Loss-Making)" if stock_summary['Profit Margin'] is not None else "N/A"),
                "Free Cash Flow (₹ Cr)": f"{round(stock_summary['Free Cash Flow'], 2)}" if stock_summary['Free Cash Flow'] is not None else "N/A",
                "ROE": interpret_roe(stock_summary["ROE"]),
                "Debt to Equity": interpret_de_ratio(stock_summary["Debt to Equity"]),
            }
            df = pd.DataFrame(display_summary_for_single_mode.items(), columns=["Metric", "Value"])
            st.dataframe(df.set_index("Metric"))

            st.subheader("📉 Historical Stock Price Chart")

            try:
                stock_yf = yf.Ticker(selected_symbol + ".NS")
                period = st.selectbox("Select period for price chart:", ["1mo", "3mo", "6mo", "1y", "5y", "max"], index=4, key="price_period")
                hist_price = stock_yf.history(period=period)
                if not hist_price.empty:
                    st.line_chart(hist_price["Close"].round(2))
                else:
                    st.warning("No historical stock data available for the selected period.")
            except Exception as e:
                st.warning(f"Could not load stock price chart. Error: {e}")
             st.subheader("📊 Historical Profit After Tax (PAT in ₹ Crores)")

            try:
                stock_yf = yf.Ticker(selected_symbol + ".NS")
                financials = stock_yf.financials
                if not financials.empty and "Net Income" in financials.index:
                    pat_df = financials.loc[["Net Income"]].transpose()
                    pat_df.index = pat_df.index.year
                    pat_df["PAT"] = (pat_df["Net Income"] / 1e7)
                    st.line_chart(pat_df[["PAT"]].round(2))
                else:
                    st.warning("Net Income data not available in financials to calculate PAT.")
            except Exception as e:
                st.warning(f"Could not retrieve PAT (Profit) data. Error: {e}")




            st.subheader("📈 Historical Revenue (₹ in Crores)")

            try:
                stock_yf = yf.Ticker(selected_symbol + ".NS")
                financials = stock_yf.financials
                if not financials.empty and "Total Revenue" in financials.index:
                    revenue_df = financials.loc[["Total Revenue"]].transpose()
                    revenue_df.index = revenue_df.index.year
                    revenue_df["Total Revenue"] = (revenue_df["Total Revenue"] / 1e7)
                    st.bar_chart(revenue_df[["Total Revenue"]].round(2))
                else:
                    st.warning("Total Revenue data not available in financials.")
            except Exception as e:
                st.warning(f"Could not retrieve historical revenue data. Error: {e}")


            st.subheader("💰 Historical Free Cash Flow (₹ in Crores)")

            try:
                stock_yf = yf.Ticker(selected_symbol + ".NS")
                cash_flow_statement = stock_yf.cashflow

                if not cash_flow_statement.empty and 'Free Cash Flow' in cash_flow_statement.index:
                    # Select 'Free Cash Flow' row, transpose, and convert index to year
                    fcf_df = cash_flow_statement.loc[['Free Cash Flow']].transpose()
                    fcf_df.index = fcf_df.index.year # Convert datetime index to year

                    # Rename column for plotting clarity
                    fcf_df.rename(columns={'Free Cash Flow': 'Free Cash Flow (₹ Cr)'}, inplace=True)

                    # Convert to Crores (adjust 1e7 based on your unit verification)
                    fcf_df['Free Cash Flow (₹ Cr)'] = fcf_df['Free Cash Flow (₹ Cr)'] / 1e7

                    # Plotting a bar chart for FCF is often better for yearly values
                    st.bar_chart(fcf_df[['Free Cash Flow (₹ Cr)']].round(2))
                else:
                    st.warning("Free Cash Flow data not available in cash flow statements.")
            except Exception as e:
                st.warning(f"Could not retrieve historical Free Cash Flow data. Error: {e}")



