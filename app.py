import streamlit as st
import yfinance as yf
import pandas as pd
import requests

# Streamlit setup
st.set_page_config(page_title="Indian Stock Analyzer", page_icon="📊")
st.title("📈 Indian Stock Analyzer (Fundamentals)")

# Load NSE tickers (Nifty50 example)
@st.cache_data
def load_nse_tickers():
    url = "https://raw.githubusercontent.com/rohanrao91/stock_market_india/main/data/nifty50.csv"
    df = pd.read_csv(url)
    df["display"] = df["Company"] + " (" + df["Symbol"] + ")"
    return df

nse_df = load_nse_tickers()
company_display = st.selectbox(
    "Select a company",
    nse_df["display"].tolist(),
    index=0
)
selected_symbol = nse_df[nse_df["display"] == company_display]["Symbol"].values[0]
ticker = selected_symbol + ".NS"
NEWS_API_KEY = "9802d49649194f36b4577221a7bd499c"  # Replace with your actual API key

# Fetch stock info
stock = yf.Ticker(ticker)
info = stock.get_info()

# Display Logo and Summary
st.markdown("---")
logo_url = info.get("logo_url")
long_name = info.get("longName", "N/A")
summary = info.get("longBusinessSummary", "Summary not available.")

if logo_url:
    col1, col2 = st.columns([1, 4])
    with col1:
        st.image(logo_url, width=80)
    with col2:
        st.subheader(long_name)
        st.caption(summary)
else:
    st.subheader(long_name)
    st.caption(summary)
st.markdown("---")

INDUSTRY_PE = {
    "Technology": 25.4, "Energy": 13.1, "Financial Services": 15.2,
    "Consumer Defensive": 28.3, "Healthcare": 24.5, "Utilities": 10.9,
    "Industrials": 20.7, "Consumer Cyclical": 22.1, "Basic Materials": 14.6,
    "Communication Services": 18.4, "Real Estate": 16.0,
}

def get_market_cap_category(market_cap_inr):
    if market_cap_inr >= 2e12: return "Mega Cap", "Strong, stable"
    elif market_cap_inr >= 5e11: return "Large Cap", "Strong, stable"
    elif market_cap_inr >= 1e11: return "Mid Cap", "Growing, moderate risk"
    elif market_cap_inr >= 1e10: return "Small Cap", "Emerging, higher risk"
    else: return "Micro Cap", "Very small, high risk"

def get_category_icon(category):
    return {
        "Mega Cap": "✅", "Large Cap": "✅", "Mid Cap": "🟡",
        "Small Cap": "🟠", "Micro Cap": "🔴"
    }.get(category, "")

def interpret_eps(eps):
    try: eps = float(eps)
    except: return "N/A"
    if eps < 0: return f"{round(eps, 2)} 🔴 (Negative)"
    elif eps < 10: return f"{round(eps, 2)} 🟠 (Low)"
    else: return f"{round(eps, 2)} ✅"

def interpret_pe_with_industry(pe, industry_pe):
    if pe is None or industry_pe is None: return "N/A"
    diff = pe - industry_pe
    if diff > 10: return f"{pe} vs {industry_pe} (🔺 Overvalued)"
    elif diff > 2: return f"{pe} vs {industry_pe} (🟠 Slightly Overvalued)"
    elif diff < -2: return f"{pe} vs {industry_pe} (✅ Undervalued)"
    else: return f"{pe} vs {industry_pe} (✅ Fairly Priced)"

def interpret_dividend_yield(dy):
    if dy is None or dy == 0: return f"0% 🔴 (No dividends)"
    dy_percent = round(dy * 1, 2)
    if dy < 1: return f"{dy_percent}% 🟠 (Low)"
    elif dy < 3: return f"{dy_percent}% ✅ (Moderate)"
    else: return f"{dy_percent}% ✅ (High)"

def interpret_roe(roe):
    if roe is None: return "N/A"
    roe_percent = round(roe * 100, 2)
    if roe_percent < 10: return f"{roe_percent}% 🟠 (Low)"
    elif roe_percent < 20: return f"{roe_percent}% 🟡 (Moderate)"
    else: return f"{roe_percent}% ✅ (High)"

