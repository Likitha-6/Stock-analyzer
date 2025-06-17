import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np # For handling NaN values gracefully

# --- Configuration ---
st.set_page_config(
    page_title="Stock Analysis Dashboard",
    page_icon="📈",
    layout="wide"
)

# --- Constants ---
INDUSTRY_PE = {
    "Technology": 30,
    "Financial Services": 15,
    "Healthcare": 25,
    "Consumer Cyclical": 20,
    "Consumer Defensive": 22,
    "Industrials": 20,
    "Basic Materials": 18,
    "Energy": 12,
    "Utilities": 17,
    "Real Estate": 16,
    "Communication Services": 25,
    "Capital Goods": 22, # Often grouped under Industrials
    "Chemicals": 20, # Often grouped under Basic Materials
    "Automotive": 18, # Often grouped under Consumer Cyclical
    "Conglomerates": 18,
    # Add more industries and their typical PE ratios as needed
}

# --- Data Loading (from CSV) ---

def load_stock_data():
    """Loads NSE stock list from a CSV file."""
    try:
        df = pd.read_csv("nse stocks.csv") # Make sure your CSV is named exactly this
        df["Searchable"] = df["Symbol"] + " - " + df["Company Name"]
        return df
    except FileNotFoundError:
        st.error("Error: 'nse stocks.csv' not found. Please ensure the file is in the same directory.")
        return pd.DataFrame() # Return empty DataFrame on error

nse_df = load_stock_data()

# --- Utility Functions ---

def get_market_cap_category(market_cap):
    """Categorizes market capitalization."""
    if market_cap is None:
        return "N/A"
    if market_cap >= 20000 * 1e7: # 20,000 Crores
        return "Mega Cap"
    elif market_cap >= 5000 * 1e7: # 5,000 Crores
        return "Large Cap"
    elif market_cap >= 1000 * 1e7: # 1,000 Crores
        return "Mid Cap"
    elif market_cap >= 100 * 1e7: # 100 Crores
        return "Small Cap"
    else:
        return "Micro Cap"

def get_category_icon(category):
    """Returns an emoji icon for market cap category."""
    icons = {
        "Mega Cap": "👑",
        "Large Cap": "🐘",
        "Mid Cap": "🐻",
        "Small Cap": "🌱",
        "Micro Cap": "🐜",
        "N/A": "❓"
    }
    return icons.get(category, "❓") # Default to question mark

def interpret_eps(eps):
    """Interprets EPS with an emoji."""
    if eps is None:
        return "N/A"
    if eps > 0:
        return f"₹{round(eps, 2)} ✅"
    elif eps < 0:
        return f"₹{round(eps, 2)} 🔻 (Loss)"
    return f"₹{round(eps, 2)}" # Zero EPS

def interpret_pe_with_industry(pe_ratio, sector):
    """Interprets P/E ratio against industry average."""
    if pe_ratio is None or pe_ratio <= 0:
        return "N/A (Non-positive P/E)" # Or 'Loss-making' etc.
    
    industry_avg_pe = INDUSTRY_PE.get(sector, None)

    if industry_avg_pe is None:
        return f"{round(pe_ratio, 2)} ❓ (Industry Avg N/A)"
    
    if pe_ratio < industry_avg_pe * 0.8:
        return f"{round(pe_ratio, 2)}vs {industry_avg_pe} ✅ Undervalued"
    elif pe_ratio > industry_avg_pe * 1.2:
        return f"{round(pe_ratio, 2)} 🔺 Overvalued"
    elif pe_ratio > industry_avg_pe:
        return f"{round(pe_ratio, 2)} 🟠 Slightly Overvalued"
    return f"{round(pe_ratio, 2)} ✅ Fairly Priced"

def calculate_cagr(start_value, end_value, years):
    """Calculates Compound Annual Growth Rate."""
    if start_value is None or end_value is None or years <= 0 or start_value <= 0:
        return None
    return ((end_value / start_value)**(1/years) - 1)

