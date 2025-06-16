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

def load_stock_data():
    try:
        # Changed filename from "nse stocks.csv" to "nse_stocks.csv" for better practice
        df = pd.read_csv("nse stocks.csv") # Ensure this file is present in your app directory
        df["Searchable"] = df["Symbol"] + " - " + df["Company Name"]
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
    if start_value <= 0 or end_value <= 0 or periods == 0:
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
    if de is None:
        return "N/A"

    # Attempt to convert to float, as yfinance can sometimes return non-numeric if data is messy
    try:
        de = float(de)

    except (ValueError, TypeError):
        return "N/A" # Return N/A if it's not a valid number

    # Heuristic: If the debtToEquity value is significantly greater than 2,
    # and it's an Indian stock (where yfinance often gives percentages),
    # assume it's a percentage and convert it to a ratio.
    # A D/E of 200% (2.0) is already quite high. If it's 50 or 100, it's likely a percentage.

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
        info = stock.info # Use .info instead of .get_info() for yfinance 0.2.x+
        
        if not info or "longName" not in info:
            return None, f"⚠️ Could not fetch data for **{ticker_symbol.upper()}**. Please check the symbol."
        
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
        
        hist = stock.history(period="max")
        all_time_high = "N/A"
        percent_from_ath = "N/A"
        ath_change_display = "N/A"
        
        if not hist.empty:
            all_time_high = round(hist["High"].max(), 2)
            if current_price and all_time_high != 0:
                percent_from_ath = round(((current_price - all_time_high) / all_time_high) * 100, 2)
                if percent_from_ath >= 0:
                    ath_change_display = f"{all_time_high} (+{percent_from_ath}%) 🟢"
                else:
                    ath_change_display = f"{all_time_high} ({percent_from_ath}%) 🔻"
        free_cash_flow = 'N/A'
        try:
            # Get annual cash flow statements
            cash_flow_statement = stock.cashflow
            
            # yfinance's cashflow DataFrame has 'Free Cash Flow' directly, which is convenient
            # The most recent data is usually the first column (index 0 or highest date)
            if not cash_flow_statement.empty and 'Free Cash Flow' in cash_flow_statement.index:
                # Get the most recent Free Cash Flow value
                fcf_value = cash_flow_statement.loc['Free Cash Flow'].iloc[0] # .iloc[0] gets the most recent value
                free_cash_flow = fcf_value / 1e7 # Convert from base units (e.g., USD) to Crores, assuming data is in millions/billions. Adjust this conversion factor based on yfinance's actual units for Indian stocks. Often, it's in the base currency, so 1e7 for Crores if it's in Rupees.
            else:
                free_cash_flow = 'N/A - Free Cash Flow data not directly found or cash flow statement empty.'
        except Exception as e:
            free_cash_flow = f'N/A - Error fetching FCF: {e}'
        
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
            #"P/E Ratio": stock_pe,
            "P/E vs Industry": interpret_pe_with_industry(stock_pe, industry_pe),
            #"PEG Ratio": f"{peg} ({peg_msg})" if peg_msg else (peg if peg is not None else "N/A"),
            "EPS": interpret_eps(info.get("trailingEps")),
            "Dividend Yield": interpret_dividend_yield(info.get("dividendYield")),
            "Profit Margin": profit_margin_percent,
            "Free Cash Flow (₹ Cr)":free_cash_flow,
            "ROE": interpret_roe(info.get("returnOnEquity")),
            "Debt to Equity": interpret_de_ratio(info.get("debtToEquity")),
        }
        return summary, None
    except Exception as e:
        return None, f"Error processing stock: **{ticker_symbol.upper()}** - {e}"

# User input for primary stock search
user_input = st.text_input("🔍 Search by symbol or company name for the primary stock:")

selected_symbol = None

if user_input:
    # 1. Try to find a match in the CSV first
    if not nse_df.empty: # Check if nse_df was loaded successfully
        matches = nse_df[nse_df["Searchable"].str.contains(user_input, case=False, na=False)]

        if not matches.empty:
            selected = st.selectbox("Select a company (Primary):", matches["Searchable"].tolist(), key="main_stock_select")
            selected_symbol = selected.split(" - ")[0]
            st.success(f"✅ Primary Stock Selected: **{selected_symbol}.NS** (from CSV)")
        else:
            # 2. If no match in CSV, try to use user_input directly as a symbol
            #    We'll assume it's an Indian stock symbol and append ".NS"
            potential_symbol = user_input.strip().upper() # Convert to uppercase for direct symbol lookup

            # Attempt to get info to confirm it's a valid symbol before setting
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


