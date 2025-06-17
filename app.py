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

# Load dynamic search CSV - Now robustly checks for Sector/Industry
@st.cache_data
def load_stock_data():
    try:
        df = pd.read_csv("nse stocks.csv")
        df["Searchable"] = df["Symbol"] + " - " + df["Company Name"]

        # Check if Sector and Industry columns exist, if not, add them with None/N/A
        if 'Sector' not in df.columns:
            df['Sector'] = None
            st.warning("Warning: 'Sector' column not found in 'nse_stocks.csv'. Sector-based features will be limited.")
        if 'Industry' not in df.columns:
            df['Industry'] = None
            st.warning("Warning: 'Industry' column not found in 'nse_stocks.csv'. Industry-based features will be limited.")

        return df
    except FileNotFoundError:
        st.error("Error: 'nse_stocks.csv' not found. Please make sure the file is in the same directory as the app.")
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
    # Add more as needed
}

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

# This function will now be used internally for comparison logic, not directly displayed
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

# This function will now be used internally for comparison logic, not directly displayed
def interpret_pe_raw(pe, industry_pe):
    if pe is None or industry_pe is None:
        return "N/A"
    diff = pe - industry_pe
    if diff > 10:
        return "Overvalued"
    elif diff > 2:
        return "Slightly Overvalued"
    elif diff < -2:
        return "Undervalued"
    else:
        return "Fairly Priced"

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
                if cagr <= 0:
                    return None, "EPS CAGR is non-positive, PEG not meaningful"
                peg = pe_ratio / (cagr * 100)
                return round(peg, 2), None
            else:
                return None, "CAGR or PE unavailable"
        else:
            return None, "Not enough EPS data for 5-year CAGR"

    except Exception as e:
        return None, f"Error calculating PEG: {e}"

# This function will now be used internally for comparison logic, not directly displayed
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

# This function will now be used internally for comparison logic, not directly displayed
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

# This function will now be used internally for comparison logic, not directly displayed
def interpret_de_ratio_raw(de):
    if de is None:
        return "N/A"
    try:
        de = float(de)
    except (ValueError, TypeError):
        return "N/A"
    de_ratio = round(de / 100, 2) # Assuming yfinance gives percentage for Indian stocks here
    if de_ratio < 1:
        return "Low Debt"
    elif 1 <= de_ratio < 2:
        return "Moderate Debt"
    else:
        return "High Debt"


@st.cache_data(ttl=3600) # Cache for 1 hour (3600 seconds)
def get_stock_summary(ticker_symbol):
    full_ticker = ticker_symbol + ".NS"
    stock = yf.Ticker(full_ticker)

    try:
        info = stock.info

        if not info or "longName" not in info:
            return None, f"⚠️ Could not fetch data for **{ticker_symbol.upper()}**. Please check the symbol."

        sector = info.get("sector", "N/A")
        industry = info.get("industry", "N/A")

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
            f"{round(market_cap / 1e9, 2)} B ({get_category_icon(market_cap_category)} {market_cap_category})"
            if market_cap else "N/A"
        )

        hist = stock.history(period="max")
        all_time_high = "N/A"
        ath_change_display = "N/A"

        if not hist.empty and current_price:
            all_time_high = round(hist["High"].max(), 2)
            if all_time_high != 0:
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

        profit_margin_percent = (
            "N/A" if profit_margin is None else
            f"{round(profit_margin * 100, 2)}% ❌ (Loss-Making)" if profit_margin < 0 else
            f"{round(profit_margin * 100, 2)}%"
        )
        peg, peg_msg = get_eps_cagr_based_peg(full_ticker)

        summary = {
            "Company Name": info.get("longName"),
            "Symbol": ticker_symbol,
            "Sector": sector,
            "Industry": industry,
            "Current Price (₹)": current_price,
            "All-Time High (₹)": ath_change_display,
            "Market Cap": market_cap_display,
            "P/E Ratio": stock_pe, # Raw value
            "EPS": trailing_eps, # Raw value
            "Dividend Yield": dividend_yield, # Raw value
            "Profit Margin": profit_margin_percent, # Still a formatted string
            "Free Cash Flow (₹ Cr)": free_cash_flow, # Formatted
            "ROE": return_on_equity, # Raw value
            "Debt to Equity": debt_to_equity, # Raw value
            "PEG Ratio": peg # Raw value
        }
        return summary, None
    except Exception as e:
        return None, f"Error processing stock: **{ticker_symbol.upper()}** - {e}"

