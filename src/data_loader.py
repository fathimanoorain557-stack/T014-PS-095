
import csv
from pathlib import Path

# Find the main project folder
PROJECT_DIR = Path(__file__).resolve().parent.parent

# Find the sample data folder
DATA_DIR = PROJECT_DIR / "T014-PS-095-sample-data"


# STEP 1: Load all CSV files
def load_data():

    files = {
        "society": "society.csv",
        "rates": "rates.csv",
        "towers": "towers.csv",
        "flats": "flats.csv",
        "owners": "owners.csv",
        "expenses": "expenses.csv",
        "meter_readings": "meter_readings.csv"
    }

    data = {}

    for name, filename in files.items():

        file_path = DATA_DIR / filename

        if not file_path.exists():
            raise FileNotFoundError(
                f"File not found: {filename}"
            )

        with open(
            file_path,
            "r",
            encoding="utf-8-sig",
            newline=""
        ) as file:

            reader = csv.DictReader(file)
            data[name] = list(reader)

    return data


# STEP 2: Load commands from commands.txt
def load_commands():

    file_path = DATA_DIR / "commands.txt"

    if not file_path.exists():
        raise FileNotFoundError("commands.txt not found")

    commands = []

    with open(
        file_path,
        "r",
        encoding="utf-8-sig"
    ) as file:

        for line in file:

            line = line.strip()

            # Ignore blank lines and comments
            if line and not line.startswith("#"):
                commands.append(line)

    return commands


# STEP 3: Display the number of records
def validate_data(data, commands):

    print("\nDATA LOADING SUCCESSFUL!")

    print("\nNUMBER OF RECORDS:")

    for name, records in data.items():
        print(f"{name}: {len(records)}")

    print(f"commands: {len(commands)}")


# STEP 4: Inspect CSV columns and sample records
def inspect_data(data):

    print("\n" + "=" * 45)
    print("FLATS CSV DETAILS")
    print("=" * 45)

    print("\nFlats CSV columns:")
    print(list(data["flats"][0].keys()))

    print("\nFirst flat record:")
    print(data["flats"][0])

    print("\n" + "=" * 45)
    print("RATES CSV DETAILS")
    print("=" * 45)

    print("\nRates CSV columns:")
    print(list(data["rates"][0].keys()))

    print("\nFirst rate record:")
    print(data["rates"][0])


# STEP 5: Run the program
if __name__ == "__main__":

    data = load_data()

    commands = load_commands()

    validate_data(data, commands)

    inspect_data(data)
