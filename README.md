# PS-095 – Housing Society Maintenance Billing, Dues and Common-Area Cost Allocation Engine

**Team ID:** T014  
**Project Code:** PS-095  
**Institute:** Atria Institute of Technology, Bengaluru  
**Department:** Computer Science and Data Science Engineering  
**Semester:** 5th Semester – CSDS A

## Team Members

1. **Dhanush T M** – 1AT24CD028
2. **Fathima Noorain** – 1AT24CD029

---

## 1. Project Overview

The Housing Society Maintenance Billing, Dues and Common-Area Cost Allocation Engine is a Python-based command-line application designed to automate apartment maintenance billing and financial management.

The system processes housing society information, flat details, owner records, maintenance rates, expenses, water meter readings and payment instructions from CSV files.

It calculates monthly maintenance bills, allocates common-area expenses, tracks payments and outstanding dues, applies interest on delayed payments, manages advance payments and supports No-Dues Certificates (NDC) and ownership transfers.

The application generates structured CSV reports for billing, financial transactions, defaulter tracking, settlements and income statements.

## 2. Objectives

- Automate monthly apartment maintenance billing.
- Calculate charges using configurable rates and applicable business rules.
- Allocate common-area expenses among eligible flats.
- Track payments, outstanding balances and advance credits.
- Calculate interest on overdue payments.
- Identify defaulters and record changes in defaulter status.
- Support ownership transfers and NDC processing.
- Generate detailed financial reports for society administration.

## 3. Technologies Used

| Technology | Purpose |
|---|---|
| Python | Application development |
| CSV | Input data and output reports |
| Decimal | Accurate financial calculations |
| unittest | Automated testing |
| PowerShell / VS Code | Development and execution |

The project uses Python standard-library modules and does not require external packages.

## 4. Project Structure

```text
T014-PS-095/
│
├── main.py
├── README.md
├── DECISION_LOG.md
├── Design_Document.pdf
│
├── src/
│   ├── data_loader.py
│   └── billing.py
│
├── tests/
│
├── T014-PS-095-Data/
│   ├── society.csv
│   ├── rates.csv
│   ├── towers.csv
│   ├── flats.csv
│   ├── owners.csv
│   ├── expenses.csv
│   ├── meter_readings.csv
│   ├── commands.txt
│   └── README.md
│
└── outputs/
    ├── bills.csv
    ├── ledger.csv
    ├── defaulter_timeline.csv
    ├── settlements.csv
    └── income_statement.csv
```

## 5. Main Features

### 5.1 Maintenance Billing

Calculates monthly maintenance using flat area and the applicable maintenance rate.

### 5.2 Additional Charges

Calculates sinking fund, water charges, parking charges, non-occupancy charges and other applicable fees.

### 5.3 Common-Area Expense Allocation

Allocates common electricity, generator diesel, lift maintenance and tanker expenses according to the applicable allocation rules.

### 5.4 GST Calculation

Applies GST according to the configured collection threshold and applicable billing conditions.

### 5.5 Payment Management

Records payments, applies them against interest and outstanding principal, and carries excess payments forward as advance credits.

### 5.6 Interest and Defaulter Tracking

Calculates overdue interest and tracks changes in defaulter status.

### 5.7 Advance Payments

Supports advance maintenance payments and applicable discount rules.

### 5.8 NDC and Ownership Transfer

Processes No-Dues Certificates and ownership transfers while handling outstanding dues and transfer fees.

### 5.9 Report Generation

Generates detailed CSV reports for bills, ledger entries, defaulter timelines, settlements and income statements.

## 6. Input Data

The application reads its sample data from the `T014-PS-095-Data` directory.

| File | Description |
|---|---|
| society.csv | Society-level information and configuration |
| rates.csv | Applicable maintenance and charge rates |
| towers.csv | Tower information |
| flats.csv | Flat details, area and occupancy information |
| owners.csv | Owner information |
| expenses.csv | Society expense records |
| meter_readings.csv | Water meter readings |
| commands.txt | Payment, billing, transfer and other processing instructions |

## 7. Requirements

- Python 3 installed on the system.
- The project folder downloaded and extracted.
- A terminal such as PowerShell or the VS Code terminal.

No additional Python packages are required.

## 8. How to Run the Project

### Step 1: Open the project directory

Open PowerShell or the VS Code terminal and navigate to the project folder:

```powershell
cd T014-PS-095
```

### Step 2: Run the application

```powershell
python main.py
```

The program loads the input data, processes the commands, performs billing and financial calculations, and generates the output reports.

### Step 3: Run automated tests

```powershell
python -m unittest discover -s tests -v
```

The test suite checks important billing calculations, validation rules and charge-allocation behaviour.

## 9. Generated Output Files

| Output file | Description |
|---|---|
| bills.csv | Monthly bills and charge details |
| ledger.csv | Financial transactions and balances |
| defaulter_timeline.csv | Defaulter status changes |
| settlements.csv | NDC and settlement records |
| income_statement.csv | Income and expense summary |

The output files are stored in the `outputs` directory.

## 10. Testing

The project includes automated unit tests using Python's `unittest` framework.

The current test suite contains 23 tests covering billing calculations, charge calculations, validation, interest, water charges, parking, GST, expense allocation and other important rules.

**Latest test result:** 23 tests passed successfully.

Run the tests using:

```powershell
python -m unittest discover -s tests -v
```

## 11. Expected Execution

On successful execution, the application displays processing information in the terminal and generates the required CSV reports.

The sample dataset contains 60 flats and commands covering billing, payments, advance payments, NDC requests, ownership transfers and validation scenarios.

## 12. Design Documentation

The detailed system design, architecture, modules, processing flow, business rules, data handling and testing approach are documented in:

**Design_Document.pdf**

## 13. Demo Video

Watch our project demonstration:

[PS-095 – Demo Video](https://drive.google.com/file/d/1Enr522c_acVDjQ96Gaye5_vcY0Efs5HM/view?usp=drivesdk)

## 14. Conclusion

The project provides an automated approach to housing society maintenance billing and financial management. It combines configurable billing rules, common-area expense allocation, payment tracking, interest calculation, defaulter monitoring and report generation in one Python application.

It aims to improve calculation accuracy, transparency and efficiency in routine housing society accounting operations.