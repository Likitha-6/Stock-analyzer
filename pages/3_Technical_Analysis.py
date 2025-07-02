import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import pandas as pd
from common.data import load_name_lookup
from indicators import apply_sma, apply_ema, get_pivot_lines
from indicators import detect_cross_signals,compute_rsi
from indicators import apply_smma

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
# Search bar (shared for all tabs)
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
# Tabs
# ─────────────────────────────
tab1, tab2, tab3 = st.tabs(["📊 Chart", "📋 Insights", "🔍 View"])

with tab1:
    # Load period state
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

    if "candle_days" not in st.session_state:
        st.session_state.candle_days = 1
    # Indicator selection
    all_indicators = st.multiselect(
        "Select Indicators",
        ["EMA", "Pivot Levels"],
        default=[]
    )

    sma_lengths = []
    ema_lengths = []
    show_pivots = False

    if "SMA" in all_indicators:
        sma_input = st.text_input("SMA Lengths (comma-separated)", value="20")
        sma_lengths = sorted(set(int(x.strip()) for x in sma_input.split(",") if x.strip().isdigit()))

    if "EMA" in all_indicators:
        ema_input = st.text_input("EMA Lengths (comma-separated)", value="20")
        ema_lengths = sorted(set(int(x.strip()) for x in ema_input.split(",") if x.strip().isdigit()))

    if "Pivot Levels" in all_indicators:
        show_pivots = True


    # Calculate the maximum indicator length needed
    max_len = max(sma_lengths + ema_lengths + [0])
    
    # Adjust period to load enough candles
    if interval == "1d":
        if max_len >= 200:
            period = "1y"
        elif max_len >= 100:
            period = "6mo"
        else:
            period = "3mo"
    elif interval == "240m":
        if max_len >= 200:
            period = "90d"
        else:
            period = "30d"
    elif interval == "60m":
        required_days = (max_len // 6) + 5  # Roughly 6 candles/hour per day
        period = f"{max(required_days, st.session_state.candle_days)}d"
    else:
        required_days = (max_len // 75) + 2  # Approx 75 candles/day for 5min interval
        period = f"{max(required_days, st.session_state.candle_days)}d"


    if interval != "1d" and chosen_sym:
        col1, col2 = st.columns([1, 1])

        with col1:
            if st.button("🔁 Load older candles"):
                st.session_state.candle_days += 1

        with col2:
            if st.button("♻️ Reset to 1 Day"):
                st.session_state.candle_days = 1

        st.caption(f"Showing: **{st.session_state.candle_days} day(s)** of data")

    
    if chosen_sym:
        try:
            df = yf.Ticker(chosen_sym + ".NS").history(interval=interval, period=period)
            df = df.reset_index()

            if df.empty:
                st.error("No data found.")
                st.session_state.df_stock = None
            else:
                df = df.reset_index()
                st.session_state.df_stock = df
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
                max_ticks = 15
                N = max(1, total_candles // max_ticks)
                tickvals = df["x_label"].iloc[::N].tolist()
                ticktext = df["x_label"].iloc[::N].tolist()

                if sma_lengths:
                    df = apply_sma(df, sma_lengths)
                    for sma_len in sma_lengths:
                        sma_col = f"SMA_{sma_len}"
                        if sma_col in df.columns:
                            valid_sma = df[sma_col].notna()
                            if valid_sma.sum() > 10:
                                fig.add_trace(go.Scatter(
                                    x=df["x_label"][valid_sma],
                                    y=df[sma_col][valid_sma],
                                    mode="lines",
                                    line=dict(width=1.5),
                                    name=f"SMA ({sma_len})"
                                ))




                if ema_lengths:
                    df = apply_ema(df, ema_lengths)
                    for ema_len in ema_lengths:
                        fig.add_trace(go.Scatter(
                            x=df["x_label"],
                            y=df[f"EMA_{ema_len}"],
                            mode="lines",
                            line=dict(width=1.5, dash="solid"),
                            name=f"EMA ({ema_len})"
                        ))

                if show_pivots:
                    pivot_lines, pivot_caption = get_pivot_lines(df, chosen_sym + ".NS", interval)
                    for line in pivot_lines:
                        fig.add_shape(**line["shape"])
                        fig.add_annotation(**line["annotation"])
                    st.caption(pivot_caption)

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
                    legend=dict(font=dict(color=font_color)),
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
                        "scrollZoom": True,
                        "displayModeBar": True,
                        "modeBarButtonsToRemove": ["zoom2d", "select2d", "lasso2d", "zoomIn2d", "zoomOut2d"],
                        "displaylogo": False
                    }
                )

        except Exception as e:
            st.error(f"Error: {e}")

with tab2:
    if chosen_sym:
        # Always fetch enough data for SMA 200
        df_insights = yf.Ticker(chosen_sym + ".NS").history(interval="1d", period="12mo")
        if not df_insights.empty:
            df_insights = df_insights.reset_index()
            df_insights["SMA_50"] = df_insights["Close"].rolling(window=50).mean()
            df_insights["SMA_200"] = df_insights["Close"].rolling(window=200).mean()
            df_insights["EMA_20"] = df_insights["Close"].ewm(span=20, adjust=False).mean()
            high_52w = df_insights["High"].max()
            low_52w = df_insights["Low"].min()

            latest_price = df_insights["Close"].iloc[-1]
            latest_sma50 = df_insights["SMA_50"].iloc[-1]
            latest_sma200 = df_insights["SMA_200"].iloc[-1]
            st.metric("💰 Current Price", f"₹{latest_price:,.2f}")
            st.metric("📈 50-day SMA", f"₹{latest_sma50:,.2f}" if pd.notna(latest_sma50) else "Not Available")
            st.metric("📉 200-day SMA", f"₹{latest_sma200:,.2f}" if pd.notna(latest_sma200) else "Not Available")
            if df_insights["EMA_20"].iloc[-1] > df_insights["EMA_20"].iloc[-5]:
                st.success("📈 20-day EMA is sloping upward — short-term trend is strengthening.")
            else:
                st.warning("📉 20-day EMA is sloping downward — short-term trend may be weakening.")

            if not df_insights["Close"].empty and len(df_insights["Close"]) >= 14:
                recent_close = df_insights["Close"].tail(14)
                volatility = recent_close.std()
                latest_price = df_insights["Close"].iloc[-1]
                vol_pct = (volatility / latest_price) * 100
            
                #st.subheader("📊 Volatility Insight")
                #st.write(f"14-day Price Std Dev: ₹{volatility:.2f} ({vol_pct:.2f}%)")
            
                if vol_pct > 5:
                    st.warning("⚠️ High volatility — expect bigger price swings.")
                elif vol_pct < 2:
                    st.info("🔒 Low volatility — stable price action.")
                else:
                    st.success("🔁 Moderate volatility — balanced risk/reward.")


            if abs(latest_price - high_52w) < 0.03 * high_52w:
                st.info("🚀 Price is near its 52-week high — possible resistance level.")
            elif abs(latest_price - low_52w) < 0.03 * low_52w:
                st.info("🔻 Price is near its 52-week low — potential support level.")
            df_insights["RSI"] = compute_rsi(df_insights)

            latest_rsi = df_insights["RSI"].iloc[-1]
            st.metric("📊 RSI (14-day)", f"{latest_rsi:.2f}")
            
            if latest_rsi > 70:
                st.warning("📈 The stock is overbought — momentum may slow, and there could be a short-term dip or consolidation.")
            elif latest_rsi < 30:
                st.success("📉 The stock is oversold — selling may be exhausted, and a potential rebound could follow.")
            else:
                st.info("⚖️ RSI is in neutral zone – no strong momentum signal.")
                        

            signal = detect_cross_signals(df_insights)
            if signal:
                st.info(signal)
        else:
            st.warning("Not enough data to compute insights.")



with tab3:
    st.subheader(f"📊 Market View for {chosen_sym or 'selected stock'}")

    if chosen_sym:
        try:
            # Load stock and NIFTY50 data
            stock_df = yf.Ticker(chosen_sym + ".NS").history(period="6mo", interval="1d")
            nifty_df = yf.Ticker("^NSEI").history(period="6mo", interval="1d")  # NIFTY 50

            if not stock_df.empty and not nifty_df.empty:
                stock_df = stock_df.reset_index()
                nifty_df = nifty_df.reset_index()

                # Ensure both have the same date index
                df_merged = pd.merge(
                    stock_df[["Date", "Close", "Volume"]],
                    nifty_df[["Date", "Close"]],
                    on="Date",
                    suffixes=("", "_NIFTY")
                )

                # Compute price returns
                df_merged["Return"] = df_merged["Close"].pct_change()
                df_merged["NIFTY_Return"] = df_merged["Close_NIFTY"].pct_change()

                #st.markdown("### 📈 Price Performance")
                change_1d = (df_merged["Close"].iloc[-1] / df_merged["Close"].iloc[-2] - 1) * 100
                change_5d = (df_merged["Close"].iloc[-1] / df_merged["Close"].iloc[-6] - 1) * 100
                change_1mo = (df_merged["Close"].iloc[-1] / df_merged["Close"].iloc[-22] - 1) * 100
                change_ytd = (df_merged["Close"].iloc[-1] / df_merged["Close"].iloc[0] - 1) * 100
                col1, col2, col3, col4 = st.columns(4)

                col1.metric("1 Day", f"{change_1d:.2f}%")
                col2.metric("5 Days", f"{change_5d:.2f}%")
                col3.metric("1 Month", f"{change_1mo:.2f}%")
                col4.metric("YTD", f"{change_ytd:.2f}%")

                

                #st.markdown("### 📊 Volume Analysis")
                latest_vol = df_merged["Volume"].iloc[-1]
                avg_vol = df_merged["Volume"].tail(21).mean()
                st.write(f"Today's Volume: `{int(latest_vol):,}` | 21-Day Avg: `{int(avg_vol):,}`")
                if latest_vol > 1.5 * avg_vol:
                    st.warning("🔺 Significant spike in trading volume today.")
                elif latest_vol < 0.5 * avg_vol:
                    st.info("🔻 Unusually low volume today.")
                else:
                    st.success("🟢 Volume within normal range.")

                #st.markdown("### 🧱 Support & Resistance (20-day)")
                support = df_merged["Close"].rolling(window=20).min().iloc[-1]
                resistance = df_merged["Close"].rolling(window=20).max().iloc[-1]
                current_price = df_merged["Close"].iloc[-1]

                st.write(f"📉 Support(20-day): ₹{support:.2f}")
                st.write(f"📈 Resistance(20-day): ₹{resistance:.2f}")

                #st.markdown("### 🤝 Correlation with NIFTY 50")
                correlation = df_merged["Return"].corr(df_merged["NIFTY_Return"])
                st.write(f"Correlation with NIFTY 50 (last 6 months): `{correlation:.2f}`")
                if correlation > 0.7:
                    st.success("✅ Highly correlated with broader market.")
                elif correlation < 0.3:
                    st.warning("⚠️ Moves independently of the NIFTY index.")

                #st.markdown("### 📅 Earnings")
                #st.info("🗓️ Next Earnings: Not available via yFinance. Please check official filings.")

                #st.markdown("### 🧭 Most Traded Price Range")
                price_bins = pd.cut(df_merged["Close"], bins=20)
                most_traded = price_bins.value_counts().idxmax()
                st.write(f"Most traded price range in last 6 months: **{most_traded}**")

            else:
                st.warning("Could not load complete data to compute View Tab insights.")

        except Exception as e:
            st.error(f"Error while generating view insights: {e}")
    else:
        st.info("Please select a stock to view details.")