# --- NEW FUNCTION FOR COMPARISON INTERPRETATION ---
def compare_and_interpret_metric(metric_name, value1, value2, industry_pe=None):
    """
    Compares two values for a given metric and returns a combined interpretation.
    Highlights the 'better' value with an emoji.
    """
    if value1 is None and value2 is None:
        return "N/A"
    
    # Handle cases where one value is None
    if value1 is None:
        return f"{value2} (N/A for Stock 1)"
    if value2 is None:
        return f"{value1} (N/A for Stock 2)"

    try:
        # Convert to float for comparison if possible
        num_value1 = float(value1)
        num_value2 = float(value2)
    except (ValueError, TypeError):
        # If values are not numerical (e.g., 'N/A' strings), compare them directly or just display both
        return f"{value1} | {value2}"

    interpretation_text = ""
    stock1_str = str(round(num_value1, 2)) if isinstance(num_value1, (int, float)) else str(num_value1)
    stock2_str = str(round(num_value2, 2)) if isinstance(num_value2, (int, float)) else str(num_value2)

    # Specific logic for each metric
    if metric_name == "P/E Ratio":
        # Lower P/E is generally better, but also consider undervaluation/overvaluation
        interpretation1 = interpret_pe_raw(num_value1, industry_pe)
        interpretation2 = interpret_pe_raw(num_value2, industry_pe)
        
        # Prioritize "Undervalued"
        if interpretation1 == "Undervalued" and interpretation2 != "Undervalued":
            return f"{stock1_str} ✅ (Undervalued) | {stock2_str} ({interpretation2})"
        elif interpretation2 == "Undervalued" and interpretation1 != "Undervalued":
            return f"{stock1_str} ({interpretation1}) | {stock2_str} ✅ (Undervalued)"
        # Then consider "Fairly Priced"
        elif interpretation1 == "Fairly Priced" and interpretation2 == "Overvalued":
             return f"{stock1_str} ✅ (Fair) | {stock2_str} ({interpretation2})"
        elif interpretation2 == "Fairly Priced" and interpretation1 == "Overvalued":
             return f"{stock1_str} ({interpretation1}) | {stock2_str} ✅ (Fair)"
        # If both are good/fair, lower is still slightly better
        elif num_value1 < num_value2:
            return f"{stock1_str} ✅ ({interpretation1}) | {stock2_str} ({interpretation2})"
        elif num_value2 < num_value1:
            return f"{stock1_str} ({interpretation1}) | {stock2_str} ✅ ({interpretation2})"
        else:
            return f"{stock1_str} ({interpretation1}) | {stock2_str} ({interpretation2}) (Similar)"

    elif metric_name == "EPS":
        # Higher EPS is better
        if num_value1 > num_value2:
            return f"{stock1_str} ✅ (Better EPS) | {stock2_str}"
        elif num_value2 > num_value1:
            return f"{stock1_str} | {stock2_str} ✅ (Better EPS)"
        else:
            return f"{stock1_str} | {stock2_str} (Similar EPS)"

    elif metric_name == "Dividend Yield":
        # Higher Dividend Yield is better (for dividend-seeking investors)
        if num_value1 > num_value2:
            return f"{stock1_str}% ✅ (Higher Yield) | {stock2_str}%"
        elif num_value2 > num_value1:
            return f"{stock1_str}% | {stock2_str}% ✅ (Higher Yield)"
        else:
            return f"{stock1_str}% | {stock2_str}% (Similar Yield)"

    elif metric_name == "ROE":
        # Higher ROE is better
        num_value1_percent = round(num_value1 * 100, 2)
        num_value2_percent = round(num_value2 * 100, 2)
        if num_value1 > num_value2:
            return f"{num_value1_percent}% ✅ (Higher ROE) | {num_value2_percent}%"
        elif num_value2 > num_value1:
            return f"{num_value1_percent}% | {num_value2_percent}% ✅ (Higher ROE)"
        else:
            return f"{num_value1_percent}% | {num_value2_percent}% (Similar ROE)"

    elif metric_name == "Debt to Equity":
        # Lower Debt to Equity is better (less risky)
        num_value1_ratio = round(num_value1 / 100, 2)
        num_value2_ratio = round(num_value2 / 100, 2)
        if num_value1 < num_value2:
            return f"{num_value1_ratio} ✅ (Lower Debt) | {num_value2_ratio}"
        elif num_value2 < num_value1:
            return f"{num_value1_ratio} | {num_value2_ratio} ✅ (Lower Debt)"
        else:
            return f"{num_value1_ratio} | {num_value2_ratio} (Similar Debt)"

    elif metric_name == "PEG Ratio":
        # Lower PEG is better (ideally < 1)
        if num_value1 < num_value2 and num_value1 >= 0: # PEG should be positive to be meaningful
            return f"{stock1_str} ✅ (Better PEG) | {stock2_str}"
        elif num_value2 < num_value1 and num_value2 >= 0:
            return f"{stock1_str} | {stock2_str} ✅ (Better PEG)"
        else:
            return f"{stock1_str} | {stock2_str} (Similar PEG or not ideal)"

    # For other metrics, just display both values or handle as needed
    return f"{stock1_str} | {stock2_str}"


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