def interpret_de_ratio(de):
    if de is None: return "N/A"
    de = round(de / 100, 2)
    if de < 1: return f"{de} ✅ (Low Debt)"
    elif de < 2: return f"{de} 🟡 (Moderate)"
    else: return f"{de} 🔴 (High Risk)"

# Stock fundamentals
sector = info.get("sector")
industry_pe = INDUSTRY_PE.get(sector)
stock_pe = info.get("trailingPE")
current_price = info.get("currentPrice")

market_cap = info.get("marketCap")
if market_cap:
    market_cap_billion = round(market_cap / 1e9, 2)
    cap_category, cap_meaning = get_market_cap_category(market_cap)
    cap_icon = get_category_icon(cap_category)
    market_cap_display = f"{market_cap_billion} B ({cap_icon} {cap_category} – {cap_meaning})"
else:
    market_cap_display = "N/A"

# All-Time High
hist = stock.history(period="max")
if not hist.empty:
    all_time_high = round(hist["High"].max(), 2)
else:
    all_time_high = "N/A"

if all_time_high != "N/A" and current_price:
    percent_from_ath = round(((current_price - all_time_high) / all_time_high) * 100, 2)
    ath_change_display = f"{all_time_high} ({percent_from_ath:+}%) {'🟢' if percent_from_ath >= 0 else '🔻'}"
else:
    ath_change_display = "N/A"

revenue = info.get("totalRevenue")
net_income = info.get("netIncomeToCommon")
revenue_billion = f"{round(revenue / 1e9, 2)} B" if revenue else "N/A"
net_income_billion = f"{round(net_income / 1e9, 2)} B" if net_income else "N/A"

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
    "EPS": interpret_eps(info.get("trailingEps")),
    "Dividend Yield": interpret_dividend_yield(info.get("dividendYield")),
    "Profit Margin": profit_margin_percent,
    "Return on Equity (ROE)": interpret_roe(info.get("returnOnEquity")),
    "Debt to Equity": interpret_de_ratio(info.get("debtToEquity")),
}

df = pd.DataFrame(data.items(), columns=["Metric", "Value"])
col1, col2 = st.columns([2, 1])
with col1:
    st.dataframe(df.set_index("Metric"))
with col2:
    st.subheader("📰 Latest News")
    query = info.get("longName", selected_symbol)
    news_url = f"https://newsapi.org/v2/everything?q={query}&language=en&sortBy=publishedAt&pageSize=5&apiKey={NEWS_API_KEY}"
    try:
        response = requests.get(news_url)
        if response.status_code == 200:
            articles = response.json().get("articles", [])
            if not articles:
                st.write("No news found.")
            for article in articles:
                st.markdown(f"**[{article['title']}]({article['url']})**")
                st.caption(f"{article['source']['name']} • {article['publishedAt'][:10]}")
        else:
            st.warning("News API limit reached or failed to fetch news.")
    except:
        st.warning("Could not load news articles.")

# 📉 Stock Price Chart
st.subheader("📉 Historical Stock Price Chart")
try:
    period = st.selectbox("Select period for price chart:", ["1mo", "3mo", "6mo", "1y", "5y", "max"], index=4)
    hist_price = stock.history(period=period)
    if not hist_price.empty:
        st.line_chart(hist_price["Close"].round(2))
    else:
        st.warning("No historical stock data available.")
except Exception as e:
    st.warning(f"Could not load stock price chart. Error: {e}")

# 📊 PAT (Profit After Tax)
st.subheader("📊 Historical Profit After Tax (PAT in ₹ Crores)")
try:
    financials = stock.financials
    financials = financials.loc[["Net Income"]].transpose()
    financials.index = financials.index.year
    financials["PAT"] = (financials["Net Income"] / 1e7)
    st.line_chart(financials[["PAT"]].round(2))
except:
    st.warning("Could not retrieve PAT data.")

# 📈 Revenue
st.subheader("📈 Historical Revenue (₹ in Crores)")
try:
    financials = stock.financials
    financials = financials.loc[["Total Revenue"]].transpose()
    financials.index = financials.index.year
    financials["Total Revenue"] = (financials["Total Revenue"] / 1e7)
    st.bar_chart(financials[["Total Revenue"]].round(2))
except:
    st.warning("Could not retrieve revenue data.")
