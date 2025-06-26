import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import pandas as pd
from ta.momentum import RSIIndicator
from ta.trend import MACD
import streamlit.components.v1 as components

st.set_page_config(layout="wide")
st.title("📈 Technical Analysis")

# --- Input Section ---
ticker = st.text_input("Enter Stock Ticker (e.g., RELIANCE.NS):", "RELIANCE.NS")

# --- Load Data ---
@st.cache_data
def load_data(ticker):
    df = yf.download(ticker, period="6mo", interval="1d")
    df.dropna(inplace=True)
    return df

df = load_data(ticker)

# --- Clean 'Close' Column ---
close_series = pd.Series(df['Close'].values.flatten(), index=df.index)
close_series = pd.to_numeric(close_series, errors='coerce')
close_series.dropna(inplace=True)
df = df.loc[close_series.index]
df['Close'] = close_series  # replace with cleaned version

# --- Compute Indicators ---
rsi = RSIIndicator(close=close_series).rsi()
macd = MACD(close=close_series)

# --- Tabs Layout ---
tabs = st.tabs(["📊 Chart & Indicators", "🧠 Insights", "💹 TradingView"])

# --- Tab 1: Candlestick & Indicators ---
with tabs[0]:
    st.subheader("Candlestick Chart with Moving Average")
    df['MA20'] = df['Close'].rolling(window=20).mean()

    fig = go.Figure()
    fig.add_trace(go.Candlestick(
        x=df.index,
        open=df['Open'],
        high=df['High'],
        low=df['Low'],
        close=df['Close'],
        name='Candlestick'
    ))
    fig.add_trace(go.Scatter(
        x=df.index,
        y=df['MA20'],
        line=dict(color='blue', width=1),
        name='20-day MA'
    ))
    fig.update_layout(xaxis_rangeslider_visible=False)
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("RSI and MACD")
    st.line_chart(rsi.rename("RSI"))
    st.line_chart(macd.macd_diff().rename("MACD Histogram"))

# --- Tab 2: Insights ---
with tabs[1]:
    st.subheader("📌 Indicator-Based Insights")

    # RSI insight
    latest_rsi = rsi.iloc[-1]
    if latest_rsi > 70:
        rsi_msg = f"⚠️ RSI is {latest_rsi:.2f} — stock may be overbought."
    elif latest_rsi < 30:
        rsi_msg = f"📉 RSI is {latest_rsi:.2f} — stock may be oversold."
    else:
        rsi_msg = f"✅ RSI is {latest_rsi:.2f} — stock is in a neutral range."
    st.markdown(f"**RSI Insight:** {rsi_msg}")

    # MACD insight
    recent_macd_cross = macd.macd_diff().diff().iloc[-1]
    if recent_macd_cross > 0:
        macd_msg = "🟢 MACD crossover detected — potential bullish momentum."
    elif recent_macd_cross < 0:
        macd_msg = "🔴 MACD cross-under detected — potential bearish momentum."
    else:
        macd_msg = "ℹ️ No recent MACD signal."
    st.markdown(f"**MACD Insight:** {macd_msg}")

# --- Tab 3: TradingView Widget ---
with tabs[2]:
    st.subheader("💹 Interactive TradingView Chart")

    # Format for TradingView: NSE:TICKER
    symbol = f"NSE:{ticker.split('.')[0]}" if ".NS" in ticker else ticker.upper()

    tv_widget = f"""
    <div class="tradingview-widget-container">
      <div id="tradingview_chart"></div>
      <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
      <script type="text/javascript">
      new TradingView.widget({{
        "width": "100%",
        "height": 600,
        "symbol": "{symbol}",
        "interval": "D",
        "timezone": "Etc/UTC",
        "theme": "light",
        "style": "1",
        "locale": "en",
        "toolbar_bg": "#f1f3f6",
        "enable_publishing": false,
        "allow_symbol_change": true,
        "container_id": "tradingview_chart"
      }});
      </script>
    </div>
    """
    components.html(tv_widget, height=650)

