import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import pandas as pd
from common.data import load_name_lookup

st.set_page_config(page_title="📈 Technical Chart", layout="wide")

# ─────────────────────────────
# Theme selector
# ─────────────────────────────
col_title, col_theme = st.columns([6, 1])
with col_title:
    st.title("📈 Indian Stock – Technical Analysis")
with col_theme:
    dark_mode = st.checkbox("🌙 Dark Mode", value=False)

theme = "Dark" if dark_mode else "Light"


# Theme colors
bg_color = "#FFFFFF" if theme == "Light" else "#0E1117"
font_color = "#000000" if theme == "Light" else "#FFFFFF"
increasing_color = "#00B26F" if theme == "Light" else "#26de81"
decreasing_color = "#FF3C38" if theme == "Light" else "#eb3b5a"

# ─────────────────────────────
# Indicator toggles with user-defined lengths
# ─────────────────────────────

# ─────────────────────────────
# Multi-Indicator Selector (SMA/EMA)
# ─────────────────────────────
# ─────────────────────────────
# SMA / EMA toggle and input
# ─────────────────────────────
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

show_pivots = st.checkbox("📏 Show Pivot Points (Daily)", value=False)




# ─────────────────────────────
# Interval Dropdown
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

# ─────────────────────────────
# Search bar – symbol or company name
# ─────────────────────────────
name_df = load_name_lookup()
symbol2name = dict(zip(name_df["Symbol"], name_df["Company Name"]))

search_query = st.text_input("Search by Symbol or Company Name").strip().lower()
chosen_sym = None

if search_query:
    mask = (
        name_df["Symbol"].str.lower().str.contains(search_query) |
        name_df["Company Name"].str.lower().str.contains(search_query)
    )
    matches = name_df[mask]

    if matches.empty:
        st.warning("No matching stock found.")
    else:
        selected = st.selectbox(
            "Select Stock",
            matches["Symbol"] + " - " + matches["Company Name"]
        )
        chosen_sym = selected.split(" - ")[0]

# ─────────────────────────────
# Load period state
# ─────────────────────────────
if "candle_days" not in st.session_state:
    st.session_state.candle_days = 1

if interval == "1d":
    period = "3mo"
elif interval == "240m":  # 4 hours
    period = f"{max(st.session_state.candle_days, 7)}d"  # Minimum 7 days
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


