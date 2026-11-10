
import csv
import re
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
INPUT_DIR = BASE_DIR / "input"
OUTPUT_DIR = BASE_DIR / "outputs"
DATABASE_DIR = BASE_DIR / "database"
DB_PATH = DATABASE_DIR / "apartment.db"


def get_table_name(filename):
    """Convert a CSV filename into a safe SQLite table name."""
    return re.sub(r"\W+", "_", Path(filename).stem)


def quote_identifier(name):
    """Safely quote a SQLite table or column name."""
    return '"' + name.replace('"', '""') + '"'


def import_csv(csv_path):
    """Import one CSV file into an SQLite table."""
    if not csv_path.exists():
        return 0

    with open(csv_path, "r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        columns = reader.fieldnames

        if not columns:
            return 0

        rows = list(reader)

    table_name = get_table_name(csv_path.name)
    table_sql = quote_identifier(table_name)

    DATABASE_DIR.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(DB_PATH) as connection:
        cursor = connection.cursor()

        column_sql = ", ".join(
            f"{quote_identifier(column)} TEXT"
            for column in columns
        )

        cursor.execute(f"DROP TABLE IF EXISTS {table_sql}")
        cursor.execute(
            f"CREATE TABLE {table_sql} ({column_sql})"
        )

        if rows:
            placeholders = ", ".join("?" for column in columns)

            insert_sql = (
                f"INSERT INTO {table_sql} VALUES ({placeholders})"
            )

            values = [
                [row.get(column, "") or "" for column in columns]
                for row in rows
            ]

            cursor.executemany(insert_sql, values)

    return len(rows)


def import_all_csvs():
    """Import every CSV dataset from input and outputs."""
    total_files = 0
    total_records = 0

    for folder in (INPUT_DIR, OUTPUT_DIR):
        if not folder.exists():
            continue

        for csv_path in sorted(folder.glob("*.csv")):
            count = import_csv(csv_path)
            total_files += 1
            total_records += count

            print(f"Imported {csv_path.name}: {count} records")

    print("\nDATABASE IMPORT COMPLETED")
    print("-------------------------")
    print("CSV files imported:", total_files)
    print("Total records imported:", total_records)
    print("Database location:", DB_PATH)
def read_table(table_name):
    """Read all records from an SQLite table."""
    allowed_tables = {
        "flats", "towers", "owners", "expenses",
        "monthly_bills", "payments", "flat_ledger",
        "meter_readings", "rates", "ndc_status",
        "ownership_history", "resale_settlements",
        "defaulters_2026_06_20",
        "defaulters_2026_11_03"
    }

    if table_name not in allowed_tables:
        raise ValueError("Invalid database table")

    with sqlite3.connect(DB_PATH) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            f'SELECT * FROM "{table_name}"'
        ).fetchall()

    return [dict(row) for row in rows]

if __name__ == "__main__":
    import_all_csvs()
