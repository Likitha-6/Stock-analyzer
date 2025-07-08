import streamlit as st
import yfinance as yf
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from scipy.signal import argrelextrema
from indicators import compute_rsi  # make sure this function exists and returns a "RSI" column

st.set_page_config(page_title=" Index Analysis", layout="wide")

# ─────────────────────────────────────
# Index Selector
# ─────────────────────────────────────
index_options = {
    "NIFTY 50": "^NSEI",
    "SENSEX": "^BSESN",
    "NIFTY Bank": "^NSEBANK",
    "NIFTY IT": "^CNXIT",
    "NIFTY FMCG": "^CNXFMCG",
    "NIFTY Auto": "^CNXAUTO",
    "NIFTY Pharma": "^CNXPHARMA",
}
selected_index = st.selectbox(" Select Index", list(index_options.keys()))
index_symbol = index_options[selected_index]


# ─────────────────────────────────────
# Load Data and Compute Indicators
# ─────────────────────────────────────
df = yf.Ticker(index_symbol).history(period="60d", interval="1d").reset_index()
price = df["Close"].iloc[-1]
# Ensure we have enough data
df["Date"] = pd.to_datetime(df["Date"])
df.set_index("Date", inplace=True)






# Compute indicators
df["EMA_9"] = df["Close"].ewm(span=9, adjust=False).mean()
df["EMA_15"] = df["Close"].ewm(span=15, adjust=False).mean()
df["RSI"] = compute_rsi(df)
df["Prev_1d"]   = df["Close"].shift(1)
df["Prev_30d"]  = df["Close"].shift(30)
df["Prev_250d"] = df["Close"].shift(250)

price     = df["Close"].iloc[-1]
day_ago   = df["Prev_1d"].iloc[-1]
month_ago = df["Prev_30d"].iloc[-1]
year_ago  = df["Prev_250d"].iloc[-1]

def pct_change(cur, prev):
    return (cur - prev) / prev * 100 if pd.notna(prev) else None

day_change   = pct_change(price, day_ago)
month_change = pct_change(price, month_ago)
year_change  = pct_change(price, year_ago)
df.reset_index(inplace=True)
def fmt_pct(val):
    return f"{val:+.2f} %" if val is not None else "—"

# ────────────────────────────
# 📊 Snapshot header
# ────────────────────────────
# ensure RSI exists
if "RSI" not in df.columns:
    df["RSI"] = compute_rsi(df)

latest_rsi = float(df["RSI"].iloc[-1])
prev_rsi   = float(df["RSI"].iloc[-2]) if len(df) > 1 else latest_rsi
rsi_arrow  = "↑" if latest_rsi >= prev_rsi else "↓"




c_price, c_day, c_month, c_rsi, c_sr = st.columns([2, 2, 2, 2, 3])

c_price.metric("💰 Price",  f"₹{price:,.2f}")
c_day.metric(  "24 h %",      fmt_pct(day_change),   delta_color="inverse")
c_month.metric("30 d %",      fmt_pct(month_change), delta_color="inverse")
c_rsi.metric(  "RSI (14)",    f"{latest_rsi:.1f} {rsi_arrow}")





# ─────────────────────────────────────
# Nearest Support & Resistance
# ─────────────────────────────────────
def get_nearest_support_resistance(df, price):
    df = df.copy()
    df["min"] = df["Close"].iloc[argrelextrema(df["Close"].values, np.less_equal, order=5)[0]]
    df["max"] = df["Close"].iloc[argrelextrema(df["Close"].values, np.greater_equal, order=5)[0]]
    supports = df["min"].dropna()
    resistances = df["max"].dropna()
    nearest_support = supports[supports < price].max() if not supports.empty else None
    nearest_resistance = resistances[resistances > price].min() if not resistances.empty else None
    return nearest_support, nearest_resistance

support, resistance = get_nearest_support_resistance(df, price)

# ─────────────────────────────────────
# Chart Rendering
# ─────────────────────────────────────
st.subheader(f" {selected_index} – Candlestick Chart with EMA 9, EMA 15")

fig = go.Figure()

fig.add_trace(go.Candlestick(
    x=df["Date"],
    open=df["Open"],
    high=df["High"],
    low=df["Low"],
    close=df["Close"],
    increasing_line_color="green",
    decreasing_line_color="#e74c3c",
    name="Price"
))
fig.add_trace(go.Scatter(x=df["Date"], y=df["EMA_9"], mode="lines", name="EMA 9", line=dict(color="orange")))
fig.add_trace(go.Scatter(x=df["Date"], y=df["EMA_15"], mode="lines", name="EMA 15", line=dict(color="cyan")))

if support:
    fig.add_hline(y=support, line_color="green", line_dash="dot", opacity=0.7,
                  annotation_text=f"Support: {support:.2f}", annotation_position="bottom right")
if resistance:
    fig.add_hline(y=resistance, line_color="red", line_dash="dot", opacity=0.7,
                  annotation_text=f"Resistance: {resistance:.2f}", annotation_position="top right")
