import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import pandas as pd
from ta.momentum import RSIIndicator
from ta.trend import MACD
from ta.volatility import BollingerBands
import streamlit.components.v1 as components

st.set_page_config(layout="wide")
st.title("📈 Technical Analysis")

# --- Input Section ---
ticker = st.text_input("Enter Stock Ticker (e.g., RELIANCE.NS):", "RELIANCE.NS")

# --- Load Data ---
@st.cache_data
def load_data(ticker):
    df = yf.download(ticker, period="6mo", interval="1d")
    return df

df = load_data(ticker)

# --- Validate & Clean Data ---
if df is None or df.empty or 'Close' not in df.columns:
    st.error("Failed to fetch valid stock data. Please check the ticker symbol.")
    st.stop()

# Clean numeric columns
for col in ['Open', 'High', 'Low', 'Close']:
    df[col] = pd.to_numeric(df[col], errors='coerce')

df.dropna(subset=['Open', 'High', 'Low', 'Close'], inplace=True)
df = df.sort_index()
df.index = pd.to_datetime(df.index)

# Extract clean close series
close_series = df['Close']

# --- Compute Indicators ---
df['MA20'] = close_series.rolling(window=20).mean()
df['EMA50'] = close_series.ewm(span=50, adjust=False).mean()

bb = BollingerBands(close=close_series, window=20, window_dev=2)
df['bb_bbm'] = bb.bollinger_mavg()
df['bb_bbh'] = bb.bollinger_hband()
df['bb_bbl'] = bb.bollinger_lband()

rsi = RSIIndicator(close=close_series).rsi()
macd = MACD(close=close_series)

# --- Tabs Layout ---
tabs = st.tabs(["📊 Chart & Indicators", "🧠 Insights", "💹 TradingView"])

# --- Tab 1: Candlestick & Indicators ---
with tabs[0]:
    st.subheader("Candlestick Chart with Technical Indicators")

    fig = go.Figure()

    # Candlestick
    fig.add_trace(go.Candlestick(
        x=df.index,
        open=df['Open'],
        high=df['High'],
        low=df['Low'],
        close=df['Close'],
        name='Candlestick',
        increasing_line_color='green',
        decreasing_line_color='red'
    ))

    # Moving Averages
    fig.add_trace(go.Scatter(
        x=df.index, y=df['MA20'], mode='lines',
        line=dict(color='blue', width=1), name='MA20'
    ))
    fig.add_trace(go.Scatter(
        x=df.index, y=df['EMA50'], mode='lines',
        line=dict(color='orange', width=1), name='EMA50'
    ))

    # Bollinger Bands
    fig.add_trace(go.Scatter(
        x=df.index, y=df['bb_bbh'], line=dict(color='gray', width=1),
        name='Bollinger High', opacity=0.4
    ))
    fig.add_trace(go.Scatter(
        x=df.index, y=df['bb_bbl'], line=dict(color='gray', width=1),
        name='Bollinger Low', opacity=0.4, fill='tonexty',
        fillcolor='rgba(173,216,230,0.2)'
    ))

    fig.update_layout(
        title=f"{ticker} - Candlestick with MA, EMA, Bollinger Bands",
        xaxis_title="Date",
        yaxis_title="Price",
        xaxis_rangeslider_visible=True,
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
        template="plotly_white",
        height=600
    )

    st.plotly_chart(fig, use_container_width=True)

# --- Tab 2: Insights ---
with tabs[1]:
    st.subheader("📌 Indicator-Based Insights")

    latest_rsi = rsi.iloc[-1]
    if latest_rsi > 70:
        rsi_msg = f"⚠️ RSI is {latest_rsi:.2f} — stock may be overbought."
    elif latest_rsi < 30:
        rsi_msg = f"📉 RSI is {latest_rsi:.2f} — stock may be oversold."
    else:
        rsi_msg = f"✅ RSI is {latest_rsi:.2f} — stock is in a neutral range."
    st.markdown(f"**RSI Insight:** {rsi_msg}")

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