def get_eps_cagr_based_peg(current_pe, eps_cagr):
    """Provides PEG ratio based interpretation."""
    if current_pe is None or eps_cagr is None or eps_cagr <= 0:
        return "N/A (Missing data or non-positive growth)"
    
    # Convert growth rate from decimal to percentage for PEG calculation
    peg_ratio = current_pe / (eps_cagr * 100)

    if peg_ratio < 1:
        return f"{round(peg_ratio, 2)} ✅ (Potentially Undervalued)"
    elif peg_ratio > 2:
        return f"{round(peg_ratio, 2)} 🔺 (Potentially Overvalued)"
    else:
        return f"{round(peg_ratio, 2)} 🟠 (Fairly Valued)"

def interpret_dividend_yield(yield_val):
    """Interprets dividend yield."""
    if yield_val is None:
        return "0% ❓"
    yield_percent = round(yield_val * 1, 2)
    if yield_percent > 3:
        return f"{yield_percent}% ✅ (High)"
    elif yield_percent > 1:
        return f"{yield_percent}% 🟠 (Moderate)"
    return f"{yield_percent}% ⚪ (Low/None)"

def interpret_roe(roe_val):
    """Interprets Return on Equity."""
    if roe_val is None:
        return "N/A ❓"
    roe_percent = round(roe_val * 100, 2)
    if roe_percent >= 15:
        return f"{roe_percent}% ✅ (Excellent)"
    elif roe_percent >= 10:
        return f"{roe_percent}% 🟠 (Good)"
    else:
        return f"{roe_percent}% 🔻 (Poor)"

def interpret_de_ratio(de_ratio):
    """Interprets Debt to Equity ratio."""
    if de_ratio is None:
        return "N/A ❓"
    
    # The yfinance debtToEquity is often a percentage or decimal,
    # assuming it's a number like 50 for 50%, or 0.5 for 50%
    # If it's 50 for 50%, then 50/100 = 0.5
    # The user's previous code used /100, so we'll maintain that for consistency.
    de_display = round(de_ratio / 100, 2)

    if de_display < 0.5:
        return f"{de_display} ✅ (Low Debt)"
    elif de_display < 1.5:
        return f"{de_display} 🟠 (Moderate Debt)"
    else:
        return f"{de_display} 🔻 (High Debt)"

