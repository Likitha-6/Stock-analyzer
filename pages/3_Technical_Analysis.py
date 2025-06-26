import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import pandas as pd
import ta
import streamlit.components.v1 as components

st.set_page_config(layout="wide")
st.title("📈 Technical Analysis")

# Stock input
ticker = st.text_input("Enter Stock Ticker (e.g., RELIANCE.NS):", "RELIANCE.NS")

# Load and cache data
@st.cache_data
def load_data(ticker):
    df = yf.download(ticker, period="6mo", interval="1d")
    df.dropna(inplace=True)
    return df

df = load_data(ticker)

# Tabs for charts and indicators
tabs = st.tabs(["📊 Chart & Indicators", "🧠 Insights", "💹 TradingView"])

# --- TAB 1: Your Technical Charts ---
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

    from ta.momentum import RSIIndicator
    from ta.trend import MACD
    
    # Clean Close prices
    df['Close'] = pd.to_numeric(df['Close'], errors='coerce')
    df.dropna(subset=['Close'], inplace=True)
    
    # Calculate indicators
    rsi = RSIIndicator(close=df['Close']).rsi()
    macd = MACD(close=df['Close'])


    st.subheader("RSI and MACD")
    #rsi = ta.momentum.RSIIndicator(df['Close']).rsi()
    #macd = ta.trend.MACD(df['Close'])
    rsi = RSIIndicator(close=df['Close']).rsi()
    macd = MACD(close=df['Close'])


    st.line_chart(rsi.rename("RSI"))
    st.line_chart(macd.macd_diff().rename("MACD Histogram"))

# --- TAB 2: Insights ---
with tabs[1]:
    st.subheader("📌 Indicator-Based Insights")
    latest_rsi = rsi.iloc[-1]
    rsi_msg = "✅ RSI indicates the stock is in a neutral zone."
    if latest_rsi > 70:
        rsi_msg = "⚠️ RSI is above 70 — the stock may be overbought."
    elif latest_rsi < 30:
        rsi_msg = "📉 RSI is below 30 — the stock may be oversold."
    st.markdown(f"**RSI Insight:** {rsi_msg} (Current RSI: {latest_rsi:.2f})")

    macd_diff = macd.macd_diff()
    recent_macd_cross = macd_diff.diff().iloc[-1]
    if recent_macd_cross > 0:
        st.markdown("**MACD Insight:** 🟢 MACD crossover detected — potential bullish momentum.")
    elif recent_macd_cross < 0:
        st.markdown("**MACD Insight:** 🔴 MACD cross-under detected — potential bearish signal.")
    else:
        st.markdown("**MACD Insight:** No recent MACD signal.")

# --- TAB 3: TradingView Embed ---
with tabs[2]:
    st.subheader("📉 Interactive TradingView Chart")
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
