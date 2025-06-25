import sqlite3

conn = sqlite3.connect("nse.db")
cursor = conn.cursor()

# List all tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()
print("Tables:", tables)

# Check columns in each table
for table in ["company_info", "industry_info"]:
    try:
        cursor.execute(f"PRAGMA table_info({table})")
        cols = cursor.fetchall()
        print(f"\nColumns in {table}:", cols)
    except Exception as e:
        print(f"Error with {table}:", e)
