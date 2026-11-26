# DECISION LOG
## PS-095 – Housing Society Maintenance Billing, Dues and Common-Area Cost Allocation Engine

**Team ID:** T014  
**Institute:** Atria Institute of Technology  
**Department:** Computer Science and Data Science Engineering  

### Team Members
1. Dhanush T M – 1AT24CD028
2. Fathima Noorain – 1AT24CD029

---

## 1. Technology Selection

**Decision:** Python was selected as the programming language.

**Reason:** Python provides readable syntax, built-in CSV processing, decimal arithmetic and unit-testing support. It is suitable for implementing the billing and financial calculation requirements.

**Decision:** CSV files were selected for input and output data.

**Reason:** CSV files are simple to maintain, easy to inspect and suitable for structured records such as flats, owners, expenses, rates and payments.

**Decision:** Python standard-library modules were preferred.

**Reason:** The application can run without installing additional third-party packages, making it easier to execute on another computer.

## 2. Application Architecture

**Decision:** The application was divided into separate modules.

- `main.py` handles application execution and command processing.
- `src/data_loader.py` handles loading and validating input data.
- `src/billing.py` contains billing and financial calculation logic.

**Reason:** Separating responsibilities makes the application easier to understand, maintain, test and extend.

## 3. Financial Precision

**Decision:** Python's `Decimal` type is used for financial calculations instead of relying on ordinary floating-point arithmetic.

**Reason:** Maintenance bills, taxes, payments, interest and expense allocations require accurate monetary values. Decimal arithmetic helps avoid common floating-point precision errors.

**Decision:** Monetary calculations use defined rounding rules.

**Reason:** Consistent rounding is necessary to generate understandable bills and ensure allocated amounts reconcile with the original expense totals.

## 4. Configurable Billing Rates

**Decision:** Maintenance and other applicable rates are stored in input data rather than being fixed throughout the calculation code.

**Reason:** This allows rates to change over time and makes it easier to maintain the billing rules.

The sample configuration includes:

- Maintenance rate of ₹3.50 per square foot from November 2025.
- Maintenance rate of ₹3.75 per square foot from February 2026.
- Sinking fund of ₹0.50 per square foot.

The applicable rate is selected according to the billing month and effective date.

## 5. Occupancy-Based Charges

**Decision:** Occupancy status is considered while calculating maintenance and applicable charges.

The implemented sample rules include:

- Non-occupancy charge of 10% of maintenance for applicable tenant-occupied flats.
- Vacant-flat maintenance at 50% of the normal maintenance component.
- Sinking fund continues to be charged according to the applicable rule.
- Vacancy effective dates are considered when determining whether a flat qualifies as vacant for a billing month.

**Reason:** Different occupancy conditions require different billing treatment.

## 6. Water Charge Calculation

**Decision:** Water charges support both metered and unmetered calculation methods.

- Metered water: ₹25 per kilolitre.
- Unmetered water: ₹150 per declared resident.
- A meter-replacement fallback is used where applicable.

**Reason:** Housing societies may have different water-meter availability and recording conditions. Supporting both methods allows the application to handle these cases.

## 7. Common-Area Expense Allocation

**Decision:** Common expenses are allocated according to the applicable allocation basis.

Examples include:

- Common electricity and generator diesel: area-based allocation.
- Lift AMC: equal allocation among eligible flats on floors above the ground floor.
- Water tanker expenses: allocation among eligible occupied flats during applicable shortage months.

**Reason:** Different shared expenses require different allocation methods. The allocation rules are designed to distribute costs consistently and reconcile the allocated total with the recorded expense.

## 8. GST Calculation

**Decision:** GST is applied according to the configured society collection threshold and flat-level maintenance condition.

The sample rules use an annual society collection threshold of ₹20 lakh and a monthly maintenance threshold of ₹7,500. The configured GST rate is 18% when the applicable conditions are met.

**Reason:** Tax calculation must follow the configured business rules rather than being applied indiscriminately to every flat.

## 9. Payment Allocation

**Decision:** Payments are applied first to outstanding interest and then to the oldest outstanding bill principal.

**Reason:** This provides a consistent payment-allocation order and makes it possible to track how each payment reduces outstanding dues.

**Decision:** Excess payments are carried forward as advance credit.

**Reason:** Any amount remaining after settling applicable dues should be available for future bills rather than being lost.

## 10. Interest Calculation

**Decision:** Delayed payments attract interest at 18% per annum after the due date.

The sample billing configuration uses the 15th day of the month as the due date. Interest begins after the due date.

**Reason:** Daily interest calculation provides a consistent way to determine overdue charges based on the actual delay.

## 11. Defaulter Management

**Decision:** The application maintains a defaulter timeline and records changes in defaulter status.

The configured sample rules include:

- Two months of arrears: reminder.
- Three months of arrears: notice and amenities suspension status.
- Six months of arrears: legal escalation and applicable legal charge.

**Reason:** A timeline makes it easier for society administrators to understand the history of overdue payments and escalation.

## 12. Advance Payment

**Decision:** The application supports advance maintenance payments.

The sample data includes a 12-month advance payment with a 3% discount on the eligible maintenance component.

**Reason:** Advance payments need to be tracked separately and applied to the appropriate billing months. Applying the discount month by month helps maintain the billing calculation.

## 13. NDC and Ownership Transfer

**Decision:** No-Dues Certificate processing checks outstanding financial obligations before issuing the certificate.

The configured sample transfer fee is ₹25,000.

**Decision:** If dues remain outstanding when an ownership transfer is processed without an issued NDC, the dues are carried forward according to the transfer rules.

**Reason:** These checks help preserve the society's outstanding financial records during ownership changes.

## 14. Command Processing

**Decision:** Commands are processed in the order in which they appear in `commands.txt`.

**Reason:** The order of operations matters. For example, payments, billing, advance adjustments, NDC requests and ownership transfers can affect subsequent financial balances.

## 15. Output Reports

**Decision:** The application generates separate CSV reports.

- `bills.csv` – monthly bill details.
- `ledger.csv` – financial transactions and balances.
- `defaulter_timeline.csv` – defaulter status changes.
- `settlements.csv` – NDC and settlement records.
- `income_statement.csv` – income and expense summary.

**Reason:** Separate reports make the generated information easier to inspect, verify and use for society accounting.

## 16. Testing Strategy

**Decision:** Python's built-in `unittest` framework is used for automated testing.

**Reason:** It allows important billing calculations, validation rules and charge-allocation behaviour to be tested without requiring an external testing framework.

The current test suite contains 23 unit tests across:

- `tests/test_billing.py`
- `tests/test_charges.py`

The tests cover flat validation, applicable rates, interest, payment validation, rounding, water charges, parking, GST, expense allocation, advance payments and other billing rules.

The test command is:

```powershell
python -m unittest discover -s tests -v
```

**Latest recorded test result:** 23 tests passed successfully.

## 17. Final Design Approach

The project uses a modular Python application, CSV-based data handling, accurate decimal calculations, configurable billing rules and automated unit testing.

The decisions above were made to support maintainability, reliable financial calculations, clear transaction records and practical execution on another computer.

---

**Project:** PS-095  
**Team:** T014  
**Document:** Decision Log