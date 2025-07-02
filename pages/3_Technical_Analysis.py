import streamlit as st
import yfinance as yf
import plotly.graph_objects as go

st.set_page_config(page_title="📈 Technical Chart", layout="wide")
st.title("📈 Indian Stock – Technical Analysis")

# ─────────────────────────────
# Interval dropdown
# ─────────────────────────────
interval_mapping = {
    "5 minutes": "5m",
    "15 minutes": "15m",
    "1 hour": "60m",
    "4 hours": "240m",
    "1 day": "1d"
}

interval_label = st.selectbox("Select interval", list(interval_mapping.keys()), index=4)
interval = interval_mapping[interval_label]

symbol = st.text_input("Enter NSE symbol (e.g., INFY, RELIANCE):").upper().strip()

# ─────────────────────────────
# Load and plot data
# ─────────────────────────────
if symbol:
    stock = yf.Ticker(symbol + ".NS")

    try:
        df = stock.history(period="7d" if "m" in interval else "3mo", interval=interval)

        if df.empty:
            st.error("No data available for this stock + interval combination.")
        else:
            fig = go.Figure()

            fig.add_trace(go.Candlestick(
                x=df.index,
                open=df['Open'],
                high=df['High'],
                low=df['Low'],
                close=df['Close'],
                name="Candles"
            ))

            fig.update_layout(
                title=f"{symbol}.NS – {interval_label} Candlestick Chart",
                xaxis_title="Date",
                yaxis_title="Price",
                xaxis_rangeslider_visible=False,
                height=600
            )

            st.plotly_chart(fig, use_container_width=True)

    except Exception as e:
        st.error(f"Failed to fetch data: {e}")