# --- Main Data Fetching and Summary Generation ---
@st.cache_data(ttl=3600) # Cache data for 1 hour
def get_stock_summary(ticker_symbol):
    """Fetches comprehensive stock summary using yfinance."""
    full_ticker = ticker_symbol + ".NS"
    stock = yf.Ticker(full_ticker)

    try:
        info = stock.info
        financials = stock.financials
        cashflow = stock.cashflow
        balance_sheet = stock.balance_sheet
        
        # Check if basic info is available
        if not info:
            return {}, f"❌ Could not retrieve basic info for {ticker_symbol}. Check symbol or try again."

        summary_data = {
            "Company Name": info.get("longName", "N/A"),
            "Sector": info.get("sector", "N/A"),
            "Industry": info.get("industry", "N/A"),
            "Current Price (₹)": f"₹{round(info.get('currentPrice', np.nan), 2)}" if info.get('currentPrice') is not None else "N/A",
            "All-Time High (₹)": f"₹{round(info.get('fiftyTwoWeekHigh', np.nan), 2)}" if info.get('fiftyTwoWeekHigh') is not None else "N/A", # Often 52-week high is used for ATH proxy
            "Market Cap": "N/A"
        }

        market_cap = info.get("marketCap")
        if market_cap is not None:
            market_cap_category = get_market_cap_category(market_cap)
            market_cap_icon = get_category_icon(market_cap_category)
            summary_data["Market Cap"] = f"₹{round(market_cap / 1e7, 2)} Cr {market_cap_icon} ({market_cap_category})"

        summary_data["P/E vs Industry"] = interpret_pe_with_industry(info.get("trailingPE"), info.get("sector"))
        summary_data["EPS"] = interpret_eps(info.get("trailingEps"))
        summary_data["Dividend Yield"] = interpret_dividend_yield(info.get("dividendYield"))
        
        # Profit Margin (often grossMargins, operatingMargins, or profitMargins)
        profit_margin = info.get("profitMargins")
        summary_data["Profit Margin"] = f"{round(profit_margin * 100, 2)}%" if profit_margin is not None else "N/A"

        # Free Cash Flow
        fcf_data = cashflow.loc["Free Cash Flow"] if "Free Cash Flow" in cashflow.index else pd.Series()
        latest_fcf = fcf_data.iloc[0] if not fcf_data.empty else None
        summary_data["Free Cash Flow (₹ Cr)"] = f"₹{round(latest_fcf / 1e7, 2)}" if latest_fcf is not None else "N/A"

        summary_data["ROE"] = interpret_roe(info.get("returnOnEquity"))
        summary_data["Debt to Equity"] = interpret_de_ratio(info.get("debtToEquity"))
        
        # --- PEG Ratio (commented out as per user's preference to not disturb single stock display) ---
        # if "trailingEps" in info and not financials.empty and "Net Income" in financials.index:
        #     # Get EPS for two relevant past years
        #     eps_past_years = financials.loc["Net Income"].iloc[0:2] / info["sharesOutstanding"]
        #     if len(eps_past_years) >= 2 and eps_past_years.iloc[1] > 0: # Ensure we have 2 years and base EPS is positive
        #         eps_cagr = calculate_cagr(eps_past_years.iloc[1], eps_past_years.iloc[0], 1) # Simple year-over-year growth
        #         summary_data["PEG Ratio"] = get_eps_cagr_based_peg(info.get("trailingPE"), eps_cagr)
        #     else:
        #         summary_data["PEG Ratio"] = "N/A (EPS growth data missing/negative)"
        # else:
        #     summary_data["PEG Ratio"] = "N/A (EPS or financial data missing)"

        return summary_data, None

    except Exception as e:
        return {}, f"❌ Error fetching data for {ticker_symbol}: {e}. This might happen for delisted or invalid symbols."

# --- Chart Plotting Helper Functions (for compare mode) ---
# These functions are kept separate for clean code in the comparison section

def plot_historical_price_chart(ticker_symbol, company_name, period, column):
    """Plots the historical closing price for a given stock."""
    with column:
        try:
            stock_yf = yf.Ticker(ticker_symbol + ".NS")
            hist_price = stock_yf.history(period=period)
            if not hist_price.empty:
                st.line_chart(hist_price["Close"].round(2).rename(company_name))
            else:
                st.warning(f"No price data available for {company_name} for the selected period.")
        except Exception as e:
            st.warning(f"Could not load historical price chart for {company_name}. Error: {e}")

def plot_historical_financial_chart(ticker_symbol, company_name, financial_metric, unit_divisor, column):
    """Plots historical financial data (PAT, Revenue, FCF) for a given stock."""
    with column:
        try:
            stock_yf = yf.Ticker(ticker_symbol + ".NS")
            
            if financial_metric == 'Free Cash Flow':
                data_df = stock_yf.cashflow
            else: # Net Income or Total Revenue
                data_df = stock_yf.financials

            if not data_df.empty and financial_metric in data_df.index:
                # Ensure data is numeric and handle potential non-numeric entries
                chart_df = data_df.loc[[financial_metric]].transpose()
                
                # Convert index to year for better plotting
                chart_df.index = chart_df.index.year
                
                # Convert financial values to Crores and round
                chart_df[financial_metric] = (pd.to_numeric(chart_df[financial_metric], errors='coerce') / unit_divisor)
                
                # Drop rows where financial_metric became NaN after conversion
                chart_df = chart_df.dropna(subset=[financial_metric])

                st.bar_chart(chart_df[[financial_metric]].round(2).rename(columns={financial_metric: f'{company_name} {financial_metric}'}))
            else:
                st.warning(f"No {financial_metric} data available for {company_name}.")
        except Exception as e:
            st.warning(f"Could not retrieve {financial_metric} data for {company_name}. Error: {e}")


