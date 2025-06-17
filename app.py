import streamlit as st
import yfinance as yf
import pandas as pd
import requests
import difflib

# Streamlit setup
st.set_page_config(page_title="Indian Stock Analyzer", page_icon="📊", layout="wide")
st.title("📈 Indian Stock Analyzer (Fundamentals)")
st.markdown("---")

# Initialize session state for the main search input and compare search input
if 'user_input_value' not in st.session_state:
    st.session_state.user_input_value = ""
if 'compare_search_input' not in st.session_state:
    st.session_state.compare_search_input = ""

# Load dynamic search CSV - No longer checking for Sector/Industry
@st.cache_data
def load_stock_data():
    try:
        df = pd.read_csv("nse stocks.csv")
        df["Searchable"] = df["Symbol"] + " - " + df["Company Name"]
        return df
    except FileNotFoundError:
        st.error("Error: 'nse_stocks.csv' not found. Please make sure the file is in the same directory as the app.")
        st.stop()
        return pd.DataFrame() # Return empty DataFrame to avoid further errors

nse_df = load_stock_data()

# Removed INDUSTRY_PE dictionary as it's no longer used

def get_market_cap_category(market_cap_inr):
    if market_cap_inr is None:
        return "N/A", "N/A"
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

def interpret_eps_raw(eps):
    if eps is None:
        return "N/A"
    try:
        eps = float(eps)
    except (TypeError, ValueError):
        return "N/A"
    if eps < 0:
        return "Negative"
    elif eps < 10:
        return "Low"
    else:
        return "Good"

# Simplified interpret_pe_raw - no longer uses industry PE
def interpret_pe_raw(pe):
    if pe is None:
        return "N/A"
    try:
        pe = float(pe)
    except (TypeError, ValueError):
        return "N/A"
    if pe < 15: # Arbitrary threshold for "Good" PE without industry context
        return "Low"
    elif pe < 30:
        return "Moderate"
    else:
        return "High"

def calculate_cagr(start_value, end_value, periods):
    if start_value is None or end_value is None or start_value <= 0 or end_value <= 0 or periods == 0:
        return None
    return (end_value / start_value) ** (1 / periods) - 1

def get_eps_cagr_based_peg(ticker):
    stock = yf.Ticker(ticker)
    pe_ratio = stock.info.get("trailingPE")

    try:
        earnings = stock.earnings
        if earnings.empty:
            return None, "No EPS data available for PEG calculation"

        if earnings.shape[0] >= 5:
            eps_data = earnings['Earnings'].sort_index().tail(5)
            eps_old = eps_data.iloc[0]
            eps_new = eps_data.iloc[-1]
            periods = len(eps_data) - 1

            if periods <= 0:
                return None, "Not enough data points for CAGR calculation"

            cagr = calculate_cagr(eps_old, eps_new, periods)

            if cagr is not None and pe_ratio is not None:
                if cagr <= 0: # PEG is not meaningful for non-growing or negative EPS growth
                    return None, "EPS CAGR is non-positive, PEG not meaningful"
                peg = pe_ratio / (cagr * 100) # CAGR is a decimal, convert to percentage for PEG formula
                return round(peg, 2), None
            else:
                return None, "CAGR or PE unavailable"
        else:
            return None, "Not enough EPS data for 5-year CAGR"

    except Exception as e:
        return None, f"Error calculating PEG: {e}"

def interpret_dividend_yield_raw(dy):
    if dy is None:
        return "No dividends"
    dy_percent = round(dy * 1, 2)
    if dy == 0:
        return "No dividends"
    elif dy < 1:
        return "Low"
    elif dy < 3:
        return "Moderate"
    else:
        return "High"

def interpret_roe_raw(roe):
    if roe is None:
        return "N/A"
    roe_percent = round(roe * 100, 2)
    if roe_percent < 10:
        return "Low"
    elif roe_percent < 20:
        return "Moderate"
    else:
        return "High"

