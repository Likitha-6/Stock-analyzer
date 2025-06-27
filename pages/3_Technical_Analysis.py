# --- Tab 1: Candlestick & Indicators ---
with tabs[0]:
    st.subheader("Candlestick Chart with Technical Indicators")

    # Add Indicators
    df['MA20'] = df['Close'].rolling(window=20).mean()
    df['EMA50'] = df['Close'].ewm(span=50, adjust=False).mean()

    # Bollinger Bands
    from ta.volatility import BollingerBands
    bb = BollingerBands(close=df['Close'], window=20, window_dev=2)
    df['bb_bbm'] = bb.bollinger_mavg()
    df['bb_bbh'] = bb.bollinger_hband()
    df['bb_bbl'] = bb.bollinger_lband()

    # Create Figure
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
        name='Bollinger Low', opacity=0.4, fill='tonexty', fillcolor='rgba(173,216,230,0.2)'
    ))

    # Layout Config
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