# --- Streamlit App Layout ---
st.title("Stock Analysis Dashboard")

# --- Stock Search and Selection ---
user_input = st.text_input("🔍 Search by symbol or company name (e.g., RELIANCE, TCS):")
selected_symbol = None

if user_input:
    if not nse_df.empty:
        matches = nse_df[nse_df["Searchable"].str.contains(user_input, case=False, na=False)]

        if not matches.empty:
            selected_full = st.selectbox(
                "Select a company:",
                matches["Searchable"].tolist(),
                key="primary_stock_select"
            )
            selected_symbol = selected_full.split(" - ")[0]
            st.success(f"✅ Stock Selected: **{selected_full}**")
        else:
            # If no match in CSV, try direct yfinance search
            potential_symbol = user_input.strip().upper()
            st.info(f"Trying to fetch data directly for **{potential_symbol}.NS**...")
            try:
                temp_ticker = yf.Ticker(potential_symbol + ".NS")
                temp_info = temp_ticker.info
                if temp_info and "longName" in temp_info:
                    selected_symbol = potential_symbol
                    st.success(f"✅ Stock Selected: **{temp_info['longName']} ({selected_symbol}.NS)** (Direct Search)")
                else:
                    st.warning("❌ No match found. Try typing a different keyword or valid symbol.")
            except Exception:
                st.warning("❌ No match found. Try typing a different keyword or valid symbol.")
    else:
        st.warning("CSV data not loaded. Cannot search for stocks.")
else:
    st.info("Please enter a company name or symbol to search for a stock.")

# --- Comparison Mode Checkbox ---
st.markdown("---")
compare_mode = st.checkbox("🆚 Compare with another stock")
st.markdown("---")

