# common/sql.py

import pandas as pd
import sqlalchemy as sa
from pathlib import Path

# Path to your local SQLite DB
DB_PATH = Path("nse.db")

# Create SQLAlchemy engine
ENGINE = sa.create_engine(f"sqlite:///{DB_PATH}", future=True)

def load_master() -> pd.DataFrame:
    """
    Join DimCompany with FactFundamentals on Symbol.
    Returns the full master DataFrame used by the app.
    """
    sql = """
        SELECT
            d.Symbol,
            d.CompanyName AS "Company Name",
            d.Sector AS "Big Sectors",
            d.Industry,
            f.PERatio AS "PE Ratio",
            f.EPS,
            f.ROE,
            f.ProfitMargin,
            f.DebtToEquity,
            f.MarketCap
        FROM DimCompany AS d
        LEFT JOIN FactFundamentals AS f ON d.Symbol = f.Symbol
    """
    return pd.read_sql(sql, ENGINE)

def test_connection() -> list[str]:
    """
    Optional: Returns list of table names in the DB for verification.
    """
    with ENGINE.connect() as conn:
        result = conn.execute(sa.text("SELECT name FROM sqlite_master WHERE type='table';"))
        return [row[0] for row in result]
