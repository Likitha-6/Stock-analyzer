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
col_sma_chk, col_sma_len, col_ema_chk, col_ema_len = st.columns([1, 1, 1, 1])

with col_sma_chk:
    show_sma = st.checkbox("📉 SMA", value=False)
with col_sma_len:
    sma_length = st.number_input("SMA Length", min_value=1, max_value=200, value=20, step=1)

with col_ema_chk:
    show_ema = st.checkbox("📈 EMA", value=False)
with col_ema_len:
    ema_length = st.number_input("EMA Length", min_value=1, max_value=200, value=20, step=1)


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
            total_candles = len(df)
            max_ticks = 15  # target max number of X-axis labels visible
            N = max(1, total_candles // max_ticks)
            
            tickvals = df["x_label"].iloc[::N].tolist()
            ticktext = df["x_label"].iloc[::N].tolist()
            if show_sma:
                df[f"SMA_{sma_length}"] = df["Close"].rolling(window=sma_length).mean()
                fig.add_trace(go.Scatter(
                    x=df["x_label"],
                    y=df[f"SMA_{sma_length}"],
                    mode="lines",
                    line=dict(color="#FFA500", width=1.5),
                    name=f"SMA ({sma_length})"
                ))
            
            if show_ema:
                df[f"EMA_{ema_length}"] = df["Close"].ewm(span=ema_length, adjust=False).mean()
                fig.add_trace(go.Scatter(
                    x=df["x_label"],
                    y=df[f"EMA_{ema_length}"],
                    mode="lines",
                    line=dict(color="#00C0F0", width=1.5, dash="dot"),
                    name=f"EMA ({ema_length})"
                ))


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
                    fixedrange=False  # ✅ Allow zoom
                ),
                plot_bgcolor=bg_color,
                paper_bgcolor=bg_color,
                font=dict(color=font_color),
                xaxis_rangeslider_visible=False,
                dragmode="pan",         # ✅ Pan by default
                hovermode="x unified",  # ✅ Show unified tooltip
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

