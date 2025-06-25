# common/sql.py
import pandas as pd
import sqlalchemy as sa
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "nse.db"   # -> project_root/nse.db
ENGINE  = sa.create_engine(f"sqlite:///{DB_PATH}", future=True)

# --- 1. Quick loaders -------------------------------------------------

def load_company_info() -> pd.DataFrame:
    """Entire company_info table (≈ 2 MB)."""
    return pd.read_sql("SELECT * FROM company_info", ENGINE)

def load_industry_info() -> pd.DataFrame:
    """Entire industry_info table."""
    return pd.read_sql("SELECT * FROM industry_info", ENGINE)

def load_master() -> pd.DataFrame:
    """Join the two tables on Symbol, similar to your old merge."""
    sql = """
        SELECT  c.*, i."Big Sectors", i.Industry
        FROM    company_info  AS c
        LEFT JOIN industry_info AS i USING (Symbol)
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
