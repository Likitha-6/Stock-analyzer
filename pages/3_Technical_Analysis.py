import streamlit as st
import yfinance as yf
import plotly.graph_objects as go

st.set_page_config(page_title="📈 Technical Chart", layout="wide")
st.title("📈 Indian Stock – Technical Analysis")

interval_mapping = {
    "5 minutes": ("5m", "1d"),
    "15 minutes": ("15m", "5d"),
    "1 hour": ("60m", "7d"),
    "4 hours": ("240m", "10d"),
    "1 day": ("1d", "3mo")
}

label = st.selectbox("Select Interval", list(interval_mapping.keys()), index=4)
interval, period = interval_mapping[label]

symbol = st.text_input("Enter NSE Symbol (e.g., INFY, RELIANCE):").upper().strip()

if symbol:
    try:
        df = yf.Ticker(symbol + ".NS").history(interval=interval, period=period)

        if df.empty:
            st.error("No data found.")
        else:
            df = df.reset_index()
            x_col = "Datetime" if "Datetime" in df.columns else "Date"

            fig = go.Figure()

            fig.add_trace(go.Candlestick(
                x=df[x_col],
                open=df['Open'],
                high=df['High'],
                low=df['Low'],
                close=df['Close'],
                name="Price"
            ))

            # Smart tick format: show date only
            tick_format = "%d/%m" if interval == "1d" else "%d/%m\n%H:%M"

            fig.update_layout(
                title=f"{symbol}.NS – {label} Chart",
                xaxis_title="Date",
                yaxis_title="Price",
                xaxis_rangeslider_visible=False,
                xaxis=dict(
                    tickformat=tick_format,
                    tickangle=-45
                ),
                height=600
            )

            st.plotly_chart(fig, use_container_width=True)

    except Exception as e:
        st.error(f"Error: {e}")