# Main app logic
if selected_symbol:
    if compare_mode:
        st.subheader("🆚 Compare With Another Stock")

        # --- NEW SEARCH BAR FOR SECOND STOCK ---
        compare_user_input = st.text_input("🔍 Search by symbol or company name for the second stock:")
        compare_symbol = None # Initialize compare_symbol

        if compare_user_input:
            if not nse_df.empty: # Check if nse_df was loaded successfully
                compare_matches = nse_df[nse_df["Searchable"].str.contains(compare_user_input, case=False, na=False)]

                if not compare_matches.empty:
                    compare_selected_full = st.selectbox(
                        "Select a company (Second Stock):",
                        compare_matches["Searchable"].tolist(),
                        key="compare_stock_select"
                    )
                    compare_symbol = compare_selected_full.split(" - ")[0]
                    st.success(f"✅ Second Stock Selected: **{compare_symbol}.NS** (from CSV)")
                else:
                    # Direct symbol lookup for comparison stock
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

        if compare_symbol: # Only try to fetch if a symbol for comparison is actually selected
            stock2_summary, error2 = get_stock_summary(compare_symbol)
            if error2:
                st.error(error2)

        # Display comparison only if both summaries are successfully retrieved
        if stock1_summary and stock2_summary:
            common_keys = list(set(stock1_summary.keys()) & set(stock2_summary.keys()))

            dict1_aligned = {k: stock1_summary[k] for k in common_keys}
            dict2_aligned = {k: stock2_summary[k] for k in common_keys}

            comparison_data = pd.DataFrame({
                stock1_summary.get("Company Name", selected_symbol.upper()): pd.Series(dict1_aligned),
                stock2_summary.get("Company Name", compare_symbol.upper()): pd.Series(dict2_aligned)
            })

            st.subheader("📊 Stock Comparison")
            st.dataframe(comparison_data)

            # --- START CHART COMPARISON ---
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
                        st.line_chart(hist_price1["Close"].round(2).rename(stock1_summary.get('Company Name', selected_symbol.upper())))
                    else:
                        st.warning(f"No price data for {stock1_summary.get('Company Name', selected_symbol.upper())}")
                except Exception as e:
                    st.warning(f"Could not load price chart for {stock1_summary.get('Company Name', selected_symbol.upper())}. Error: {e}")

            with col2_price:
                try:
                    stock2_yf = yf.Ticker(compare_symbol + ".NS")
                    hist_price2 = stock2_yf.history(period=compare_chart_period)
                    if not hist_price2.empty:
                        st.line_chart(hist_price2["Close"].round(2).rename(stock2_summary.get('Company Name', compare_symbol.upper())))
                    else:
                        st.warning(f"No price data for {stock2_summary.get('Company Name', compare_symbol.upper())}")
                except Exception as e:
                    st.warning(f"Could not load price chart for {stock2_summary.get('Company Name', compare_symbol.upper())}. Error: {e}")

            # --- Historical Profit After Tax (PAT) Chart Comparison ---
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
                        st.bar_chart(pat_df1[["PAT"]].round(2).rename(columns={'PAT': stock1_summary.get('Company Name', selected_symbol.upper()) + ' PAT'}))
                    else:
                        st.warning(f"No PAT data for {stock1_summary.get('Company Name', selected_symbol.upper())}")
                except Exception as e:
                    st.warning(f"Could not retrieve PAT data for {stock1_summary.get('Company Name', selected_symbol.upper())}. Error: {e}")

            with col2_pat:
                try:
                    stock2_yf = yf.Ticker(compare_symbol + ".NS")
                    financials2 = stock2_yf.financials
                    if not financials2.empty and "Net Income" in financials2.index:
                        pat_df2 = financials2.loc[["Net Income"]].transpose()
                        pat_df2.index = pat_df2.index.year
                        pat_df2["PAT"] = (pat_df2["Net Income"] / 1e7)
                        st.bar_chart(pat_df2[["PAT"]].round(2).rename(columns={'PAT': stock2_summary.get('Company Name', compare_symbol.upper()) + ' PAT'}))
                    else:
                        st.warning(f"No PAT data for {stock2_summary.get('Company Name', compare_symbol.upper())}")
                except Exception as e:
                    st.warning(f"Could not retrieve PAT data for {stock2_summary.get('Company Name', compare_symbol.upper())}. Error: {e}")

            # --- Historical Revenue Chart Comparison ---
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
                        st.bar_chart(revenue_df1[["Total Revenue"]].round(2).rename(columns={'Total Revenue': stock1_summary.get('Company Name', selected_symbol.upper()) + ' Revenue'}))
                    else:
                        st.warning(f"No Revenue data for {stock1_summary.get('Company Name', selected_symbol.upper())}")
                except Exception as e:
                    st.warning(f"Could not retrieve revenue data for {stock1_summary.get('Company Name', selected_symbol.upper())}. Error: {e}")

            with col2_rev:
                try:
                    stock2_yf = yf.Ticker(compare_symbol + ".NS")
                    financials2 = stock2_yf.financials
                    if not financials2.empty and "Total Revenue" in financials2.index:
                        revenue_df2 = financials2.loc[["Total Revenue"]].transpose()
                        revenue_df2.index = revenue_df2.index.year
                        revenue_df2["Total Revenue"] = (revenue_df2["Total Revenue"] / 1e7)
                        st.bar_chart(revenue_df2[["Total Revenue"]].round(2).rename(columns={'Total Revenue': stock2_summary.get('Company Name', compare_symbol.upper()) + ' Revenue'}))
                    else:
                        st.warning(f"No Revenue data for {stock2_summary.get('Company Name', compare_symbol.upper())}")
                except Exception as e:
                    st.warning(f"Could not retrieve revenue data for {stock2_summary.get('Company Name', compare_symbol.upper())}. Error: {e}")

            # --- Historical Free Cash Flow (FCF) Chart Comparison ---
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
                        st.bar_chart(fcf_df1[['Free Cash Flow (₹ Cr)']].round(2).rename(columns={'Free Cash Flow (₹ Cr)': stock1_summary.get('Company Name', selected_symbol.upper()) + ' FCF'}))
                    else:
                        st.warning(f"No FCF data for {stock1_summary.get('Company Name', selected_symbol.upper())}")
                except Exception as e:
                    st.warning(f"Could not retrieve FCF data for {stock1_summary.get('Company Name', selected_symbol.upper())}. Error: {e}")

            with col2_fcf:
                try:
                    stock2_yf = yf.Ticker(compare_symbol + ".NS")
                    cash_flow_statement2 = stock2_yf.cashflow
                    if not cash_flow_statement2.empty and 'Free Cash Flow' in cash_flow_statement2.index:
                        fcf_df2 = cash_flow_statement2.loc[['Free Cash Flow']].transpose()
                        fcf_df2.index = fcf_df2.index.year
                        fcf_df2['Free Cash Flow (₹ Cr)'] = fcf_df2['Free Cash Flow'] / 1e7
                        st.bar_chart(fcf_df2[['Free Cash Flow (₹ Cr)']].round(2).rename(columns={'Free Cash Flow (₹ Cr)': stock2_summary.get('Company Name', compare_symbol.upper()) + ' FCF'}))
                    else:
                        st.warning(f"No FCF data for {stock2_summary.get('Company Name', compare_symbol.upper())}")
                except Exception as e:
                    st.warning(f"Could not retrieve FCF data for {stock2_summary.get('Company Name', compare_symbol.upper())}. Error: {e}")
            # --- END CHART COMPARISON ---

        elif stock1_summary: # Only primary stock available
            if compare_user_input and not compare_symbol: # User typed something but no valid selection
                 st.warning("Please select a valid second stock from the dropdown.")
            else:
                st.warning("Please search and select a second stock to compare for full comparison view.")
            st.subheader(f"📋 Fundamentals Summary for {stock1_summary.get('Company Name', selected_symbol.upper())}")
            df = pd.DataFrame(stock1_summary.items(), columns=["Metric", "Value"])
            st.dataframe(df.set_index("Metric"))
        else:
            st.warning("No primary stock selected. Please select a primary stock to begin comparison or single view.")

    else: # Not in compare mode (single stock view)
        stock_summary, error = get_stock_summary(selected_symbol)

        if error:
            st.error(error)
        elif stock_summary:
            df = pd.DataFrame(stock_summary.items(), columns=["Metric", "Value"])

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
