# bootstrap_db.py
import pandas as pd
import yfinance as yf
import sqlalchemy as sa
from pathlib import Path
from tqdm import tqdm

DB_PATH = "nse.db"

# 1) Build an engine (SQLite URL = "sqlite:///path")
engine = sa.create_engine(f"sqlite:///{DB_PATH}", echo=False, future=True)

# 2) Read your existing CSV of NSE tickers
master_df = pd.read_csv("nse_stock_big_sectors.csv")   # adapt path if needed
symbols = master_df["Symbol"].dropna().unique()

# 3) Write DimCompany (static lookup table)
dim = master_df.rename(columns={
    "Company Name": "CompanyName",
    "Big Sectors":  "Sector"
})[["Symbol", "CompanyName", "Sector", "Industry"]]
dim.to_sql("DimCompany", engine, if_exists="replace", index=False)

# 4) Pull fundamentals from yfinance
rows = []
for sym in tqdm(symbols, desc="Fetching fundamentals"):
    try:
        info = yf.Ticker(f"{sym}.NS").info
    except Exception:
        info = {}
    rows.append({
        "Symbol":       sym,
        "PERatio":      info.get("trailingPE"),
        "EPS":          info.get("trailingEps"),
        "ROE":          info.get("returnOnEquity"),
        "ProfitMargin": info.get("profitMargins"),
        "DebtToEquity": info.get("debtToEquity"),
        "MarketCap":    info.get("marketCap"),
    })

fact = pd.DataFrame(rows)
fact.to_sql("FactFundamentals", engine, if_exists="replace", index=False)

print(f"✅  Seeded {len(dim)} companies into {DB_PATH}")