def interpret_de_ratio_raw(de):
    if de is None:
        return "N/A"
    try:
        de = float(de)
    except (ValueError, TypeError):
        return "N/A"
    # Assuming yfinance gives absolute ratio for debtToEquity, not percentage
    de_ratio = round(de/100, 2)
    if de_ratio < 1:
        return "Low Debt"
    elif 1 <= de_ratio < 2:
        return "Moderate Debt"
    else:
        return "High Debt"

# Helper functions for single stock view icons
def get_eps_icon(interpretation):
    return "🔴" if interpretation == "Negative" else ("🟠" if interpretation == "Low" else "✅")

def get_dividend_icon(interpretation):
    return "🔴" if interpretation == "No dividends" else ("🟠" if interpretation == "Low" else "✅")

def get_roe_icon(interpretation):
    return "🟠" if interpretation == "Low" else ("🟡" if interpretation == "Moderate" else "✅")

def get_de_icon(interpretation):
    return "🔴" if interpretation == "High Debt" else ("🟡" if interpretation == "Moderate Debt" else "✅")

# Simplified P/E interpretation for single stock view - no industry context
def interpret_pe_no_industry(pe):
    if pe is None:
        return "N/A"
    try:
        pe = float(pe)
    except (ValueError, TypeError):
        return "N/A"

    if pe < 0:
        return f"P/E: {round(pe, 2)} (Loss-making company) 🔴"
    elif pe < 15:
        return f"P/E: {round(pe, 2)} (Relatively Low) ✅"
    elif pe < 30:
        return f"P/E: {round(pe, 2)} (Moderate) 🟡"
    else:
        return f"P/E: {round(pe, 2)} (High) 🟠"


 # Cache for 1 hour (3600 seconds)
def get_stock_summary(ticker_symbol):
    full_ticker = ticker_symbol + ".NS"
    stock = yf.Ticker(full_ticker)

    try:
        info = stock.info

        if not info or "longName" not in info:
            return None, f"⚠️ Could not fetch data for **{ticker_symbol.upper()}**. Please check the symbol."

        # Sector and Industry are no longer fetched or returned

        # Get raw values for metrics
        current_price = info.get("currentPrice")
        stock_pe = info.get("trailingPE")
        trailing_eps = info.get("trailingEps")
        dividend_yield = info.get("dividendYield")
        profit_margin = info.get("profitMargins")
        return_on_equity = info.get("returnOnEquity")
        debt_to_equity = info.get("debtToEquity")
        market_cap = info.get("marketCap")

        # Calculate/format derived values
        market_cap_category, _ = get_market_cap_category(market_cap)
        market_cap_display = (
            f"{round(market_cap / 1e9, 2)} B" # For consistency in comparison, just show value
            if market_cap else "N/A"
        )
        market_cap_category_icon_display = ( # For displaying icon in specific row
             f"{get_category_icon(market_cap_category)} {market_cap_category}"
            if market_cap else "N/A"
        )


        hist = stock.history(period="max")
        all_time_high = "N/A"
        ath_change_display = "N/A"

        if not hist.empty and current_price:
            all_time_high = round(hist["High"].max(), 2)
            if all_time_high != 0:
                # Keep raw for comparison table, but also prep formatted for single view
                percent_from_ath = round(((current_price - all_time_high) / all_time_high) * 100, 2)
                if percent_from_ath >= 0:
                    ath_change_display = f"{all_time_high} (+{percent_from_ath}%) 🟢"
                else:
                    ath_change_display = f"{all_time_high} ({percent_from_ath}%) 🔻"
        else:
             ath_change_display = "N/A"

        free_cash_flow = 'N/A'
        try:
            cash_flow_statement = stock.cashflow
            if not cash_flow_statement.empty and 'Free Cash Flow' in cash_flow_statement.index:
                fcf_value = cash_flow_statement.loc['Free Cash Flow'].iloc[0]
                free_cash_flow = fcf_value / 1e7 # Convert to Crores
            else:
                free_cash_flow = 'N/A - Data not found'
        except Exception as e:
            free_cash_flow = f'N/A - Error: {e}'

        profit_margin_raw = profit_margin # Keep raw for potential future numerical comparison
        profit_margin_display = (
            "N/A" if profit_margin is None else
            f"{round(profit_margin * 100, 2)}%" # Simple display for comparison
        )
        peg, peg_msg = get_eps_cagr_based_peg(full_ticker)

        summary = {
            "Company Name": info.get("longName"),
            "Symbol": ticker_symbol,
            "Current Price (₹)": current_price,
            "All-Time High (₹)": all_time_high, # Use raw ATH for comparison
            "Market Cap": market_cap, # Use raw market cap for comparison
            "P/E Ratio": stock_pe, # Raw value
            "EPS": trailing_eps, # Raw value
            "Dividend Yield": dividend_yield, # Raw value
            "Profit Margin": profit_margin_raw, # Raw profit margin
            "Free Cash Flow (₹ Cr)": free_cash_flow, # Formatted as it's a derived value
            "ROE": return_on_equity, # Raw value
            "Debt to Equity": debt_to_equity, # Raw value
            "PEG Ratio": peg, # Raw value
            "Market Cap Category": market_cap_category_icon_display # For specific display in table
        }
        return summary, None
    except Exception as e:
        return None, f"Error processing stock: **{ticker_symbol.upper()}** - {e}"