# --- Display Stock Information ---
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
                    st.success(f"✅ Second Stock Selected: **{compare_selected_full}** ")
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

        stock1_summary, error1 = get_stock_summary(selected_symbol)
        stock2_summary, error2 = (None, None)

        if error1:
            st.error(error1)

        if compare_symbol:
            stock2_summary, error2 = get_stock_summary(compare_symbol)
            if error2:
                st.error(error2)

        # Display comparison only if both summaries are successfully retrieved
        if stock1_summary and stock2_summary:
            # --- START NEW COMPARISON LOGIC (Selective Interpretation) ---

            # Fetch raw info for direct numerical comparison (will hit cache thanks to @st.cache_data)
            stock1_raw_info = yf.Ticker(selected_symbol + ".NS").info
            stock2_raw_info = yf.Ticker(compare_symbol + ".NS").info

            # Dictionary to build the final comparison display DataFrame
            comparison_display_data = {}

            # Define metrics for which we want selective interpretation
            # "key_in_info": The key to get the raw numerical value from yfinance's info dict
            # "format_func": How to format the raw value for the "worse" stock (without interpretation)
            selective_interpretation_metrics = {
                "P/E vs Industry": {
                    "key_in_info": "trailingPE",
                    "format_func": lambda x: f"{round(x, 2)}" if x is not None else "N/A"
                },
                "EPS": {
                    "key_in_info": "trailingEps",
                    "format_func": lambda x: f"{round(x, 2)}" if x is not None else "N/A"
                },
                "Dividend Yield": {
                    "key_in_info": "dividendYield",
                    "format_func": lambda x: f"{round(x * 100, 2)}%" if x is not None else "0%"
                },
                "ROE": {
                    "key_in_info": "returnOnEquity",
                    "format_func": lambda x: f"{round(x * 100, 2)}%" if x is not None else "N/A"
                },
                "Debt to Equity": {
                    "key_in_info": "debtToEquity",
                    # IMPORTANT: For D/E, we apply the same /100 conversion as interpret_de_ratio
                    # so the numerical value is consistent with the single stock display.
                    "format_func": lambda x: f"{round(x / 100, 2)}" if x is not None else "N/A"
                },
            }

            # List of all metrics in desired display order for the table
            display_order = [
                "Company Name", "Sector", "Current Price (₹)", "All-Time High (₹)", "Market Cap",
                "P/E vs Industry", "EPS", "Dividend Yield", "Profit Margin",
                "Free Cash Flow (₹ Cr)", "ROE", "Debt to Equity"
            ]

            # Populate comparison_display_data based on original summary and selective interpretation
            for metric_name in display_order:
                if metric_name in selective_interpretation_metrics:
                    config = selective_interpretation_metrics[metric_name]
                    key_in_info = config["key_in_info"]
                    format_func = config["format_func"]

                    val1 = stock1_raw_info.get(key_in_info)
                    val2 = stock2_raw_info.get(key_in_info)

                    interpret_val1_str = stock1_summary.get(metric_name, "N/A")
                    interpret_val2_str = stock2_summary.get(metric_name, "N/A")

                    stock1_is_better = False
                    stock2_is_better = False

                    # Determine which stock is 'better'
                    if val1 is None and val2 is None:
                        stock1_display = "N/A"
                        stock2_display = "N/A"
                    elif val1 is None: # Only stock2 has value
                        stock1_display = "N/A"
                        stock2_display = interpret_val2_str
                    elif val2 is None: # Only stock1 has value
                        stock1_display = interpret_val1_str
                        stock2_display = "N/A"
                    else: # Both have values, compare them
                        if metric_name == "P/E vs Industry":
                            # For PE, generally lower positive is better. Negative PE usually worse.
                            if val1 < 0 and val2 < 0: # Both negative, closer to zero is better
                                stock1_is_better = val1 > val2
                                stock2_is_better = val2 > val1
                            elif val1 < 0: # Only stock1 negative, stock2 is better
                                stock2_is_better = True
                            elif val2 < 0: # Only stock2 negative, stock1 is better
                                stock1_is_better = True
                            else: # Both positive, lower is better
                                stock1_is_better = val1 < val2
                                stock2_is_better = val2 < val1
                        elif metric_name == "Debt to Equity": # Lower is better
                            stock1_is_better = val1 < val2
                            stock2_is_better = val2 < val1
                        else: # For EPS, Dividend Yield, ROE (higher is better)
                            stock1_is_better = val1 > val2
                            stock2_is_better = val2 > val1

                        # Handle ties: If values are equal, display plain formatted value for both
                        if val1 == val2 or (not stock1_is_better and not stock2_is_better): # If neither is clearly better
                            stock1_display = format_func(val1)
                            stock2_display = format_func(val2)
                        elif stock1_is_better:
                            stock1_display = interpret_val1_str
                            stock2_display = format_func(val2) # Plain value for worse stock
                        else: # stock2_is_better
                            stock1_display = format_func(val1) # Plain value for worse stock
                            stock2_display = interpret_val2_str

                    comparison_display_data[metric_name] = {
                        stock1_summary.get("Company Name", selected_symbol.upper()): stock1_display,
                        stock2_summary.get("Company Name", compare_symbol.upper()): stock2_display
                    }
                else: # For other metrics (Company Name, Current Price, Market Cap, etc.), display as is
                    if metric_name in stock1_summary and metric_name in stock2_summary:
                        comparison_display_data[metric_name] = {
                            stock1_summary.get("Company Name", selected_symbol.upper()): stock1_summary.get(metric_name),
                            stock2_summary.get("Company Name", compare_symbol.upper()): stock2_summary.get(metric_name)
                        }

            # Create DataFrame from the processed data and transpose to get metrics as index
            comparison_data_df = pd.DataFrame(comparison_display_data).transpose()

            st.subheader("📊 Stock Comparison")
            st.dataframe(comparison_data_df)

            # --- END NEW COMPARISON LOGIC ---

            # --- START CHART COMPARISON (Refactored) ---
            st.markdown("---")
            st.subheader("📈 Historical Data Comparison")

            compare_chart_period = st.selectbox(
                "Select period for historical charts:",
                ["1mo", "3mo", "6mo", "1y", "3y", "5y", "max"],
                index=4, # Default to 5 years
                key="compare_chart_period"
            )

            # --- Historical Price Chart Comparison ---
            st.markdown("##### 📉 Historical Price Chart")
            col1_price, col2_price = st.columns(2)
            plot_historical_price_chart(selected_symbol, stock1_summary.get('Company Name', selected_symbol.upper()), compare_chart_period, col1_price)
            plot_historical_price_chart(compare_symbol, stock2_summary.get('Company Name', compare_symbol.upper()), compare_chart_period, col2_price)


            # --- Historical Profit After Tax (PAT) Chart Comparison ---
            st.markdown("##### 📊 Historical Profit After Tax (PAT in ₹ Crores)")
            col1_pat, col2_pat = st.columns(2)
            # Net Income is used for PAT
            plot_historical_financial_chart(selected_symbol, stock1_summary.get('Company Name', selected_symbol.upper()), "Net Income", 1e7, col1_pat)
            plot_historical_financial_chart(compare_symbol, stock2_summary.get('Company Name', compare_symbol.upper()), "Net Income", 1e7, col2_pat)

            # --- Historical Revenue Chart Comparison ---
            st.markdown("##### 📈 Historical Revenue (₹ in Crores)")
            col1_rev, col2_rev = st.columns(2)
            plot_historical_financial_chart(selected_symbol, stock1_summary.get('Company Name', selected_symbol.upper()), "Total Revenue", 1e7, col1_rev)
            plot_historical_financial_chart(compare_symbol, stock2_summary.get('Company Name', compare_symbol.upper()), "Total Revenue", 1e7, col2_rev)

            # --- Historical Free Cash Flow (FCF) Chart Comparison ---
            st.markdown("##### 💰 Historical Free Cash Flow (₹ in Crores)")
            col1_fcf, col2_fcf = st.columns(2)
            plot_historical_financial_chart(selected_symbol, stock1_summary.get('Company Name', selected_symbol.upper()), "Free Cash Flow", 1e7, col1_fcf)
            plot_historical_financial_chart(compare_symbol, stock2_summary.get('Company Name', compare_symbol.upper()), "Free Cash Flow", 1e7, col2_fcf)

            # --- END CHART COMPARISON ---

        elif stock1_summary: # Only primary stock selected, waiting for second stock
            if compare_user_input and not compare_symbol:
                st.warning("Please select a valid second stock from the dropdown.")
            else:
                st.info("Please search and select a second stock to compare for the full comparison view.")
            st.subheader(f"📋 Fundamentals Summary for {stock1_summary.get('Company Name', selected_symbol.upper())}")
            df = pd.DataFrame(stock1_summary.items(), columns=["Metric", "Value"])
            st.dataframe(df.set_index("Metric"))
        else:
            st.warning("No primary stock data available. Please check the symbol or try again.")

    else: # Not in compare mode (single stock view - THIS REMAINS UNCHANGED)
        stock_summary, error = get_stock_summary(selected_symbol)

        if error:
            st.error(error)
        elif stock_summary:
            st.subheader(f"📋 Fundamentals Summary for {stock_summary.get('Company Name', selected_symbol.upper())}")
            df = pd.DataFrame(stock_summary.items(), columns=["Metric", "Value"])
            st.dataframe(df.set_index("Metric"))

            st.markdown("---")
            st.subheader("📈 Historical Price Chart")
            price_period = st.selectbox(
                "Select period for historical price chart:",
                ["1mo", "3mo", "6mo", "1y", "3y", "5y", "max"],
                index=4, # Default to 5 years
                key="single_chart_period"
            )
            try:
                stock_yf = yf.Ticker(selected_symbol + ".NS")
                hist_price = stock_yf.history(period=price_period)
                if not hist_price.empty:
                    st.line_chart(hist_price["Close"].round(2))
                else:
                    st.warning("No historical price data available for the selected period.")
            except Exception as e:
                st.error(f"Could not load historical price chart: {e}")

        else:
            st.warning("No stock data available. Please select a valid stock.")
