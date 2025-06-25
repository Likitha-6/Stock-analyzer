# bootstrap_db.py
# ------------------------------------------------------------
# Create/refresh SQLite database nse.db with two tables:
#   • DimCompany        (static listing info from CSV)
#   • FactFundamentals  (latest fundamentals from yfinance)
# ------------------------------------------------------------
import pandas as pd
import yfinance as yf
import sqlalchemy as sa
from tqdm import tqdm
from pathlib import Path

# ------------------------------------------------------------
# Config – edit paths if your CSV files live elsewhere
# ------------------------------------------------------------
CSV_COMPANY   = "nse_stocks_.csv"                   # uploaded file #1
CSV_INDUSTRY  = "nse_stocks_with industries.csv"    # uploaded file #2
DB_PATH       = "nse.db"                            # output SQLite

engine = sa.create_engine(f"sqlite:///{DB_PATH}", future=True, echo=False)

# ------------------------------------------------------------
# 1) DimCompany  (Symbol, CompanyName, Sector, Industry)
# ------------------------------------------------------------
df_company  = pd.read_csv(CSV_COMPANY)
df_industry = pd.read_csv(CSV_INDUSTRY)[["Symbol", "Big Sectors", "Industry"]]

dim = (
    df_company
      .rename(columns={"Company Name": "CompanyName"})
      [["Symbol", "CompanyName"]]
      .merge(df_industry, on="Symbol", how="left")
)
dim.to_sql("DimCompany", engine, if_exists="replace", index=False)

# ------------------------------------------------------------
# 2) FactFundamentals  (latest yfinance snapshot)
# ------------------------------------------------------------
symbols = dim["Symbol"].dropna().unique()
rows    = []

print("⬇️  Pulling fundamentals from yfinance (this may take a while)…")
for sym in tqdm(symbols, desc="Fetching"):
    try:
        info = yf.Ticker(f"{sym}.NS").info
    except Exception:
        info = {}
    rows.append({
        "Symbol":        sym,
        "PERatio":       info.get("trailingPE"),
        "EPS":           info.get("trailingEps"),
        "ROE":           info.get("returnOnEquity"),
        "ProfitMargin":  info.get("profitMargins"),
        "DebtToEquity":  info.get("debtToEquity"),
        "MarketCap":     info.get("marketCap"),
    })

pd.DataFrame(rows).to_sql("FactFundamentals", engine, if_exists="replace", index=False)

print(f"✅  Seeded {len(dim):,} companies into {DB_PATH}")
