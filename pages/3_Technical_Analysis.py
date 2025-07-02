import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import pandas as pd
from common.data import load_name_lookup
from pivot_utils import get_previous_period_ohlc, calculate_classic_pivots

st.set_page_config(page_title="📈 Technical Chart", layout="wide")

# Theme selector
col_title, col_theme = st.columns([6, 1])
with col_title:
    st.title("📈 Indian Stock – Technical Analysis")
with col_theme:
    dark_mode = st.checkbox("🌙 Dark Mode", value=False)

theme = "Dark" if dark_mode else "Light"

bg_color = "#FFFFFF" if theme == "Light" else "#0E1117"
font_color = "#000000" if theme == "Light" else "#FFFFFF"
increasing_color = "#00B26F" if theme == "Light" else "#26de81"
decreasing_color = "#FF3C38" if theme == "Light" else "#eb3b5a"

# SMA/EMA inputs
col_sma_chk, col_ema_chk = st.columns(2)
with col_sma_chk:
    show_sma = st.checkbox("📉 Show SMA")
with col_ema_chk:
    show_ema = st.checkbox("📈 Show EMA")

col_sma_input, col_ema_input = st.columns(2)
if show_sma:
    with col_sma_input:
        sma_input = st.text_input("SMA Lengths (comma-separated)", value="20")
    sma_lengths = sorted(set(int(x.strip()) for x in sma_input.split(",") if x.strip().isdigit()))
else:
    sma_lengths = []

if show_ema:
    with col_ema_input:
        ema_input = st.text_input("EMA Lengths (comma-separated)", value="20")
    ema_lengths = sorted(set(int(x.strip()) for x in ema_input.split(",") if x.strip().isdigit()))
else:
    ema_lengths = []

# Interval selector
interval_mapping = {
    "5 minutes": "5m",
    "15 minutes": "15m",
    "1 hour": "60m",
    "4 hours": "240m",
    "1 day": "1d"
}
label = st.selectbox("Select Interval", list(interval_mapping.keys()), index=0)
interval = interval_mapping[label]

# Stock search
name_df = load_name_lookup()
symbol2name = dict(zip(name_df["Symbol"], name_df["Company Name"]))
search_query = st.text_input("Search by Symbol or Company Name").strip().lower()
chosen_sym = None
show_pivots = st.checkbox("📌 Show Pivot Levels", value=True)
pivot_levels = {}

if search_query:
    mask = (
        name_df["Symbol"].str.lower().str.contains(search_query) |
        name_df["Company Name"].str.lower().str.contains(search_query)
    )
    matches = name_df[mask]
    if matches.empty:
        st.warning("No matching stock found.")
    else:
        selected = st.selectbox("Select Stock", matches["Symbol"] + " - " + matches["Company Name"])
        chosen_sym = selected.split(" - ")[0]

# Load period state
if "candle_days" not in st.session_state:
    st.session_state.candle_days = 1

if interval == "1d":
    period = "3mo"
elif interval == "240m":
    period = "30d"
elif interval == "60m":
    period = f"{max(st.session_state.candle_days, 5)}d"
else:
    period = f"{st.session_state.candle_days}d"

if interval != "1d" and chosen_sym:
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("🔁 Load older candles"):
            st.session_state.candle_days += 1
    with col2:
        if st.button("♻️ Reset to 1 Day"):
            st.session_state.candle_days = 1
    st.caption(f"Showing: **{st.session_state.candle_days} day(s)** of data")

# Load and render chart
if chosen_sym:
    try:
        df = yf.Ticker(chosen_sym + ".NS").history(interval=interval, period=period)
        df = df.reset_index()
        if df.empty:
            st.error("No data found.")
        else:
            x_col = "Datetime" if "Datetime" in df.columns else "Date"
            df["x_label"] = df[x_col].dt.strftime("%d/%m %H:%M") if "m" in interval or "h" in interval else df[x_col].dt.strftime("%d/%m")

            fig = go.Figure()
            fig.add_trace(go.Candlestick(
                x=df["x_label"], open=df["Open"], high=df["High"],
                low=df["Low"], close=df["Close"],
                increasing_line_color=increasing_color,
                decreasing_line_color=decreasing_color,
                name="Price"
            ))

            total_candles = len(df)
            N = max(1, total_candles // 15)
            tickvals = df["x_label"].iloc[::N].tolist()
            ticktext = df["x_label"].iloc[::N].tolist()

            for sma_len in sma_lengths:
                df[f"SMA_{sma_len}"] = df["Close"].rolling(window=sma_len).mean()
                fig.add_trace(go.Scatter(
                    x=df["x_label"], y=df[f"SMA_{sma_len}"], mode="lines",
                    line=dict(width=1.5), name=f"SMA ({sma_len})"
                ))

            for ema_len in ema_lengths:
                df[f"EMA_{ema_len}"] = df["Close"].ewm(span=ema_len, adjust=False).mean()
                fig.add_trace(go.Scatter(
                    x=df["x_label"], y=df[f"EMA_{ema_len}"], mode="lines",
                    line=dict(width=1.5, dash="solid"), name=f"EMA ({ema_len})"
                ))

            if show_pivots:
                base = get_previous_period_ohlc(chosen_sym + ".NS")
                if base:
                    pivots = calculate_classic_pivots(base["high"], base["low"], base["close"])
                    for label, value in pivots.items():
                        fig.add_shape(
                            type="line", x0=df["x_label"].iloc[0], x1=df["x_label"].iloc[-1],
                            y0=value, y1=value,
                            line=dict(color="#999999", width=1, dash="dot"),
                            layer="below"
                        )
                        fig.add_annotation(
                            x=df["x_label"].iloc[-1], y=value,
                            text=label, showarrow=False,
                            xanchor="left", yanchor="middle",
                            font=dict(color=font_color, size=10),
                            bgcolor=bg_color, borderpad=2
                        )
                    st.caption(f"📏 Pivot Source: {base['date']} – Classic")

            fig.update_layout(
                title=f"{chosen_sym}.NS – {label} Chart ({period})",
                xaxis_title="Date/Time", yaxis_title="Price",
                xaxis=dict(type="category", tickangle=-45, showgrid=False,
                           tickfont=dict(color=font_color), tickmode="array",
                           tickvals=tickvals, ticktext=ticktext),
                yaxis=dict(showgrid=False, tickfont=dict(color=font_color), fixedrange=False),
                plot_bgcolor=bg_color, paper_bgcolor=bg_color,
                font=dict(color=font_color),
                legend=dict(font=dict(color=font_color)),
                xaxis_rangeslider_visible=False, dragmode="pan",
                hovermode="x unified", height=600, width=900
            )

            st.plotly_chart(fig, use_container_width=False, config={
                "scrollZoom": True, "displayModeBar": True,
                "modeBarButtonsToRemove": ["zoom2d", "select2d", "lasso2d", "zoomIn2d", "zoomOut2d"],
                "displaylogo": False
            })

    except Exception as e:
        st.error(f"Error: {e}")