# --- STYLING FUNCTIONS FOR DATAFRAME ---

def highlight_best_numeric(s, metric_type):
    """
    Highlights the 'better' value in a row for numeric metrics.
    Applies bold and green background.
    """
    styles = [''] * len(s) # Initialize all to empty strings for no styling

    # Extract numeric values and their original indices from the Series
    numeric_values = []
    original_indices = []
    for i, val in enumerate(s):
        try:
            numeric_values.append(float(val))
            original_indices.append(i)
        except (ValueError, TypeError):
            # If not numeric, treat as None for comparison purposes
            numeric_values.append(None)

    # If no valid numeric values for comparison, return empty styles
    if not any(val is not None for val in numeric_values):
        return styles

    best_style = 'background-color: lightgreen; font-weight: bold;'

    try:
        if metric_type == "higher": # e.g., EPS, Dividend Yield, ROE, Profit Margin, FCF
            best_val = -float('inf')
            best_idx = -1

            # Find the maximum numeric value
            for i, val in enumerate(numeric_values):
                if val is not None and val > best_val:
                    best_val = val
                    best_idx = i

            # Apply style to all cells that match the best value (handles ties)
            if best_idx != -1:
                for i, val in enumerate(numeric_values):
                    if val is not None and val == best_val:
                        styles[original_indices[i]] = best_style

        elif metric_type == "lower": # e.g., P/E Ratio, Debt to Equity, PEG Ratio
            best_val = float('inf')
            best_idx = -1

            # Find the minimum numeric value (only consider non-negative for PE/PEG)
            for i, val in enumerate(numeric_values):
                if val is not None and val >= 0 and val < best_val:
                    best_val = val
                    best_idx = i

            # Apply style to all cells that match the best value (handles ties)
            if best_idx != -1:
                for i, val in enumerate(numeric_values):
                    if val is not None and val == best_val:
                        styles[original_indices[i]] = best_style

        elif metric_type == "market_cap":
            # For Market Cap, typically larger is considered more stable
            best_val = -float('inf')
            best_idx = -1
            for i, val in enumerate(numeric_values):
                if val is not None and val > best_val:
                    best_val = val
                    best_idx = i
            if best_idx != -1:
                for i, val in enumerate(numeric_values):
                    if val is not None and val == best_val:
                        styles[original_indices[i]] = best_style

    except Exception as e:
        # print(f"Error in highlight_best_numeric for {s.name}: {e}") # For debugging
        pass # Fallback to no highlighting on error

    return styles


