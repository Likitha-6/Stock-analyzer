import streamlit as st
import yfinance as yf
import plotly.graph_objects as go

st.set_page_config(page_title="📈 Technical Chart", layout="wide")
st.title("📈 Indian Stock – Technical Analysis")

symbol = st.text_input("Enter NSE symbol (e.g., INFY, RELIANCE):").upper().strip()

if symbol:
    data = yf.Ticker(symbol + ".NS").history(period="3mo", interval="1d")

    if data.empty:
        st.error("No data found.")
    else:
        fig = go.Figure()

        # Candlestick
        fig.add_trace(go.Candlestick(
            x=data.index,
            open=data['Open'],
            high=data['High'],
            low=data['Low'],
            close=data['Close'],
            name="Price"
        ))

        # Volume as bar
        fig.add_trace(go.Bar(
            x=data.index,
            y=data["Volume"],
            name="Volume",
            marker_color="lightblue",
            yaxis="y2",
            opacity=0.3
        ))

        # Layout with dual y-axis
        fig.update_layout(
            title=f"{symbol}.NS – Last 3 Months",
            xaxis=dict(title="Date"),
            yaxis=dict(title="Price"),
            yaxis2=dict(title="Volume", overlaying="y", side="right", showgrid=False),
            xaxis_rangeslider_visible=False,
            height=600
        )

        st.plotly_chart(fig, use_container_width=True)
