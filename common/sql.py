# common/sql.py
# ------------------------------------------------------------------
# Tiny data-access layer for your Streamlit app.
# ------------------------------------------------------------------
import pandas as pd
import sqlalchemy as sa
import os
from pathlib import Path

# ------------------------------------------------------------------
# 1. Locate database  (always absolute path)
# ------------------------------------------------------------------
_DB_NAME = "nse.db"
_DB_PATH = Path(__file__).resolve().parent.parent / _DB_NAME   # project_root/nse.db
_ENGINE  = sa.create_engine(f"sqlite:///{_DB_PATH}", future=True)

print(f"🔗  SQLAlchemy opening DB at: {_DB_PATH}")

# ------------------------------------------------------------------
# 2. Public helpers
# ------------------------------------------------------------------
def load_master() -> pd.DataFrame:
    """
    Return the main dataset used by Sector/Fundamentals pages.
    Joins DimCompany (listing info) with FactFundamentals (latest metrics).
    """
    sql = """
        SELECT
            d.Symbol,
            d.CompanyName           AS "Company Name",
            d."Big Sectors"         AS "Big Sectors",
            d.Industry,
            f.PERatio               AS "PE Ratio",
            f.EPS,
            f.ROE,
            f.ProfitMargin,
            f.DebtToEquity,
            f.MarketCap
        FROM DimCompany AS d
        LEFT JOIN FactFundamentals AS f
          ON d.Symbol = f.Symbol
    """
    return pd.read_sql(sql, _ENGINE)


def list_tables() -> list[str]:
    """Return a simple list of table names present in the DB."""
    with _ENGINE.connect() as conn:
        rows = conn.execute(sa.text(
            "SELECT name FROM sqlite_master WHERE type='table';"
        ))
        return [r[0] for r in rows]


def run_sql(query: str, **params) -> pd.DataFrame:
    """Run an arbitrary SQL SELECT and return a DataFrame (for ad-hoc use)."""
    return pd.read_sql(sa.text(query), _ENGINE, params=params)