# User input for primary stock search
user_input = st.text_input("🔍 Search by symbol or company name for the primary stock:",
                           value=st.session_state.user_input_value,
                           key="user_input_text_box")

selected_symbol = None

if user_input:
    if not nse_df.empty:
        matches = nse_df[nse_df["Searchable"].str.contains(user_input, case=False, na=False)]

        if not matches.empty:
            selected = st.selectbox("Select a company (Primary):", matches["Searchable"].tolist(), key="main_stock_select")
            selected_symbol = selected.split(" - ")[0]
            st.success(f"✅ Primary Stock Selected: **{selected_symbol}.NS** (from CSV)")
        else:
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
        st.warning("CSV data not loaded. Please check 'nse_stocks.csv' file.")
else:
    st.info("Please enter a company name or symbol to search for the primary stock.")

st.markdown("---")

# Removed "Explore Stocks by Sector" section

st.markdown("---")

compare_mode = st.checkbox("🔄 Compare stocks")

# Main app logic
if selected_symbol:
    # Always fetch summary for the primary stock
    stock1_summary, error1 = get_stock_summary(selected_symbol)

    if error1:
        st.error(error1)
    elif compare_mode:
        st.subheader("🆚 Compare With Another Stock")

        st.session_state.compare_search_input = st.text_input(
            "🔍 Search by symbol or company name for the second stock:",
            value=st.session_state.compare_search_input,
            key="compare_search_text_input"
        )
        compare_symbol = None

        if st.session_state.compare_search_input:
            compare_user_input = st.session_state.compare_search_input
            if not nse_df.empty:
                compare_matches = nse_df[nse_df["Searchable"].str.contains(compare_user_input, case=False, na=False)]

                if not compare_matches.empty:
                    if len(compare_matches) == 1:
                        compare_symbol = compare_matches["Symbol"].iloc[0]
                        st.success(f"✅ Second Stock Selected: **{compare_matches['Company Name'].iloc[0]} ({compare_symbol}.NS)** (from CSV)")
                    else:
                        compare_selected_full = st.selectbox(
                            "Select a company (Second Stock):",
                            compare_matches["Searchable"].tolist(),
                            key="compare_stock_select"
                        )
                        compare_symbol = compare_selected_full.split(" - ")[0]
                        st.success(f"✅ Second Stock Selected: **{compare_symbol}.NS** (from CSV)")
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
            st.info("Please enter a company name or symbol for the second stock.")

        stock2_summary, error2 = (None, None)

        if compare_symbol:
            stock2_summary, error2 = get_stock_summary(compare_symbol)
            if error2:
                st.error(error2)

        if stock1_summary and stock2_summary:
            st.subheader("📊 Stock Comparison")

            # Prepare data for the DataFrame with separate columns
            # Removed Sector/Industry from comparison
            comparison_data = {
                "Metric": [],
                stock1_summary.get("Company Name", selected_symbol.upper()): [],
                stock2_summary.get("Company Name", compare_symbol.upper()): [],
                "Interpretation": [] # Add an interpretation column
            }

            # Helper to format numbers for display
            def format_value(value, metric_type):
                if value is None:
                    return "N/A"
                if metric_type == "percent":
                    return f"{round(value * 100, 2)}%" if isinstance(value, (int, float)) else value
                elif metric_type == "currency":
                    return f"₹ {round(value, 2)}" if isinstance(value, (int, float)) else value
                elif metric_type == "millions": # Assuming FCF is in Crores and we want to show it as is
                    return f"₹ {round(value, 2)} Cr" if isinstance(value, (int, float)) else value
                else: # General numeric or string
                    return round(value, 2) if isinstance(value, (int, float)) else value

            # Populate the comparison data dictionary
            # Use a specific order for metrics
            metrics_to_compare_config = [
                ("Current Price (₹)", "currency", "No specific interpretation for comparison."),
                ("All-Time High (₹)", "currency", "No specific interpretation for comparison."),
                ("Market Cap", "value", "Generally, larger market cap implies more stability."),
                ("P/E Ratio", "value", "Lower P/E is generally considered better (cheaper)."),
                ("EPS", "value", "Higher EPS indicates greater profitability."),
                ("Dividend Yield", "percent", "Higher dividend yield means more income for dividend investors."),
                ("Profit Margin", "percent", "Higher profit margin indicates better efficiency."),
                ("Free Cash Flow (₹ Cr)", "millions", "Higher free cash flow means more cash available for growth or dividends."),
                ("ROE", "percent", "Higher Return on Equity indicates better efficiency in generating profit from shareholder equity."),
                ("Debt to Equity", "value", "Lower Debt to Equity indicates less reliance on debt (less risky)."),
                ("PEG Ratio", "value", "Lower PEG (ideally < 1) suggests a better value relative to growth.")
            ]

            # Add Company Name and Market Cap Category first
            comparison_data["Metric"].append("Company Name")
            comparison_data[stock1_summary.get("Company Name", selected_symbol.upper())].append(stock1_summary.get("Company Name", selected_symbol.upper()))
            comparison_data[stock2_summary.get("Company Name", compare_symbol.upper())].append(stock2_summary.get("Company Name", compare_symbol.upper()))
            comparison_data["Interpretation"].append("Names of the compared companies")

            comparison_data["Metric"].append("Market Cap Category")
            comparison_data[stock1_summary.get("Company Name", selected_symbol.upper())].append(stock1_summary.get("Market Cap Category"))
            comparison_data[stock2_summary.get("Company Name", compare_symbol.upper())].append(stock2_summary.get("Market Cap Category"))
            comparison_data["Interpretation"].append("Size based on market capitalization")

            # Now add the numerical metrics
            for metric, format_type, interpretation_text in metrics_to_compare_config:
                value1 = stock1_summary.get(metric)
                value2 = stock2_summary.get(metric)

                comparison_data["Metric"].append(metric)
                comparison_data[stock1_summary.get("Company Name", selected_symbol.upper())].append(format_value(value1, format_type))
                comparison_data[stock2_summary.get("Company Name", compare_symbol.upper())].append(format_value(value2, format_type))
                comparison_data["Interpretation"].append(interpretation_text)

            comparison_df = pd.DataFrame(comparison_data).set_index("Metric")

            # Apply styling to highlight the best stock
            def apply_comparison_style(row):
                styles = [''] * len(row)
                metric = row.name # Get the metric name from the index

                # Get raw numeric values from the original summary for comparison
                raw_val1 = stock1_summary.get(metric)
                raw_val2 = stock2_summary.get(metric)

                # Identify the positions of the stock data columns in the row (for styling)
                stock1_col_name = stock1_summary.get("Company Name", selected_symbol.upper())
                stock2_col_name = stock2_summary.get("Company Name", compare_symbol.upper())

                # Get the integer position of the columns in the DataFrame row
                col_idx_stock1 = comparison_df.columns.get_loc(stock1_col_name)
                col_idx_stock2 = comparison_df.columns.get_loc(stock2_col_name)


                # Only compare if both raw values are not None
                if raw_val1 is None or raw_val2 is None:
                    return styles # Cannot compare if data is missing

                try:
                    num_val1 = float(raw_val1)
                    num_val2 = float(raw_val2)
                except (ValueError, TypeError):
                    return styles # Cannot compare non-numeric values for highlighting

                best_style = 'background-color: lightgreen; font-weight: bold;'

                # Define the comparison logic for each metric
                if metric == "P/E Ratio": # Lower is better, but only if positive
                    if num_val1 >= 0 and num_val2 >= 0:
                        if num_val1 < num_val2:
                            styles[col_idx_stock1] = best_style
                        elif num_val2 < num_val1:
                            styles[col_idx_stock2] = best_style
                    elif num_val1 is not None and num_val1 >= 0 and (num_val2 is None or num_val2 < 0): # Stock1 is valid positive, Stock2 is invalid/negative
                        styles[col_idx_stock1] = best_style
                    elif num_val2 is not None and num_val2 >= 0 and (num_val1 is None or num_val1 < 0): # Stock2 is valid positive, Stock1 is invalid/negative
                        styles[col_idx_stock2] = best_style


                elif metric in ["EPS", "Dividend Yield", "ROE", "Profit Margin", "Free Cash Flow (₹ Cr)"]:
                    # Higher is better
                    if num_val1 > num_val2:
                        styles[col_idx_stock1] = best_style
                    elif num_val2 > num_val1:
                        styles[col_idx_stock2] = best_style

                elif metric == "Debt to Equity":
                    # Lower is better (less risky)
                    if num_val1 < num_val2:
                        styles[col_idx_stock1] = best_style
                    elif num_val2 < num_val1:
                        styles[col_idx_stock2] = best_style

                elif metric == "PEG Ratio":
                    # Lower and positive is better
                    if num_val1 >= 0 and num_val2 >= 0:
                        if num_val1 < num_val2:
                            styles[col_idx_stock1] = best_style
                        elif num_val2 < num_val1:
                            styles[col_idx_stock2] = best_style
                    elif num_val1 is not None and num_val1 >= 0: # Only stock1 has a valid positive PEG
                        styles[col_idx_stock1] = best_style
                    elif num_val2 is not None and num_val2 >= 0: # Only stock2 has a valid positive PEG
                        styles[col_idx_stock2] = best_style

                elif metric == "Market Cap":
                    # For Market Cap, usually larger is considered more stable/dominant
                    if num_val1 > num_val2:
                        styles[col_idx_stock1] = best_style
                    elif num_val2 > num_val1:
                        styles[col_idx_stock2] = best_style

                # No specific highlighting for "Current Price" or "All-Time High" as "better" is subjective for these

                return styles

            # Apply the styling. `subset` specifies which columns the styling function should operate on.
            styled_df = comparison_df.style.apply(
                apply_comparison_style,
                axis=1, # Apply row-wise
                # Apply only to the stock data columns, excluding "Interpretation"
                subset=pd.Index([stock1_summary.get("Company Name", selected_symbol.upper()),
                                 stock2_summary.get("Company Name", compare_symbol.upper())])
            )

            st.dataframe(styled_df, use_container_width=True)

        elif stock1_summary: # Only stock1 summary available, display its single view
            if st.session_state.compare_search_input and not compare_symbol:
                st.warning("Please select a valid second stock from the dropdown or search result to enable full comparison.")
            else:
                st.info("Enter a second stock in the search bar above to enable comparison.") # More helpful message

            # The single stock display logic remains here, but moved outside the `if compare_symbol` block
            # to be executed if compare_mode is true but no valid second stock is selected yet.
            st.subheader(f"📋 Fundamentals Summary for {stock1_summary.get('Company Name', selected_symbol.upper())}")
            # For single view, we want full interpretations back
            single_stock_display_summary = {
                "Company Name": stock1_summary.get("Company Name"),
                "Symbol": stock1_summary.get("Symbol"),
                "Current Price (₹)": stock1_summary.get("Current Price (₹)"),
                "All-Time High (₹)": stock1_summary.get("All-Time High (₹)") + f" ({round((stock1_summary.get('Current Price (₹)') - stock1_summary.get('All-Time High (₹)')) / stock1_summary.get('All-Time High (₹)') * 100, 2)}%)" if stock1_summary.get('All-Time High (₹)') is not None and stock1_summary.get('Current Price (₹)') is not None and stock1_summary.get('All-Time High (₹)') !=0 else "N/A", # Add percentage change for single view
                "Market Cap": f"₹ {round(stock1_summary.get('Market Cap') / 1e9, 2)} B ({stock1_summary.get('Market Cap Category')})", # Add category back
                "P/E Ratio": interpret_pe_no_industry(stock1_summary.get("P/E Ratio")), # Simplified P/E interpretation
                "EPS": f"{round(stock1_summary.get('EPS'), 2)} {get_eps_icon(interpret_eps_raw(stock1_summary.get('EPS')))}" if stock1_summary.get("EPS") is not None else "N/A",
                "Dividend Yield": f"{round(stock1_summary.get('Dividend Yield')*100,2)}% {get_dividend_icon(interpret_dividend_yield_raw(stock1_summary.get('Dividend Yield')))}" if stock1_summary.get("Dividend Yield") is not None else "N/A",
                "Profit Margin": f"{round(stock1_summary.get('Profit Margin')*100,2)}%" if stock1_summary.get('Profit Margin') is not None else "N/A", # Formatted for single view
                "Free Cash Flow (₹ Cr)": f"₹ {round(stock1_summary.get('Free Cash Flow (₹ Cr)'), 2)} Cr" if stock1_summary.get('Free Cash Flow (₹ Cr)') != 'N/A' else "N/A", # Ensure formatting
                "ROE": f"{round(stock1_summary.get('ROE')*100,2)}% {get_roe_icon(interpret_roe_raw(stock1_summary.get('ROE')))}" if stock1_summary.get("ROE") is not None else "N/A",
                "Debt to Equity": f"{round(stock1_summary.get('Debt to Equity'),2)} {get_de_icon(interpret_de_ratio_raw(stock1_summary.get('Debt to Equity')))}" if stock1_summary.get("Debt to Equity") is not None else "N/A",
                "PEG Ratio": f"{stock1_summary.get('PEG Ratio')} (Lower is better)" if stock1_summary.get('PEG Ratio') is not None else "N/A"
            }

            df = pd.DataFrame(single_stock_display_summary.items(), columns=["Metric", "Value"])
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
            st.subheader("💰 Historical Free Cash Flow (₹ in Crores)")

            try:
                stock_yf = yf.Ticker(selected_symbol + ".NS")
                cash_flow_statement = stock_yf.cashflow

                if not cash_flow_statement.empty and 'Free Cash Flow' in cash_flow_statement.index:
                    fcf_df = cash_flow_statement.loc[['Free Cash Flow']].transpose()
                    fcf_df.index = fcf_df.index.year
                    fcf_df.rename(columns={'Free Cash Flow': 'Free Cash Flow (₹ Cr)'}, inplace=True)
                    fcf_df['Free Cash Flow (₹ Cr)'] = fcf_df['Free Cash Flow'] / 1e7
                    st.bar_chart(fcf_df[['Free Cash Flow (₹ Cr)']].round(2))
                else:
                    st.warning("Free Cash Flow data not available in cash flow statements.")
            except Exception as e:
                st.warning(f"Could not retrieve historical Free Cash Flow data. Error: {e}")

            st.subheader("📈 Historical Revenue (₹ in Crores)")

            try:
                stock_yf = yf.Ticker(selected_symbol + ".NS")
                financials = stock_yf.financials
                if not financials.empty and "Total Revenue" in financials.index:
                    revenue_df = financials.loc[["Total Revenue"]].transpose()
                    revenue_df.index = revenue_df.index.year
                    revenue_df["Total Revenue"] = (revenue_df["Total Revenue"] / 1e7)
                    st.bar_chart(revenue_df[["Total Revenue"].round(2)])
                else:
                    st.warning("Total Revenue data not available in financials.")
            except Exception as e:
                st.warning(f"Could not retrieve historical revenue data. Error: {e}")

    else: # Not in compare mode (single stock view)
        # Display the single stock summary directly
        if stock1_summary:
            st.subheader(f"📋 Stock Fundamentals Summary for {stock1_summary.get('Company Name', selected_symbol.upper())}")
            # For single view, we want full interpretations back
            single_stock_display_summary = {
                "Company Name": stock1_summary.get("Company Name"),
                "Symbol": stock1_summary.get("Symbol"),
                "Current Price (₹)": stock1_summary.get("Current Price (₹)"),
                "All-Time High (₹)": stock1_summary.get("All-Time High (₹)") + f" ({round((stock1_summary.get('Current Price (₹)') - stock1_summary.get('All-Time High (₹)')) / stock1_summary.get('All-Time High (₹)') * 100, 2)}%)" if stock1_summary.get('All-Time High (₹)') is not None and stock1_summary.get('Current Price (₹)') is not None and stock1_summary.get('All-Time High (₹)') !=0 else "N/A",
                "Market Cap": f"₹ {round(stock1_summary.get('Market Cap') / 1e9, 2)} B ({stock1_summary.get('Market Cap Category')})",
                "P/E Ratio": interpret_pe_no_industry(stock1_summary.get("P/E Ratio")),
                "EPS": f"{round(stock1_summary.get('EPS'), 2)} {get_eps_icon(interpret_eps_raw(stock1_summary.get('EPS')))}" if stock1_summary.get("EPS") is not None else "N/A",
                "Dividend Yield": f"{round(stock1_summary.get('Dividend Yield')*100,2)}% {get_dividend_icon(interpret_dividend_yield_raw(stock1_summary.get('Dividend Yield')))}" if stock1_summary.get("Dividend Yield") is not None else "N/A",
                "Profit Margin": f"{round(stock1_summary.get('Profit Margin')*100,2)}%" if stock1_summary.get('Profit Margin') is not None else "N/A",
                "Free Cash Flow (₹ Cr)": f"₹ {round(stock1_summary.get('Free Cash Flow (₹ Cr)'), 2)} Cr" if stock1_summary.get('Free Cash Flow (₹ Cr)') != 'N/A' else "N/A",
                "ROE": f"{round(stock1_summary.get('ROE')*100,2)}% {get_roe_icon(interpret_roe_raw(stock1_summary.get('ROE')))}" if stock1_summary.get("ROE") is not None else "N/A",
                "Debt to Equity": f"{round(stock1_summary.get('Debt to Equity'),2)} {get_de_icon(interpret_de_ratio_raw(stock1_summary.get('Debt to Equity')))}" if stock1_summary.get("Debt to Equity") is not None else "N/A",
                "PEG Ratio": f"{stock1_summary.get('PEG Ratio')} (Lower is better)" if stock1_summary.get('PEG Ratio') is not None else "N/A"
            }
            df = pd.DataFrame(single_stock_display_summary.items(), columns=["Metric", "Value"])
            st.dataframe(df.set_index("Metric"))

            st.subheader("📉 Historical Stock Price Chart")

            try:
                stock_yf = yf.Ticker(selected_symbol + ".NS")
                period = st.selectbox("Select period for price chart:", ["1mo", "3mo", "6mo", "1y", "5y", "max"], index=4, key="price_period_single") # Changed key for single mode
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
            st.subheader("💰 Historical Free Cash Flow (₹ in Crores)")

            try:
                stock_yf = yf.Ticker(selected_symbol + ".NS")
                cash_flow_statement = stock_yf.cashflow

                if not cash_flow_statement.empty and 'Free Cash Flow' in cash_flow_statement.index:
                    fcf_df = cash_flow_statement.loc[['Free Cash Flow']].transpose()
                    fcf_df.index = fcf_df.index.year
                    fcf_df.rename(columns={'Free Cash Flow': 'Free Cash Flow (₹ Cr)'}, inplace=True)
                    fcf_df['Free Cash Flow (₹ Cr)'] = fcf_df['Free Cash Flow'] / 1e7
                    st.bar_chart(fcf_df[['Free Cash Flow (₹ Cr)']].round(2))
                else:
                    st.warning("Free Cash Flow data not available in cash flow statements.")
            except Exception as e:
                st.warning(f"Could not retrieve historical Free Cash Flow data. Error: {e}")

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
        else:
            st.warning("No primary stock selected. Please select a primary stock to view its fundamentals.")
