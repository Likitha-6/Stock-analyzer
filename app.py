import streamlit as st
import yfinance as yf
import pandas as pd
import requests
import difflib
import numpy as np
import plotly.graph_objs as go

# Streamlit setup
st.set_page_config(page_title="Indian Stock Analyzer", page_icon="📊")
st.title("📈 Indian Stock Analyzer (Fundamentals)")
st.markdown("---")
compare_mode = st.checkbox("🔄 Compare stocks")


def load_stock_data():
    try:
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
    "Automotive": 22.1, 
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
    de_ratio=round(de/100,2)

    if de_ratio < 1:
        return f"{de_ratio} ✅ (Low Debt)"
    elif 1 <= de_ratio < 2:
        return f"{de_ratio} 🟡 (Moderate)"
    else: # de_ratio is 2 or higher
        return f"{de_ratio} 🔴 (High Risk)"

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
        }
        return summary, None
    except Exception as e:
        return None, f"Error processing stock: **{ticker_symbol.upper()}** - {e}"



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
    elif metric_name in ["Debt to Equity"]:
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
def plot_historical_price(ticker_symbol, company_name, period):
    full_ticker = ticker_symbol + ".NS"
    hist_price = yf.Ticker(full_ticker).history(period=period)

    if hist_price.empty:
        st.warning(f"No price data for {company_name}")
        return

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=hist_price.index, y=hist_price['Close'], mode='lines', name='Close Price'))

    fig.update_layout(
        title=f'{company_name} Historical Price - {period}',
        xaxis_title='Date',
        yaxis_title='Close Price (INR)',
        hovermode="x unified",
        yaxis=dict(
            autorange=True, # Ensure auto-ranging is on
            rangemode='normal' # Crucial change: calculate range based only on data values
        )
    )
    st.plotly_chart(fig, use_container_width=True)