fig.update_xaxes(
    rangebreaks=[dict(bounds=["sat", "sun"])]  # hide Saturdays & Sundays
)

fig.update_layout(
    title=f"{selected_index} – Nearest Support & Resistance",
    xaxis_title="Date",
    yaxis_title="Price",
    template="plotly_dark",
    xaxis_rangeslider_visible=False,
    dragmode="pan",
    height=600,
    xaxis=dict(showgrid=False),
    yaxis=dict(showgrid=False)
)

st.plotly_chart(fig, use_container_width=True, config={"scrollZoom": True})



# ─────────────────────────────────────
# Technical Insights
# ─────────────────────────────────────
st.subheader("Insights")

latest_ema9 = df["EMA_9"].iloc[-1]
latest_ema15 = df["EMA_15"].iloc[-1]
ema15_5days_ago = df["EMA_15"].iloc[-5]
latest_rsi = df["RSI"].iloc[-1]

if latest_ema9 > latest_ema15:
    st.success("✅ Short-term momentum is **bullish** (EMA 9 > EMA 15).")
else:
    st.error("❌ Short-term momentum is **bearish** (EMA 9 < EMA 15).")

if latest_ema15 > ema15_5days_ago:
    st.success(" EMA 15 is sloping upward — trend strengthening.")
else:
    st.warning(" EMA 15 is sloping downward — short-term weakening.")

if latest_rsi > 70:
    st.warning("⚠️ RSI > 70: **Overbought** — potential pullback.")
elif latest_rsi < 30:
    st.success("RSI < 30: **Oversold** — potential rebound opportunity.")
else:
    st.info("⚖️ RSI is in **neutral zone**.")

# ─────────────────────────────────────
# Final Recommendation
# ─────────────────────────────────────
#st.subheader(" Final Recommendation")

buy_signal = latest_ema9 > latest_ema15 and latest_rsi < 30 and latest_ema15 < ema15_5days_ago
wait_signal = latest_ema9 > latest_ema15 and 30 <= latest_rsi <= 60
avoid_signal = latest_ema9 < latest_ema15 and latest_ema15 < ema15_5days_ago

if buy_signal:
    st.success("✅ **Buy**: Oversold condition and bullish crossover. Potential short-term reversal.")
elif wait_signal:
    st.info("⚖️ **Hold / Wait**: Momentum improving, but no clear breakout yet.")
elif avoid_signal:
    st.error("❌ **Avoid**: Bearish alignment and weakening trend. Stay cautious.")
else:
    st.warning("ℹ️ No strong signal. Continue to monitor index behavior.")





# ─────────────────────────────────────
# 📰 News Sentiment Analysis (FinBERT)
# ─────────────────────────────────────
import feedparser
import datetime
import streamlit as st
from transformers import AutoTokenizer, AutoModelForSequenceClassification, pipeline

# ─────────────────────────────
# Cache FinBERT model
# ─────────────────────────────
@st.cache_resource
def load_finbert():
    tokenizer = AutoTokenizer.from_pretrained("ProsusAI/finbert")
    model     = AutoModelForSequenceClassification.from_pretrained("ProsusAI/finbert")
    return pipeline("sentiment-analysis", model=model, tokenizer=tokenizer)

sentiment_pipeline = load_finbert()

# ─────────────────────────────
# Function to fetch news from two RSS feeds
# ─────────────────────────────
def fetch_index_news(max_headlines=5):
    today = datetime.datetime.utcnow().date()
    feeds = {
        "CNBC TV18": "https://www.cnbc.com/id/19838190/device/rss/rss.html",
        "Economic Times": "https://economictimes.indiatimes.com/rssfeedsdefault.cms"
    }

    headlines = []
    per_source = max_headlines

    for source, url in feeds.items():
        feed = feedparser.parse(url)
        count = 0

        for entry in feed.entries:
            # some feeds use updated_parsed
            parsed = getattr(entry, "published_parsed", None) or getattr(entry, "updated_parsed", None)
            if not parsed:
                continue

            pub_date = datetime.datetime(*parsed[:6]).date()
            if pub_date == today:
                headlines.append({
                    "source": source,
                    "title": entry.title,
                    "link": entry.link,
                    "published": entry.published if hasattr(entry, "published") else ""
                })
                count += 1
                if count >= per_source:
                    break

    return headlines

# ─────────────────────────────
# News Sentiment Section
# ─────────────────────────────
st.markdown("---")
st.subheader("News Analysis")

raw_headlines = fetch_index_news(max_headlines=5)

if not raw_headlines:
    st.warning("No recent news found.")
else:
    # display and collect titles for sentiment
    titles = []
    for item in raw_headlines:
        st.info(
            f"**[{item['source']}]** {item['title']}  \n"
            f"_{item['published']}_  \n"
            f"{item['link']}"
        )
        titles.append(item["title"])

    # sentiment
    results = sentiment_pipeline(titles)
   