# --- Sector Explorer Dropdown (Conditional based on 'Sector' column presence) ---
st.subheader("Explore Stocks by Sector")
if 'Sector' in nse_df.columns and not nse_df['Sector'].isnull().all(): # Check if column exists AND has data
    all_sectors = nse_df['Sector'].dropna().unique().tolist()
    all_sectors.sort()

    selected_sector_display = st.selectbox(
        "Select a Sector:",
        ["Select a Sector to view companies"] + all_sectors,
        key="sector_explorer"
    )

    if selected_sector_display != "Select a Sector to view companies":
        filtered_stocks_by_sector = nse_df[nse_df['Sector'] == selected_sector_display].copy()
        if not filtered_stocks_by_sector.empty:
            st.markdown(f"**Companies in {selected_sector_display} Sector ({len(filtered_stocks_by_sector)} companies):**")

            # Allow selecting a stock from this list to automatically analyze it
            filtered_stock_options = [""] + filtered_stocks_by_sector["Searchable"].tolist()
            selected_stock_from_sector = st.selectbox(
                "Select a stock from this sector to analyze it above:",
                filtered_stock_options,
                key="select_stock_from_sector"
            )

            if selected_stock_from_sector:
                st.session_state.user_input_value = selected_stock_from_sector.split(" - ")[0]
                st.rerun()

            st.dataframe(filtered_stocks_by_sector[['Symbol', 'Company Name', 'Industry']].set_index('Symbol'))
        else:
            st.info(f"No stocks found for the {selected_sector_display} sector in your data.")
else:
    st.warning("""
        **Feature Unavailable:** To use 'Explore Stocks by Sector', your 'nse_stocks.csv' must contain a 'Sector' column with data.

        **How to enable this feature:**
        1.  **Run the `enrich_nse_data.py` script (provided above) once.** This script will fetch Sector and Industry data for all stocks from Yahoo Finance and save it to a new CSV.
        2.  **Rename/Copy** the generated `nse_stocks_enriched.csv` to `nse_stocks.csv` (or copy it) to use with your Streamlit app.
        3.  **Re-run your Streamlit app.**
        """)

st.markdown("---")

compare_mode = st.checkbox("🔄 Compare stocks")

