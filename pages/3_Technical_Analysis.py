import yfinance as yf
import streamlit as st
import pandas as pd

symbol = st.text_input("Enter NSE Symbol", "RELIANCE")
period = st.selectbox("Select period", ["1mo", "3mo", "6mo", "1y", "3y", "5y", "max"], index=2)

if symbol:
    df = yf.download(f"{symbol}.NS", period=period, interval="1d")

    if df.empty:
        st.error("⚠️ No data returned. Try a different symbol or period.")
        st.stop()

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(-1)

    required = ["Open", "High", "Low", "Close", "Volume"]
    missing = [col for col in required if col not in df.columns]
    if missing:
        st.error(f"❌ Missing expected columns: {missing}")
        st.dataframe(df.head())
        st.stop()

    df = df.dropna(subset=required)
    st.success("✅ Data loaded successfully.")
    st.dataframe(df.tail())