# ─────────────────────────────
# Load and render chart
# ─────────────────────────────
if chosen_sym:
    try:
        df = yf.Ticker(chosen_sym + ".NS").history(interval=interval, period=period)
        df = df.reset_index()
        
        if df.empty:
            st.error("No data found.")
        else:
            df = df.reset_index()
            x_col = "Datetime" if "Datetime" in df.columns else "Date"
            df["x_label"] = df[x_col].dt.strftime("%d/%m %H:%M") if "m" in interval or "h" in interval else df[x_col].dt.strftime("%d/%m")
            # Compute classic pivot points from previous day's data
            # ─────────────────────────────
            # Pivot Points – TradingView-style (fixed from previous day/week)
            # ─────────────────────────────
            pivot_levels = {}
            
            if show_pivots:
                # Get fixed daily or weekly OHLC regardless of current chart interval
                pivot_base_data = yf.Ticker(chosen_sym + ".NS").history(interval="1d", period="7d").reset_index()
            
                if len(pivot_base_data) >= 2:
                    prev_day = pivot_base_data.iloc[-2]  # Previous full day
                    high = prev_day["High"]
                    low = prev_day["Low"]
                    close = prev_day["Close"]
            
                    # Choose the pivot type
                    pivot_type = st.selectbox("Pivot Type", ["Classic", "Fibonacci", "Woodie", "Camarilla", "Demark"], index=0)
            
                    def calculate_pivots(high, low, close, pivot_type):
                        if pivot_type == "Classic":
                            P = (high + low + close) / 3
                            R1 = 2 * P - low
                            S1 = 2 * P - high
                            R2 = P + (high - low)
                            S2 = P - (high - low)
                            R3 = high + 2 * (P - low)
                            S3 = low - 2 * (high - P)
                        elif pivot_type == "Fibonacci":
                            P = (high + low + close) / 3
                            R1 = P + 0.382 * (high - low)
                            S1 = P - 0.382 * (high - low)
                            R2 = P + 0.618 * (high - low)
                            S2 = P - 0.618 * (high - low)
                            R3 = P + 1.000 * (high - low)
                            S3 = P - 1.000 * (high - low)
                        elif pivot_type == "Woodie":
                            P = (high + low + 2 * close) / 4
                            R1 = 2 * P - low
                            S1 = 2 * P - high
                            R2 = P + (high - low)
                            S2 = P - (high - low)
                            R3 = high + 2 * (P - low)
                            S3 = low - 2 * (high - P)
                        elif pivot_type == "Camarilla":
                            P = close
                            range_ = high - low
                            R1 = close + 0.0916 * range_
                            S1 = close - 0.0916 * range_
                            R2 = close + 0.183 * range_
                            S2 = close - 0.183 * range_
                            R3 = close + 0.275 * range_
                            S3 = close - 0.275 * range_
                        elif pivot_type == "Demark":
                            open_ = prev_day["Open"]
                            if close < open_:
                                X = high + (2 * low) + close
                            elif close > open_:
                                X = (2 * high) + low + close
                            else:
                                X = high + low + (2 * close)
                            P = X / 4
                            R1 = X / 2 - low
                            S1 = X / 2 - high
                            R2 = R3 = S2 = S3 = None  # Not defined in Demark
            
                        return {
                            "Pivot": P,
                            "R1": R1, "R2": R2, "R3": R3,
                            "S1": S1, "S2": S2, "S3": S3
                        }
            
                    pivot_levels = calculate_pivots(high, low, close, pivot_type)
            

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
            total_candles = len(df)
            max_ticks = 15  # target max number of X-axis labels visible
            N = max(1, total_candles // max_ticks)
            
            tickvals = df["x_label"].iloc[::N].tolist()
            ticktext = df["x_label"].iloc[::N].tolist()
            # Add SMA overlays
            for sma_len in sma_lengths:
                df[f"SMA_{sma_len}"] = df["Close"].rolling(window=sma_len).mean()
                fig.add_trace(go.Scatter(
                    x=df["x_label"],
                    y=df[f"SMA_{sma_len}"],
                    mode="lines",
                    line=dict(width=1.5),
                    name=f"SMA ({sma_len})"
                ))
            
            # Add EMA overlays
            for ema_len in ema_lengths:
                df[f"EMA_{ema_len}"] = df["Close"].ewm(span=ema_len, adjust=False).mean()
                fig.add_trace(go.Scatter(
                    x=df["x_label"],
                    y=df[f"EMA_{ema_len}"],
                    mode="lines",
                    line=dict(width=1.5, dash="solid"),
                    name=f"EMA ({ema_len})"
                ))

            # Draw pivot levels as horizontal lines
            for name, value in pivot_levels.items():
                fig.add_hline(
                    y=value,
                    line=dict(width=1, dash="dot"),
                    annotation_text=name,
                    annotation_position="right",
                    line_color="#999999"
                )


            fig.update_layout(
                title=f"{chosen_sym}.NS – {label} Chart ({period})",
                xaxis_title="Date/Time",
                yaxis_title="Price",
                xaxis=dict(
                    type="category",
                    tickangle=-45,
                    showgrid=False,
                    tickfont=dict(color=font_color),
                    tickmode="array",
                    tickvals=tickvals,
                    ticktext=ticktext
                ),
                yaxis=dict(
                    showgrid=False,
                    tickfont=dict(color="#000000" if theme == "Light" else font_color),
                    fixedrange=False
                ),
                plot_bgcolor=bg_color,
                paper_bgcolor=bg_color,
                font=dict(color=font_color),
                legend=dict(font=dict(color=font_color)),  # ✅ Add this
                xaxis_rangeslider_visible=False,
                dragmode="pan",
                hovermode="x unified",
                height=600,
                width=900
            )

            

            st.plotly_chart(
                fig,
                use_container_width=False,
                config={
                    "scrollZoom": True,             # 🔍 Zoom with scroll wheel
                    "displayModeBar": True,         # 🛠 Show toolbar for zoom/pan
                    "modeBarButtonsToRemove": ["zoom2d", "select2d", "lasso2d", "zoomIn2d", "zoomOut2d"],
                    "displaylogo": False
                }
            )



    except Exception as e:
        st.error(f"Error: {e}")