def plot_financial_chart(df, y_column, title, y_axis_title, chart_type='line'):
    if df.empty or y_column not in df.columns or df[y_column].isnull().all():
        st.warning(f"No {y_column} data available for this stock.")
        return

    fig = go.Figure()
    
    if chart_type == 'line':
        fig.add_trace(go.Scatter(x=df.index, y=df[y_column], mode='lines+markers', name=y_column))
    elif chart_type == 'bar':
        fig.add_trace(go.Bar(x=df.index, y=df[y_column], name=y_column))
    
    fig.update_layout(
        title=title,
        xaxis_title='Year',
        yaxis_title=y_axis_title,
        hovermode="x unified",
        yaxis=dict(
            autorange=True, # Ensure auto-ranging is on
            rangemode='normal' # Crucial change: calculate range based only on data values
        )
    )
    st.plotly_chart(fig, use_container_width=True)
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
            st.dataframe(comparison_data)
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
            st.session_state["selected_symbol"] = selected_symbol
            st.session_state["compare_symbol"] = compare_symbol
            with col1_price:
                # Call the new plotting function
                company_name1 = stock1_raw_summary.get('Company Name', selected_symbol.upper()) if stock1_raw_summary else selected_symbol.upper()
                plot_historical_price(selected_symbol, company_name1, compare_chart_period)

            with col2_price:
                # Call the new plotting function
                company_name2 = stock2_raw_summary.get('Company Name', compare_symbol.upper()) if stock2_raw_summary else compare_symbol.upper()
                plot_historical_price(compare_symbol, company_name2, compare_chart_period)



            # --- Historical Profit After Tax (PAT) Chart Comparison ---
            st.markdown("##### 📊 Historical Profit After Tax (PAT in ₹ Crores)")
            col1_pat, col2_pat = st.columns(2)
            with col1_pat:
                try:
                    ticker=yf.Ticker(selected_symbol + ".NS")
                    fin=ticker.financials.T
                    fin.index=pd.to_datetime(fin.index)
                    fin.index=fin.index.year
                    fin = fin.apply(pd.to_numeric, errors="coerce")  # Convert all to numeric
                    financials1 = fin
                    annual_financials1 = financials1.reset_index().set_index('periodType').loc['ANNUAL'].sort_index() if 'periodType' in financials1.index.names else financials1.sort_index()
                    if not annual_financials1.empty and "Net Income" in annual_financials1.columns:
                        pat_df1 = annual_financials1[["Net Income"]].copy().dropna()
                         
                        pat_df1["PAT"] = (pat_df1["Net Income"] / 1e7).round(2) # Convert and round
                        st.line_chart(pat_df1[["PAT"]])
                    else:
                        st.warning("No PAT data ")
                except Exception as e:
                    st.warning(f"Could not retrieve PAT data . Error: {e}")

            with col2_pat:
                try:
                    ticker_2=yf.Ticker(compare_symbol + ".NS")
                    fin_2=ticker_2.financials.T
                    fin_2.index=pd.to_datetime(fin_2.index)
                    fin_2.index=fin_2.index.year
                    fin_2 = fin_2.apply(pd.to_numeric, errors="coerce")
                     
                    financials2 = fin_2
                    annual_financials2 = financials2.reset_index().set_index('periodType').loc['ANNUAL'].sort_index() if 'periodType' in financials2.index.names else financials2.sort_index()
                    if not annual_financials2.empty and "Net Income" in annual_financials2.columns:
                        pat_df2 = annual_financials2[["Net Income"]].copy().dropna()
                        
                        pat_df2["PAT"] = (pat_df2["Net Income"] / 1e7).round(2)
                        st.line_chart(pat_df2[["PAT"]])
                    else:
                        st.warning("No PAT data ")
                except Exception as e:
                    st.warning(f"Could not retrieve PAT data . Error: {e}")

            # --- Historical Revenue Chart Comparison ---
            st.markdown("##### 📈 Historical Revenue (₹ in Crores)")
            col1_rev, col2_rev = st.columns(2)
            with col1_rev:
                try:
                    ticker=yf.Ticker(selected_symbol + ".NS")
                    fin=ticker.financials.T
                    fin.index = pd.to_datetime(fin.index)
                    fin.index=fin.index.year
                    fin = fin.apply(pd.to_numeric, errors="coerce")
                    financials1 = fin
                    annual_financials1 = financials1.reset_index().set_index('periodType').loc['ANNUAL'].sort_index() if 'periodType' in financials1.index.names else financials1.sort_index()
                    if not annual_financials1.empty and "Total Revenue" in annual_financials1.columns:
                        revenue_df1 = annual_financials1[["Total Revenue"]].copy().dropna()
                        
                        revenue_df1["Total Revenue"] = (revenue_df1["Total Revenue"] / 1e7).round(2)
                        st.bar_chart(revenue_df1[["Total Revenue"]])
                    else:
                        st.warning("No Revenue data ")
                except Exception as e:
                    st.warning(f"Could not retrieve revenue data. Error: {e}")

            with col2_rev:
                try:
                    ticker_2=yf.Ticker(compare_symbol + ".NS")
                    fin_2=ticker_2.financials.T
                    fin_2.index=pd.to_datetime(fin_2.index)
                    fin_2.index=fin_2.index.year
                    fin_2 = fin_2.apply(pd.to_numeric, errors="coerce")
                    financials2 = fin_2
                    annual_financials2 = financials2.reset_index().set_index('periodType').loc['ANNUAL'].sort_index() if 'periodType' in financials2.index.names else financials2.sort_index()
                    if not annual_financials2.empty and "Total Revenue" in annual_financials2.columns:
                        revenue_df2 = annual_financials2[["Total Revenue"]].copy().dropna()
                       
                        revenue_df2["Total Revenue"] = (revenue_df2["Total Revenue"] / 1e7).round(2)
                        st.bar_chart(revenue_df2[["Total Revenue"]])
                    else:
                        st.warning("No Revenue data ")
                except Exception as e:
                    st.warning(f"Could not retrieve revenue data . Error: {e}")

            # --- Historical Free Cash Flow (FCF) Chart Comparison ---
            st.markdown("##### 💰 Historical Free Cash Flow (₹ in Crores)")
            col1_fcf, col2_fcf = st.columns(2)
            with col1_fcf:
                try:
                    cf1 = yf.Ticker(selected_symbol + ".NS").cashflow.T
                    cf1.index = pd.to_datetime(cf1.index).year.astype(int)
                    cf1 = cf1.apply(pd.to_numeric, errors="coerce").dropna(how="all")
                    cash_flow_statement1 = cf1
                    annual_cash_flow1 = cash_flow_statement1.reset_index().set_index('periodType').loc['ANNUAL'].sort_index() if 'periodType' in cash_flow_statement1.index.names else cash_flow_statement1.sort_index()

                    if not annual_cash_flow1.empty and 'Free Cash Flow' in annual_cash_flow1.columns:
                        fcf_df1 = annual_cash_flow1[['Free Cash Flow']].copy()
                        
                        fcf_df1['Free Cash Flow (₹ Cr)'] = (fcf_df1['Free Cash Flow'] / 1e7).round(2)
                        st.bar_chart(fcf_df1[['Free Cash Flow (₹ Cr)']])
                    else:
                        st.warning("No FCF data ")
                except Exception as e:
                    st.warning(f"Could not retrieve FCF data . Error: {e}")

            with col2_fcf:
                try:
                    cf2 = yf.Ticker(compare_symbol + ".NS").cashflow.T
                    cf2.index = pd.to_datetime(cf2.index).year.astype(int)
                    cf2 = cf2.apply(pd.to_numeric, errors="coerce").dropna(how="all")
                    cash_flow_statement2 = cf2
                    annual_cash_flow2 = cash_flow_statement2.reset_index().set_index('periodType').loc['ANNUAL'].sort_index() if 'periodType' in cash_flow_statement2.index.names else cash_flow_statement2.sort_index()

                    if not annual_cash_flow2.empty and 'Free Cash Flow' in annual_cash_flow2.columns:
                        fcf_df2 = annual_cash_flow2[['Free Cash Flow']].copy()
                    
                        fcf_df2['Free Cash Flow (₹ Cr)'] = (fcf_df2['Free Cash Flow'] / 1e7).round(2)
                        st.bar_chart(fcf_df2[['Free Cash Flow (₹ Cr)']])
                    else:
                        st.warning("No FCF data ")
                except Exception as e:
                    st.warning(f"Could not retrieve FCF data . Error: {e}")

        elif stock1_raw_summary: # Only primary stock available, in compare mode but second not selected/found
            if compare_user_input and not compare_symbol:
                 st.warning("Please select a valid second stock from the dropdown or try a different search term.")
            else:
                st.info("Please search and select a second stock to enable full comparison view. Displaying primary stock details below.")
            
            # Fallback to display single stock if only one is found in compare mode
            st.subheader(f"📋 Fundamentals Summary for {stock1_raw_summary.get('Company Name', selected_symbol.upper())}")
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

            # Chart Period Selector for Single Stock Mode
            single_chart_period = st.selectbox(
                "Select period for historical chart:",
                ["1mo", "3mo", "6mo", "1y", "3y", "5y", "max"],
                index=3, # Default to 1 year
                key="single_chart_period"
            )

            # Call the new plotting function
            company_name = stock_summary.get('Company Name', selected_symbol.upper())
            plot_historical_price(selected_symbol, company_name, single_chart_period)


            st.markdown("##### 📊 Historical Profit After Tax (PAT in ₹ Crores)")
            try:
                ticker=yf.Ticker(selected_symbol + ".NS")
                fin=ticker.financials.T
                fin.index=pd.to_datetime(fin.index)
                fin.index=fin.index.year
                fin = fin.apply(pd.to_numeric, errors="coerce")  # Convert all to numeric  
                financials = fin
                annual_financials = financials.reset_index().set_index('periodType').loc['ANNUAL'].sort_index() if 'periodType' in financials.index.names else financials.sort_index()
                if not annual_financials.empty and "Net Income" in annual_financials.columns:
                    pat_df = annual_financials[["Net Income"]].copy().dropna()
                   
                    pat_df["PAT"] = (pat_df["Net Income"] / 1e7).round(2)
                    st.line_chart(pat_df[["PAT"]])
                else:
                    st.warning("No PAT data ")
            except Exception as e:
                st.warning(f"Could not retrieve PAT data . Error: {e}")


            st.subheader("📈 Historical Revenue (₹ in Crores)")
            try:
                ticker=yf.Ticker(selected_symbol + ".NS")
                fin=ticker.financials.T
                fin.index=pd.to_datetime(fin.index)
                fin.index=fin.index.year
                fin = fin.apply(pd.to_numeric, errors="coerce")  # Convert all to numeric
                financials = fin
                # Ensure we are consistently using 'ANNUAL' data if available
                annual_financials = financials.reset_index().set_index('periodType').loc['ANNUAL'].sort_index() if 'periodType' in financials.index.names else financials.sort_index()

                if not annual_financials.empty and "Total Revenue" in annual_financials.columns:
                    revenue_df = annual_financials[["Total Revenue"]].copy().dropna()
                    
                    revenue_df["Total Revenue"] = (revenue_df["Total Revenue"] / 1e7).round(2)
                    st.bar_chart(revenue_df[["Total Revenue"]]) # No need to rename columns in single chart as it takes index name
                else:
                    st.warning("Total Revenue data not available in financials.")
            except Exception as e:
                st.warning(f"Could not retrieve historical revenue data. Error: {e}")


            st.subheader("💰 Historical Free Cash Flow (₹ in Crores)")
            try:
                cf1 = yf.Ticker(selected_symbol + ".NS").cashflow.T
                cf1.index = pd.to_datetime(cf1.index).year.astype(int)
                cf1 = cf1.apply(pd.to_numeric, errors="coerce").dropna(how="all")
                cash_flow_statement = cf1
                annual_cash_flow = cash_flow_statement.reset_index().set_index('periodType').loc['ANNUAL'].sort_index() if 'periodType' in cash_flow_statement.index.names else cash_flow_statement.sort_index()

                if not annual_cash_flow.empty and 'Free Cash Flow' in annual_cash_flow.columns:
                    fcf_df = annual_cash_flow[['Free Cash Flow']].copy()
                    
                    fcf_df['Free Cash Flow (₹ Cr)'] = (fcf_df['Free Cash Flow'] / 1e7).round(2)
                    st.bar_chart(fcf_df[['Free Cash Flow (₹ Cr)']]) 
                else:
                    st.warning("Free Cash Flow data not available in cash flow statements.")
            except Exception as e:
                st.warning(f"Could not retrieve historical Free Cash Flow data. Error: {e}")
