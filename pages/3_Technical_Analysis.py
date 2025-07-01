from streamlit_lightweight_charts import renderLightweightCharts

# ...

if chosen_sym:
    stock = yf.Ticker(chosen_sym + ".NS")
    df = stock.history(period="3mo", interval="1d")

    if df.empty:
        st.error("No data available for this stock.")
    else:
        df = df.reset_index()
        df["time"] = df["Date"].dt.strftime("%Y-%m-%d")

        # Prepare candlestick data
        ohlc = [
            {
                "time": row["time"],
                "open": row["Open"],
                "high": row["High"],
                "low": row["Low"],
                "close": row["Close"]
            }
            for _, row in df.iterrows()
        ]

        # Prepare volume data
        volume = [
            {
                "time": row["time"],
                "value": row["Volume"],
                "color": "green" if row["Close"] >= row["Open"] else "red"
            }
            for _, row in df.iterrows()
        ]

        chart_config = [
            {
                "type": "Candlestick",
                "data": ohlc,
            },
            {
                "type": "Histogram",
                "data": volume,
                "options": {
                    "color": "rgba(0,150,136,0.5)",
                    "priceFormat": {"type": "volume"},
                    "priceScaleId": "",
                },
                "priceScale": {
                    "scaleMargins": {
                        "top": 0.8,
                        "bottom": 0,
                    },
                },
            }
        ]

        st.subheader(f"📊 {symbol2name.get(chosen_sym, chosen_sym)} – {chosen_sym}.NS")
        renderLightweightCharts(chart_config, height=500)
