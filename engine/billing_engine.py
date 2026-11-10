
import csv
from pathlib import Path


# Project folder location
BASE_DIR = Path(__file__).resolve().parent.parent
INPUT_DIR = BASE_DIR / "input"


# Load CSV files
def load_csv(filename):
    file_path = INPUT_DIR / filename

    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    with open(file_path, "r", encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


# Load commands
def load_commands():
    file_path = INPUT_DIR / "commands.txt"

    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    with open(file_path, "r", encoding="utf-8-sig") as file:
        return [
            line.strip()
            for line in file
            if line.strip() and not line.strip().startswith("#")
        ]


# Main program
def main():

    print("=" * 55)
    print("APARTMENT MAINTENANCE BILLING SYSTEM")
    print("=" * 55)

    # Load all input files
    society = load_csv("society.csv")
    rates = load_csv("rates.csv")
    towers = load_csv("towers.csv")
    flats = load_csv("flats.csv")
    owners = load_csv("owners.csv")
    expenses = load_csv("expenses.csv")
    meter_readings = load_csv("meter_readings.csv")
    commands = load_commands()

    # Display record counts
    print("\nDATA LOADED SUCCESSFULLY")
    print("-" * 55)

    print("Society records:", len(society))
    print("Rate records:", len(rates))
    print("Tower records:", len(towers))
    print("Flat records:", len(flats))
    print("Owner records:", len(owners))
    print("Expense records:", len(expenses))
    print("Meter reading records:", len(meter_readings))
    print("Commands:", len(commands))

    # Display column names and first records
    datasets = {
        "Society": society,
        "Rates": rates,
        "Towers": towers,
        "Flats": flats,
        "Owners": owners,
        "Expenses": expenses,
        "Meter Readings": meter_readings
    }

    print("\nCSV COLUMN DETAILS")
    print("-" * 55)

    for name, records in datasets.items():
        print(f"\n{name}:")

        if records:
            print("Columns:", list(records[0].keys()))
            print("First record:", records[0])
        else:
            print("No records found")

    # Display all rate records
    print("\nALL RATE RECORDS")
    print("-" * 55)

    for record in rates:
        print(record)

    print("\nALL SOCIETY RECORDS")
    print("-" * 55)

    for record in society:
        print(record)

    print("\nAll input files loaded successfully!")
    print("=" * 55)


if __name__ == "__main__":
    main()
