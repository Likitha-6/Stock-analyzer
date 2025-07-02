import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import pandas as pd

st.set_page_config(page_title="📈 Technical Chart", layout="wide")
st.title("📈 Indian Stock – Technical Analysis")

# ─────────────────────────────
# Theme selector
# ─────────────────────────────
theme = st.selectbox("Chart Theme", ["Light", "Dark"], index=0)

# Theme colors
bg_color = "#FFFFFF" if theme == "Light" else "#0E1117"
grid_color = "#CCCCCC" if theme == "Light" else "#333333"
font_color = "#000000" if theme == "Light" else "#FFFFFF"
increasing_color = "#00B26F" if theme == "Light" else "#26de81"
decreasing_color = "#FF3C38" if theme == "Light" else "#eb3b5a"

# ─────────────────────────────
# Interval & Symbol Input
# ─────────────────────────────
interval_mapping = {
    "5 minutes": "5m",
    "15 minutes": "15m",
    "1 hour": "60m",
    "4 hours": "240m",
    "1 day": "1d"
}

label = st.selectbox("Select Interval", list(interval_mapping.keys()), index=0)
interval = interval_mapping[label]

symbol = st.text_input("Enter NSE Symbol (e.g., INFY, RELIANCE):").upper().strip()

# ─────────────────────────────
# Candle loader state
# ─────────────────────────────
if "candle_days" not in st.session_state:
    st.session_state.candle_days = 1

if interval == "1d":
    period = "3mo"
else:
    period = f"{st.session_state.candle_days}d"

if interval != "1d":
    if st.button("🔁 Load older candles"):
        st.session_state.candle_days += 1

    st.caption(f"Showing: **{st.session_state.candle_days} day(s)** of data")

# ─────────────────────────────
# Load and render chart
# ─────────────────────────────
if symbol:
    try:
        df = yf.Ticker(symbol + ".NS").history(interval=interval, period=period)

        if df.empty:
            st.error("No data found.")
        else:
            df = df.reset_index()
            x_col = "Datetime" if "Datetime" in df.columns else "Date"
            df["x_label"] = df[x_col].dt.strftime("%d/%m %H:%M") if "m" in interval or "h" in interval else df[x_col].dt.strftime("%d/%m")

            fig = go.Figure()

            fig.add_trace(go.Candlestick(
                x=df["x_label"],
                open=df["Open"],
                high=df["High"],
                low=df["Low"],
                close=df["Close"],
                increasing_line_color=increasing_color,
                decreasing_line_color=decreasing_color,
                name="Price"
            ))

            fig.update_layout(
                title=f"{symbol}.NS – {label} Chart ({period})",
                xaxis_title="Date/Time",
                yaxis_title="Price",
                xaxis=dict(type="category", tickangle=-45, gridcolor=grid_color),
                yaxis=dict(gridcolor=grid_color),
                plot_bgcolor=bg_color,
                paper_bgcolor=bg_color,
                font=dict(color=font_color),
                xaxis_rangeslider_visible=False,
                height=600
            )

            st.plotly_chart(fig, use_container_width=True)

    except Exception as e:
        st.error(f"Error: {e}")