# Main app logic
if selected_symbol:
    if compare_mode:
        st.subheader("🆚 Compare With Another Stock")

        compare_col_main, compare_col_competitors = st.columns([0.7, 0.3])

        with compare_col_main:
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

            stock1_summary, error1 = get_stock_summary(selected_symbol)
            stock2_summary, error2 = (None, None)

            if error1:
                st.error(error1)

            if compare_symbol:
                stock2_summary, error2 = get_stock_summary(compare_symbol)
                if error2:
                    st.error(error2)

            if stock1_summary and stock2_summary:
                st.subheader("📊 Stock Comparison")

                comparison_metrics = [
                    "Current Price (₹)",
                    "All-Time High (₹)",
                    "Market Cap",
                    "P/E Ratio",
                    "EPS",
                    "Dividend Yield",
                    "Profit Margin",
                    "Free Cash Flow (₹ Cr)",
                    "ROE",
                    "Debt to Equity",
                    "PEG Ratio"
                ]

                comparison_data = {}
                stock1_name = stock1_summary.get("Company Name", selected_symbol.upper())
                stock2_name = stock2_summary.get("Company Name", compare_symbol.upper())

                for metric in comparison_metrics:
                    value1 = stock1_summary.get(metric)
                    value2 = stock2_summary.get(metric)

                    if metric == "P/E Ratio":
                        industry_pe1 = INDUSTRY_PE.get(stock1_summary.get("Sector"))
                        industry_pe2 = INDUSTRY_PE.get(stock2_summary.get("Sector"))
                        
                        # Use the P/E of the primary stock's sector for interpretation, or average if both available
                        effective_industry_pe = industry_pe1 
                        if industry_pe1 is None and industry_pe2 is not None:
                            effective_industry_pe = industry_pe2
                        elif industry_pe1 is not None and industry_pe2 is not None:
                             effective_industry_pe = (industry_pe1 + industry_pe2) / 2 # Can adjust this logic
                        
                        comparison_data[metric] = compare_and_interpret_metric(metric, value1, value2, effective_industry_pe)
                    elif metric in ["EPS", "Dividend Yield", "ROE", "Debt to Equity", "PEG Ratio"]:
                        comparison_data[metric] = compare_and_interpret_metric(metric, value1, value2)
                    elif metric == "Current Price (₹)" or metric == "All-Time High (₹)":
                        # For these, just display both values as direct comparison is usually desired
                        comparison_data[metric] = f"{value1} | {value2}"
                    elif metric == "Market Cap":
                        # Market cap display is already formatted string, just combine
                        comparison_data[metric] = f"{value1} | {value2}"
                    elif metric == "Profit Margin":
                         # Profit margin is already formatted string, just combine
                         comparison_data[metric] = f"{value1} | {value2}"
                    elif metric == "Free Cash Flow (₹ Cr)":
                        # Free cash flow is already formatted string, just combine
                        comparison_data[metric] = f"{value1} | {value2}"
                    else:
                        comparison_data[metric] = f"{value1} | {value2}" # Default for others

                comparison_df = pd.DataFrame(comparison_data.items(), columns=["Metric", "Comparison Result"])
                comparison_df = comparison_df.set_index("Metric")

                # Add a row for the company names to the header
                header_row = pd.DataFrame({
                    "Metric": ["Company Name"],
                    "Comparison Result": [f"{stock1_name} | {stock2_name}"]
                }).set_index("Metric")

                st.dataframe(pd.concat([header_row, comparison_df]))


            elif stock1_summary:
                if st.session_state.compare_search_input and not compare_symbol:
                    st.warning("Please select a valid second stock from the dropdown or search result.")
                else:
                    st.warning("Please search and select a second stock to compare for full comparison view.")
                st.subheader(f"📋 Fundamentals Summary for {stock1_summary.get('Company Name', selected_symbol.upper())}")
                # For single view, we want full interpretations back
                single_stock_display_summary = {
                    "Company Name": stock1_summary.get("Company Name"),
                    "Symbol": stock1_summary.get("Symbol"),
                    "Sector": stock1_summary.get("Sector"),
                    "Industry": stock1_summary.get("Industry"),
                    "Current Price (₹)": stock1_summary.get("Current Price (₹)"),
                    "All-Time High (₹)": stock1_summary.get("All-Time High (₹)"),
                    "Market Cap": stock1_summary.get("Market Cap"),
                    "P/E vs Industry": interpret_pe_with_industry(stock1_summary.get("P/E Ratio"), INDUSTRY_PE.get(stock1_summary.get("Sector"))),
                    "EPS": interpret_eps_raw(stock1_summary.get("EPS")) + f" ({round(stock1_summary.get('EPS'),2)})" if stock1_summary.get("EPS") is not None else "N/A",
                    "Dividend Yield": interpret_dividend_yield_raw(stock1_summary.get("Dividend Yield")) + f" ({round(stock1_summary.get('Dividend Yield')*100,2)}%)" if stock1_summary.get("Dividend Yield") is not None else "N/A",
                    "Profit Margin": stock1_summary.get("Profit Margin"),
                    "Free Cash Flow (₹ Cr)": stock1_summary.get("Free Cash Flow (₹ Cr)"),
                    "ROE": interpret_roe_raw(stock1_summary.get("ROE")) + f" ({round(stock1_summary.get('ROE')*100,2)}%)" if stock1_summary.get("ROE") is not None else "N/A",
                    "Debt to Equity": interpret_de_ratio_raw(stock1_summary.get("Debt to Equity")) + f" ({round(stock1_summary.get('Debt to Equity')/100,2)})" if stock1_summary.get("Debt to Equity") is not None else "N/A",
                    "PEG Ratio": f"{stock1_summary.get('PEG Ratio')} (Lower is better)" if stock1_summary.get('PEG Ratio') is not None else "N/A"
                }

                df = pd.DataFrame(single_stock_display_summary.items(), columns=["Metric", "Value"])
                st.dataframe(df.set_index("Metric"))
            else:
                st.warning("No primary stock selected. Please select a primary stock to begin comparison or single view.")


        with compare_col_competitors:
            st.subheader("Similar Companies")
            # --- Competitor Section (Conditional based on 'Sector' column presence) ---
            if 'Sector' in nse_df.columns and not nse_df['Sector'].isnull().all() and stock1_summary and selected_symbol:
                selected_sector = stock1_summary.get('Sector')
                selected_industry = stock1_summary.get('Industry')

                if selected_sector and selected_sector != 'N/A':
                    competitors = nse_df[
                        ((nse_df['Sector'] == selected_sector) | (nse_df['Industry'] == selected_industry)) &
                        (nse_df['Symbol'] != selected_symbol)
                    ].copy()

                    if not competitors.empty:
                        competitors['Match_Type'] = competitors.apply(
                            lambda row: 2 if row['Industry'] == selected_industry else (1 if row['Sector'] == selected_sector else 0),
                            axis=1
                        )
                        competitors = competitors.sort_values(by=['Match_Type', 'Company Name'], ascending=[False, True])

                        competitor_options = competitors["Searchable"].head(15).tolist()

                        selected_competitor_from_list = st.selectbox(
                            "Select a competitor to compare:",
                            [""] + competitor_options,
                            key="competitor_select"
                        )

                        if selected_competitor_from_list:
                            st.session_state.compare_search_input = selected_competitor_from_list.split(" - ")[0]
                            st.rerun()
                    else:
                        st.info(f"No other companies found in the same sector ('{selected_sector}') or industry ('{selected_industry}') in your enriched CSV.")
                else:
                    st.info(f"Sector/Industry data for {selected_symbol} is not available or 'N/A' to find similar companies from your CSV.")
            else:
                st.warning("""
                    **Feature Unavailable:** To see similar companies, your 'nse_stocks.csv' must contain populated 'Sector' and 'Industry' columns.

                    **How to enable this feature:**
                    1.  **Run the `enrich_nse_data.py` script (provided above) once.**
                    2.  **Rename/Copy** the generated `nse_stocks_enriched.csv` to `nse_stocks.csv`.
                    3.  **Re-run your Streamlit app.**
                    """)

        if stock1_summary and stock2_summary:
            st.markdown("---")
            st.subheader("📈 Historical Data Comparison")

            compare_chart_period = st.selectbox(
                "Select period for historical charts:",
                ["1mo", "3mo", "6mo", "1y", "3y", "5y", "max"],
                index=4,
                key="compare_chart_period"
            )

            st.markdown("##### 📉 Historical Price Chart")
            col1_price, col2_price = st.columns(2)
            with col1_price:
                try:
                    stock1_yf = yf.Ticker(selected_symbol + ".NS")
                    hist_price1 = stock1_yf.history(period=compare_chart_period)
                    if not hist_price1.empty:
                        st.line_chart(hist_price1["Close"].round(2).rename(stock1_name))
                    else:
                        st.warning(f"No price data for {stock1_name}")
                except Exception as e:
                    st.warning(f"Could not load price chart for {stock1_name}. Error: {e}")

            with col2_price:
                try:
                    stock2_yf = yf.Ticker(compare_symbol + ".NS")
                    hist_price2 = stock2_yf.history(period=compare_chart_period)
                    if not hist_price2.empty:
                        st.line_chart(hist_price2["Close"].round(2).rename(stock2_name))
                    else:
                        st.warning(f"No price data for {stock2_name}")
                except Exception as e:
                    st.warning(f"Could not load price chart for {stock2_name}. Error: {e}")

            st.markdown("##### 📊 Historical Profit After Tax (PAT in ₹ Crores)")
            col1_pat, col2_pat = st.columns(2)
            with col1_pat:
                try:
                    stock1_yf = yf.Ticker(selected_symbol + ".NS")
                    financials1 = stock1_yf.financials
                    if not financials1.empty and "Net Income" in financials1.index:
                        pat_df1 = financials1.loc[["Net Income"]].transpose()
                        pat_df1.index = pat_df1.index.year
                        pat_df1["PAT"] = (pat_df1["Net Income"] / 1e7)
                        st.bar_chart(pat_df1[["PAT"]].round(2).rename(columns={'PAT': stock1_name + ' PAT'}))
                    else:
                        st.warning(f"No PAT data for {stock1_name}")
                except Exception as e:
                    st.warning(f"Could not retrieve PAT data for {stock1_name}. Error: {e}")

            with col2_pat:
                try:
                    stock2_yf = yf.Ticker(compare_symbol + ".NS")
                    financials2 = stock2_yf.financials
                    if not financials2.empty and "Net Income" in financials2.index:
                        pat_df2 = financials2.loc[["Net Income"]].transpose()
                        pat_df2.index = pat_df2.index.year
                        pat_df2["PAT"] = (pat_df2["Net Income"] / 1e7)
                        st.bar_chart(pat_df2[["PAT"]].round(2).rename(columns={'PAT': stock2_name + ' PAT'}))
                    else:
                        st.warning(f"No PAT data for {stock2_name}")
                except Exception as e:
                    st.warning(f"Could not retrieve PAT data for {stock2_name}. Error: {e}")

            st.markdown("##### 📈 Historical Revenue (₹ in Crores)")
            col1_rev, col2_rev = st.columns(2)
            with col1_rev:
                try:
                    stock1_yf = yf.Ticker(selected_symbol + ".NS")
                    financials1 = stock1_yf.financials
                    if not financials1.empty and "Total Revenue" in financials1.index:
                        revenue_df1 = financials1.loc[["Total Revenue"]].transpose()
                        revenue_df1.index = revenue_df1.index.year
                        revenue_df1["Total Revenue"] = (revenue_df1["Total Revenue"] / 1e7)
                        st.bar_chart(revenue_df1[["Total Revenue"]].round(2).rename(columns={'Total Revenue': stock1_name + ' Revenue'}))
                    else:
                        st.warning(f"No Revenue data for {stock1_name}")
                except Exception as e:
                    st.warning(f"Could not retrieve revenue data for {stock1_name}. Error: {e}")

            with col2_rev:
                try:
                    stock2_yf = yf.Ticker(compare_symbol + ".NS")
                    financials2 = stock2_yf.financials
                    if not financials2.empty and "Total Revenue" in financials2.index:
                        revenue_df2 = financials2.loc[["Total Revenue"]].transpose()
                        revenue_df2.index = revenue_df2.index.year
                        revenue_df2["Total Revenue"] = (revenue_df2["Total Revenue"] / 1e7)
                        st.bar_chart(revenue_df2[["Total Revenue"]].round(2).rename(columns={'Total Revenue': stock2_name + ' Revenue'}))
                    else:
                        st.warning(f"No Revenue data for {stock2_name}")
                except Exception as e:
                    st.warning(f"Could not retrieve revenue data for {stock2_name}. Error: {e}")

            st.markdown("##### 💰 Historical Free Cash Flow (₹ in Crores)")
            col1_fcf, col2_fcf = st.columns(2)
            with col1_fcf:
                try:
                    stock1_yf = yf.Ticker(selected_symbol + ".NS")
                    cash_flow_statement1 = stock1_yf.cashflow
                    if not cash_flow_statement1.empty and 'Free Cash Flow' in cash_flow_statement1.index:
                        fcf_df1 = cash_flow_statement1.loc[['Free Cash Flow']].transpose()
                        fcf_df1.index = fcf_df1.index.year
                        fcf_df1['Free Cash Flow (₹ Cr)'] = fcf_df1['Free Cash Flow'] / 1e7
                        st.bar_chart(fcf_df1[['Free Cash Flow (₹ Cr)']].round(2).rename(columns={'Free Cash Flow (₹ Cr)': stock1_name + ' FCF'}))
                    else:
                        st.warning(f"No FCF data for {stock1_name}")
                except Exception as e:
                    st.warning(f"Could not retrieve FCF data for {stock1_name}. Error: {e}")

            with col2_fcf:
                try:
                    stock2_yf = yf.Ticker(compare_symbol + ".NS")
                    cash_flow_statement2 = stock2_yf.cashflow
                    if not cash_flow_statement2.empty and 'Free Cash Flow' in cash_flow_statement2.index:
                        fcf_df2 = cash_flow_statement2.loc[['Free Cash Flow']].transpose()
                        fcf_df2.index = fcf_df2.index.year
                        fcf_df2['Free Cash Flow (₹ Cr)'] = fcf_df2['Free Cash Flow'] / 1e7
                        st.bar_chart(fcf_df2[['Free Cash Flow (₹ Cr)']].round(2).rename(columns={'Free Cash Flow (₹ Cr)': stock2_name + ' FCF'}))
                    else:
                        st.warning(f"No FCF data for {stock2_name}")
                except Exception as e:
                    st.warning(f"Could not retrieve FCF data for {stock2_name}. Error: {e}")

    else: # Not in compare mode (single stock view)
        stock_summary, error = get_stock_summary(selected_symbol)

        if error:
            st.error(error)
        elif stock_summary:
            # Re-interpret for single stock view with the original full interpretations
            single_stock_display_summary = {
                "Company Name": stock_summary.get("Company Name"),
                "Symbol": stock_summary.get("Symbol"),
                "Sector": stock_summary.get("Sector"),
                "Industry": stock_summary.get("Industry"),
                "Current Price (₹)": stock_summary.get("Current Price (₹)"),
                "All-Time High (₹)": stock_summary.get("All-Time High (₹)"),
                "Market Cap": stock_summary.get("Market Cap"),
                "P/E vs Industry": interpret_pe_with_industry(stock_summary.get("P/E Ratio"), INDUSTRY_PE.get(stock_summary.get("Sector"))),
                "EPS": f"{round(stock_summary.get('EPS'), 2)} {get_eps_icon(interpret_eps_raw(stock_summary.get('EPS')))}" if stock_summary.get("EPS") is not None else "N/A",
                "Dividend Yield": f"{round(stock_summary.get('Dividend Yield')*100,2)}% {get_dividend_icon(interpret_dividend_yield_raw(stock_summary.get('Dividend Yield')))}" if stock_summary.get("Dividend Yield") is not None else "N/A",
                "Profit Margin": stock_summary.get("Profit Margin"),
                "Free Cash Flow (₹ Cr)": stock_summary.get("Free Cash Flow (₹ Cr)"),
                "ROE": f"{round(stock_summary.get('ROE')*100,2)}% {get_roe_icon(interpret_roe_raw(stock_summary.get('ROE')))}" if stock_summary.get("ROE") is not None else "N/A",
                "Debt to Equity": f"{round(stock_summary.get('Debt to Equity')/100,2)} {get_de_icon(interpret_de_ratio_raw(stock_summary.get('Debt to Equity')))}" if stock_summary.get("Debt to Equity") is not None else "N/A",
                "PEG Ratio": f"{stock_summary.get('PEG Ratio')} (Lower is better)" if stock_summary.get('PEG Ratio') is not None else "N/A"
            }
            df = pd.DataFrame(single_stock_display_summary.items(), columns=["Metric", "Value"])

            st.subheader(f"📋 Stock Fundamentals Summary for {stock_summary.get('Company Name', selected_symbol.upper())}")
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
                    fcf_df['Free Cash Flow (₹ Cr)'] = fcf_df['Free Cash Flow (₹ Cr)'] / 1e7
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

# Helper functions for single stock view interpretations (added for consistency)
def get_eps_icon(interpretation):
    return "🔴" if interpretation == "Negative" else ("🟠" if interpretation == "Low" else "✅")

def get_dividend_icon(interpretation):
    return "🔴" if interpretation == "No dividends" else ("🟠" if interpretation == "Low" else "✅")

def get_roe_icon(interpretation):
    return "🟠" if interpretation == "Low" else ("🟡" if interpretation == "Moderate" else "✅")

def get_de_icon(interpretation):
    return "🔴" if interpretation == "High Debt" else ("🟡" if interpretation == "Moderate Debt" else "✅")
