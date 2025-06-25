# common/sql.py
import pandas as pd
import sqlalchemy as sa
from pathlib import Path

import os
db_path = os.path.join(os.path.dirname(__file__), "..", "nse.db")
ENGINE = sa.create_engine(f"sqlite:///{os.path.abspath(db_path)}")



# --- 1. Quick loaders -------------------------------------------------

def load_company_info() -> pd.DataFrame:
    """Entire company_info table (≈ 2 MB)."""
    return pd.read_sql("SELECT * FROM company_info", ENGINE)

def load_industry_info() -> pd.DataFrame:
    """Entire industry_info table."""
    return pd.read_sql("SELECT * FROM industry_info", ENGINE)

 def load_master() -> pd.DataFrame:
    """Join DimCompany and FactFundamentals on Symbol."""
    sql = """
        SELECT
            d.Symbol,
            d.CompanyName AS "Company Name",
            d.Sector      AS "Big Sectors",
            d.Industry,
            f.PERatio     AS "PE Ratio",
            f.EPS,
            f.ROE,
            f.ProfitMargin,
            f.DebtToEquity,
            f.MarketCap
        FROM DimCompany AS d
        LEFT JOIN FactFundamentals AS f ON d.Symbol = f.Symbol
    """
    return pd.read_sql(sql, ENGINE)





# --- 2. Ad-hoc helpers -------------------------------------------------

def get_fundamentals(symbol: str) -> pd.Series:
    """Example: pull one row of fundamentals (extend once you add that table)."""
    sql = "SELECT * FROM company_info WHERE Symbol = :sym"
    return pd.read_sql(sql, ENGINE, params={"sym": symbol}).squeeze()

# --- 3. Utility to run raw SQL (optional) ------------------------------
def run_query(query: str, **params) -> pd.DataFrame:
    return pd.read_sql(sa.text(query), ENGINE, params=params)
