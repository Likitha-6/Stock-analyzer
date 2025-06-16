import streamlit as st
import yfinance as yf
import pandas as pd
import requests

# Streamlit setup
st.set_page_config(page_title="Indian Stock Analyzer", page_icon="📊")
st.title("📈 Indian Stock Analyzer (Fundamentals)")
st.markdown("---")
compare_mode = st.checkbox("🔄 Compare stocks")
# Load dynamic search CSV
nse_df = pd.read_csv("nse stocks.csv")  # Ensure this file is present in the app directory
nse_df.dropna(subset=["Company Name", "Symbol"], inplace=True)
company_names = nse_df["Company Name"].tolist()
company_names = sorted(nse_df["Company Name"].tolist())
selected_company = st.selectbox("Search for a company", company_names)
ticker_input = nse_df[nse_df["Company Name"] == selected_company]["Symbol"].values[0]
ticker = ticker_input.upper().strip() + ".NS"
st.caption(f"Selected Ticker: `{ticker}`")


#st.markdown("Enter an NSE stock ticker (e.g., RELIANCE, TCS, SBIN, INFY):")

#ticker_input = st.text_input("Ticker Symbol", "RELIANCE")
#ticker = ticker_input.upper().strip() + ".NS"
#NEWS_API_KEY = "9802d49649194f36b4577221a7bd499c"  # Replace with your actual API key



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

    return f"{pe} vs {industry_pe} ({interpretation})"

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
        eps_list = (earnings["Earnings"] / 1e9).tolist()  # Convert to billions for easier scale
        eps_old = eps_list[0]
        eps_new = eps_list[-1]
        cagr = calculate_cagr(eps_old, eps_new, len(eps_list) - 1)

        if cagr and pe_ratio:
            peg = pe_ratio / (cagr * 100)  # Convert CAGR to %
            return round(peg, 2), None
        else:
            return None, "CAGR or PE unavailable"

    except Exception as e:
        return None, f"Error: {e}"


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
    elif de < 1:
        return f"{de} ✅ (Low Debt)"
    elif de > 1 and de <2:
        return f"{de} 🟡 (Moderate)"
    else:
        return f"{de} 🔴 (High Risk)"
def get_stock_summary(ticker_input):
    ticker = ticker_input.upper().strip() + ".NS"
    stock = yf.Ticker(ticker)
    info = stock.get_info()
    

    if not info or "longName" not in info:
        return None, f"⚠️ Could not fetch data for {ticker_input.upper()}. Please check the symbol."

    sector = info.get("sector")
    industry_pe = INDUSTRY_PE.get(sector)
    stock_pe = info.get("trailingPE")
    eps_growth = info.get("earningsQuarterlyGrowth")  # or use another suitable key
    peg, peg_msg = get_eps_cagr_based_peg(ticker_input)

    current_price = info.get("currentPrice")

    try:
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
            #"PEG Ratio": f"{peg} ({peg_msg})" if peg_msg else peg,
            "EPS": interpret_eps(info.get("trailingEps")),
            "Dividend Yield": interpret_dividend_yield(info.get("dividendYield")),
            "Profit Margin": profit_margin_percent,
            "ROE": interpret_roe(info.get("returnOnEquity")),
            "Debt/Equity": interpret_de_ratio(info.get("debtToEquity")),
            #"Revenue": revenue_billion,
            #"Net Income": net_income_billion,
        }
        return summary, None
    except Exception as e:
        return None, f"Error processing stock: {ticker_input.upper()} - {e}"


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
            # Create a DataFrame for comparison
            comparison_data = pd.DataFrame({
                ticker_input.upper(): stock1_summary,
                compare_input.upper() if stock2_summary else "": stock2_summary or {}
            })
    
            st.subheader("📊 Stock Comparison")
            st.dataframe(comparison_data)
    else:
            
        try:
            stock = yf.Ticker(ticker)
            info = stock.get_info()
            sector = info.get("sector")
            industry_pe = INDUSTRY_PE.get(sector)
            stock_pe = info.get("trailingPE")
            current_price = info.get("currentPrice")
            peg,peg_msg = get_eps_cagr_based_peg(ticker)
    
    
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
            if all_time_high != "N/A" and current_price:
                percent_from_ath = round(((current_price - all_time_high) / all_time_high) * 100, 2)
                if percent_from_ath >= 0:
                    ath_change_display = f"{all_time_high} (+{percent_from_ath}%) 🟢"
                else:
                    ath_change_display = f"{all_time_high} ({percent_from_ath}%) 🔻"
            else:
                ath_change_display = "N/A"
    
    
            revenue = info.get("totalRevenue")
            net_income = info.get("netIncomeToCommon")
            revenue_billion = f"{round(revenue / 1e9, 2)} B" if revenue else "N/A"
            net_income_billion = f"{round(net_income / 1e9, 2)} B" if net_income else "N/A"
            #industry_pe = INDUSTRY_PE.get(sector)
    
    
            # Convert profit margin to % format
            profit_margin = info.get("profitMargins")
            if profit_margin is None:
                profit_margin_percent = "N/A"
            elif profit_margin < 0:
                profit_margin_percent = f"{round(profit_margin * 100, 2)}% ❌ (Loss-Making)"
            else:
                profit_margin_percent = f"{round(profit_margin * 100, 2)}%"
    
            data = {
                "Company Name": info.get("longName"),
                "Sector": info.get("sector"),
                "Current Price (₹)": info.get("currentPrice"),
                "All-Time High (₹)": ath_change_display,
                "Market Cap (Billion ₹)": market_cap_display,
                "P/E Ratio": info.get("trailingPE"),
                "P/E vs Industry": interpret_pe_with_industry(stock_pe, industry_pe),
                #"PEG Ratio": f"{peg} ({peg_msg})" if peg_msg else peg,


                #"Industry_PE":industry_pe,
                "EPS": interpret_eps(info.get("trailingEps")),
    
                "Dividend Yield": interpret_dividend_yield(info.get("dividendYield")),
                #"Revenue (TTM)": revenue_billion,
                #"Net Income (TTM)": net_income_billion,
                "Profit Margin": profit_margin_percent,
                "Return on Equity (ROE)": interpret_roe(info.get("returnOnEquity")),
                "Debt to Equity": interpret_de_ratio(info.get("debtToEquity")),
            }
    
            df = pd.DataFrame(data.items(), columns=["Metric", "Value"])

            st.subheader("📋 Stock Fundamentals Summary")
            st.dataframe(df.set_index("Metric"))
    
    
           
            
            # RIGHT: News Section
            #
            #st.dataframe(df.set_index("Metric"))
    
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
        

