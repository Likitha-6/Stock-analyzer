import streamlit as st
import yfinance as yf
import pandas as pd

# Load data
@st.cache_data
def load_data(ticker):
    try:
        df = yf.download(ticker, period="6mo", interval="1d")
        return df
    except Exception as e:
        st.error(f"Error downloading data: {e}")
        return None

df = load_data(ticker)

# Check if df is valid DataFrame
if df is None:
    st.error("Failed to download data.")
    st.stop()

st.write(f"Type of df: {type(df)}")
st.write(f"Columns in df: {df.columns}")

# If df.columns is a MultiIndex, flatten it or extract the 'Adj Close' or 'Close'
if isinstance(df.columns, pd.MultiIndex):
    st.warning("MultiIndex columns detected - flattening or selecting 'Close' column.")
    # Flatten columns
    df.columns = ['_'.join(col).strip() for col in df.columns.values]
    st.write(f"Flattened columns: {df.columns}")

# Now check for 'Close' column explicitly
if 'Close' not in df.columns:
    st.error("'Close' column not found in data. Columns available: " + ", ".join(df.columns))
    st.stop()

# Convert columns to numeric safely
price_cols = ['Open', 'High', 'Low', 'Close']
missing_cols = [col for col in price_cols if col not in df.columns]
if missing_cols:
    st.error(f"Missing price columns: {missing_cols}")
    st.stop()

for col in price_cols:
    try:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    except Exception as e:
        st.error(f"Failed to convert column {col} to numeric: {e}")
        st.stop()

df.dropna(subset=price_cols, inplace=True)
df = df.sort_index()
df.index = pd.to_datetime(df.index)

close_series = df['Close']

st.write("Data loaded and cleaned successfully.")
st.write(df.head())
