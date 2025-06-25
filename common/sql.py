# common/sql.py
import pandas as pd
import sqlalchemy as sa

DB_PATH = "nse.db"
ENGINE = sa.create_engine(f"sqlite:///{DB_PATH}", future=True)

def list_tables():
    """Return all table names in the DB (for debugging)."""
    with ENGINE.connect() as conn:
        return [row[0] for row in conn.execute(sa.text(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ))]

def preview(table_name: str, n: int = 5):
    """Preview any table."""
    return pd.read_sql(f"SELECT * FROM {table_name} LIMIT {n}", ENGINE)

def load_master() -> pd.DataFrame:
    """Join DimCompany and FactFundamentals on Symbol."""
    sql = """
        SELECT
            d.Symbol,
            d.CompanyName     AS "Company Name",
            d."Big Sectors",
            d.Industry,
            f.PERatio         AS "PE Ratio",
            f.EPS,
            f.ROE,
            f.ProfitMargin,
            f.DebtToEquity,
            f.MarketCap,
            f.Description     AS "Description"
        FROM DimCompany AS d
        LEFT JOIN FactFundamentals AS f
        ON d.Symbol = f.Symbol
    """
    return pd.read_sql(sql, ENGINE)
