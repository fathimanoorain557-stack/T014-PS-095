# PS-095 – Housing Society Maintenance Billing, Dues and Common-Area Cost Allocation Engine — Sample Data Pack

Prepared by 10 SECONDS for Team T014.

## Files

| File | What it holds | Row count |
|---|---|---|
| `society.csv` | Society master: GSTIN, previous-FY collection (for the Rs 20 lakh GST test), bill and due day | 1 data rows |
| `rates.csv` | All rates and thresholds with effective dates (maintenance rate revised from 2026-02-01) | 17 data rows |
| `towers.csv` | 2 towers, 10 floors each, both with lifts | 2 data rows |
| `flats.csv` | 60 flats with area, occupancy at period start, residents, meter flag, parking and owner | 60 data rows |
| `owners.csv` | 60 original owners + 3 buyers who receive flats by transfer | 63 data rows |
| `expenses.csv` | 12 months of common expenses by head (lift AMC per tower; tanker only in short-supply months) | 75 data rows |
| `meter_readings.csv` | Month-end cumulative water meter readings for metered flats (opening reading 2025-10-31) | 598 data rows |
| `commands.txt` | Bill runs, ~500 payments, advance, occupancy declarations, parking complaint, transfers, NDC requests and prints | 584 command lines (excluding comments) |

Row numbers quoted below are 1-based data-row numbers (the header is row 0). Line numbers for `commands.txt` are physical line numbers including comment lines.

## Column reference

Conventions: dates `YYYY-MM-DD`; timestamps `YYYY-MM-DD HH:MM:SS` (24h, IST, no timezone suffix); money in Rs as plain decimals with 2 places (no commas, no symbol); percentages as plain numbers (12.5 means 12.5%); booleans `true`/`false`; IDs uppercase with a fixed prefix. An empty cell means "not applicable" and only appears in columns whose notes say so.

### `society.csv`

| Column | Type | Units / format | Allowed values | Notes |
|---|---|---|---|---|
| society_id | string | SOC-nn | — | — |
| society_name | string | — | — | — |
| city | string | — | — | — |
| gstin | string | 15 chars | — | fake but well-formed |
| prior_fy_collection | decimal | Rs | — | annual collection used for the Rs 20 lakh GST test |
| bill_day | int | day of month | 1 | — |
| due_day | int | day of month | 15 | interest from the next day |

### `rates.csv`

| Column | Type | Units / format | Allowed values | Notes |
|---|---|---|---|---|
| rate_code | string | — | see file | a code may have several rows; use the row with the latest effective_from <= the 1st of the covered month |
| description | string | — | — | — |
| value | decimal | see unit | — | percent values are plain numbers |
| unit | enum | — | Rs_per_sqft, Rs_per_kl, Rs_per_head, Rs_per_slot, Rs_per_month, Rs, percent | — |
| effective_from | date | — | — | — |

### `towers.csv`

| Column | Type | Units / format | Allowed values | Notes |
|---|---|---|---|---|
| tower_id | string | TWR-x | TWR-A, TWR-B | — |
| tower_name | string | — | — | — |
| floors | int | — | — | floors 0 (ground) to 9 |
| has_lift | bool | — | — | — |

### `flats.csv`

| Column | Type | Units / format | Allowed values | Notes |
|---|---|---|---|---|
| flat_id | string | FLT-<tower><floor><nn> | — | e.g. FLT-A001 = Tower A ground floor flat 01 |
| tower_id | string | — | towers.csv | — |
| floor | int | — | 0-9 | 0 = ground floor (excluded from lift AMC) |
| super_builtup_sqft | int | sq ft | — | basis for maintenance, sinking fund, electricity and diesel |
| bedrooms | int | — | 1-4 | — |
| occupancy | enum | — | OWNER, TENANT, VACANT | status at 2025-11-01; later changes come as DECLARE_OCCUPANCY |
| declared_residents | int | persons | — | for per-head water on unmetered flats (and metered flats in a meter-replacement month) |
| has_water_meter | bool | — | — | — |
| covered_slots | int | — | 0-2 | — |
| open_slots | int | — | 0-1 | — |
| owner_id | string | — | owners.csv | owner at period start |
| possession_date | date | — | — | — |

### `owners.csv`

| Column | Type | Units / format | Allowed values | Notes |
|---|---|---|---|---|
| owner_id | string | OWN-nnn | — | — |
| owner_name | string | — | — | — |
| gender | enum | — | M, F | — |
| mobile | string | 10 digits | — | — |
| email | string | — | — | — |

### `expenses.csv`

| Column | Type | Units / format | Allowed values | Notes |
|---|---|---|---|---|
| expense_id | string | EXP-nnnn | — | — |
| expense_month | date | 1st of month | — | month the cost relates to |
| head | enum | — | SECURITY, HOUSEKEEPING, LIFT_AMC, COMMON_ELECTRICITY, GENERATOR_DIESEL, WATER_TANKER | SECURITY and HOUSEKEEPING are funded from maintenance (income statement only); the others are allocated |
| tower_id | string | — | towers.csv | set only for LIFT_AMC (per tower); empty = society-wide |
| amount | decimal | Rs | — | — |
| vendor | string | — | — | — |
| paid_date | date | — | — | — |

### `meter_readings.csv`

| Column | Type | Units / format | Allowed values | Notes |
|---|---|---|---|---|
| reading_id | string | MR-nnnn | — | — |
| flat_id | string | — | flats.csv | metered flats only |
| reading_date | date | — | month end | consumption for month M = reading at end of M - reading at end of M-1 |
| reading_kl | decimal | kilolitres, 1 decimal | — | cumulative meter value |
| remarks | string | — | meter replaced | optional; empty for normal readings |

## Command file format

`commands.txt` holds one command per line in the form `COMMAND_NAME|arg1|arg2|...`. Commands must be processed strictly in file order. Lines starting with `#` are comments and blank lines are ignored. Every argument is always present (no empty fields). Every command used in this pack:

| Command | Arguments (in order) | Meaning |
|---|---|---|
| `GENERATE_BILLS` | `covered_month|bill_date` | Bill every flat for covered_month (1st of month); bill dated bill_date (1st of next month), due on the 15th |
| `DECLARE_OCCUPANCY` | `flat_id|status|effective_date|declared_residents` | Occupancy change OWNER/TENANT/VACANT from effective_date; VACANT counts for a month only if in force for the whole month |
| `PARKING_COMPLAINT` | `complaint_id|flat_id|complaint_date` | Second car without a slot: Rs 1,000/month from the complaint month |
| `PAYMENT` | `payment_id|flat_id|payment_ts|amount|mode` | Payment (UPI/NEFT/CHEQUE); settles interest first, then oldest principal; surplus becomes advance |
| `ADVANCE` | `payment_id|flat_id|payment_ts|first_month|months|amount` | Advance for `months` months of maintenance from first_month at 3% discount; consumed month by month |
| `TRANSFER_FEE` | `payment_id|flat_id|payment_ts|amount` | Rs 25,000 transfer fee needed for a no-dues certificate |
| `ISSUE_NDC` | `flat_id|request_date` | Issue the no-dues certificate if outstanding (incl. interest and legal) is zero and the fee is paid; else REFUSED with reason |
| `TRANSFER` | `transfer_id|flat_id|new_owner_id|transfer_date` | Ownership transfer; dues carry over unless an NDC was issued before this date |
| `PRINT_BILL` | `flat_id|covered_month` | Print one monthly bill with line items |
| `PRINT_LEDGER` | `flat_id|as_of_date` | Print the flat ledger up to the date |
| `PRINT_DEFAULTERS` | `as_of_date` | Print flats in REMINDER/NOTICE/LEGAL with arrears months |
| `PRINT_INCOME_STATEMENT` | `from_month|to_month` | Society income (billed by head) vs expenses for the covered months |

## Planted scenarios

Every edge case in the brief, mapped to the exact record where it occurs, followed by extra traps.

- **EC-01 Flat declared vacant from the 2nd of the month - not vacant for billing**
  - FLT-A802: declared VACANT effective 2026-03-02 (the 2nd) — NOT vacant for March 2026 (full maintenance); vacant from the next full month — `commands.txt line 141`
- **EC-02 Maintenance exactly Rs 7,500 - no GST**
  - FLT-B402: 2,000 sq ft owner-occupied; from 2026-02-01 maintenance = 2,000 x 3.75 = Rs 7,500.00 exactly — no GST (threshold is 'exceeds') — `flats.csv row 44 (flat_id=FLT-B402)`
- **EC-03 Water meter reading lower than previous (meter replaced) - treat consumption as per-head for that month**
  - FLT-A501: reading on 2026-06-30 is 3.1 kl, lower than the previous month-end reading (meter replaced) — bill water for that month per head (declared residents x Rs 150); the next month is metered again from the new meter's reading — `meter_readings.csv row 165 (reading_id=MR-0165)`
- **EC-04 Payment on the 15th at 23:59 vs 16th - interest start**
  - FLT-B501: pays the 2026-09-01 bill at 2026-09-15 23:59:00 (due date, 23:59) — on time, no interest — `commands.txt line 460`
  - FLT-B601: pays the 2026-09-01 bill at 2026-09-16 00:00:30 — after the due date: 1 day of interest at 18% p.a. (from the 16th) is settled first from this payment — `commands.txt line 461`
- **EC-05 Arrears dropping to exactly 2 months after a partial payment**
  - FLT-A601: bills dated 2026-04-01, 2026-05-01, 2026-06-01 unpaid → REMINDER, then NOTICE (3 months; club/gym suspended); the Rs 14,600 payment on 2026-07-04 clears all accrued interest and the oldest bill only, leaving exactly 2 past-due bills unsettled — state goes NOTICE → REMINDER, not NORMAL — `commands.txt line 330`
- **EC-06 Advance of 12 months when rates change in month 4**
  - FLT-A801: ADVANCE of Rs 70,684 on 2025-11-06 = 12 x (1735 sq ft x Rs 3.50) less 3% for maintenance Nov-2025..Oct-2026; the rate rises to Rs 3.75 from 2026-02-01 (month 4) — the covered months are NOT re-billed for the difference; other heads are billed normally — `commands.txt line 3`
- **EC-07 Ground-floor flat on a building with lift - excluded from AMC**
  - FLT-A001: ground-floor flat in TWR-A (has_lift=true) — excluded from the LIFT_AMC split; TWR-A's lift AMC is shared equally by its 27 flats on floors 1-9 — `flats.csv row 1 (flat_id=FLT-A001)`
- **EC-08 Transfer recorded the day before no-dues certificate issuance**
  - FLT-B202: TRANSFER to OWN-063 recorded 2026-09-14, ISSUE_NDC requested 2026-09-15 (the next day) with the 2026-09-01 bill still unpaid — certificate REFUSED and, because no certificate was issued before the transfer, the old owner's dues carry over to the new owner — `commands.txt line 457; commands.txt line 459`
- **Extra traps (not in the brief, but realistic):**
  - FLT-B802: declared VACANT effective 2026-07-01 (the 1st) — vacant for the whole of July 2026: 50% maintenance, 100% sinking fund, and excluded from the tanker split if a tanker month — `commands.txt line 318`
  - FLT-B801: 2285 sq ft — maintenance above Rs 7,500 in every month, so 18% GST on the FULL maintenance amount (sinking fund, water, electricity untaxed) — `flats.csv row 55 (flat_id=FLT-B801)`
  - FLT-B602: complaint on 2026-04-18 about a second car without a slot — Rs 1,000 unauthorised parking from the April 2026 bill (the complaint month) onward, not pro-rated — `commands.txt line 228`
  - Duplicate PAYMENT for FLT-A001 (same payment_id, identical line) repeated 2 minutes later — reject the second (payment_id already recorded) — `commands.txt line 269; commands.txt line 270`
  - PAYMENT for FLT-C101 — no such flat (there is no Tower C); must be REJECTED and not posted anywhere — `commands.txt line 250`
  - FLT-A601: Rs 52,800 clears everything including interest — REMINDER → NORMAL; surplus carried as advance — `commands.txt line 385`
  - FLT-A602: six bills (dated 2026-01-01..2026-06-01) unpaid — LEGAL on 2026-06-16 with a Rs 2,500 legal charge; the Rs 56,800 cheque on 2026-07-10 brings arrears below 2 months → NORMAL, but the balance (including the legal charge under any allocation order) remains payable — `commands.txt line 346`
  - FLT-A602: ISSUE_NDC on 2026-07-20 must be REFUSED — dues outstanding and no transfer fee paid — `commands.txt line 361`
  - FLT-A602: Rs 52,000 full clearance (incl. legal charge and interest) + Rs 25,000 transfer fee; NDC issued 2026-10-05 BEFORE the 2026-10-08 transfer — nothing carries over to OWN-061 (surplus stays with the flat as advance) — `commands.txt line 469; commands.txt line 470; commands.txt line 480; commands.txt line 492`
  - FLT-A301: Rs 24,249 on 2026-03-06 = current dues + the next bill less about Rs 60 — the next bill after credits is under Rs 100 and must still be issued — `commands.txt line 155`
  - FLT-B902: Rs 23,185 on 2026-03-08 = current dues + next bill + about Rs 3,000 — the next bill is negative after credits: issue it at zero payable and carry the credit forward as advance — `commands.txt line 164`

## What is NOT in this pack

Expected outputs are not provided for this set. Validate your engine with your own test suite against the rules in your brief (BR-01 … BR-nn). A separate hidden input set with the same schema will be used at final evaluation; outputs are compared field-for-field, so follow the column formats above exactly in your own output.

## Output format expected at evaluation

Produce these CSV files (header row, same conventions as above, rows sorted as stated). Where the brief is silent on a format detail the choice below is binding for evaluation.

### `bills.csv`

One row per flat per covered month (720 rows), sorted by covered_month then flat_id.

Columns, in order: `bill_id`, `flat_id`, `owner_id`, `covered_month`, `bill_date`, `due_date`, `billing_status`, `maintenance`, `sinking_fund`, `non_occupancy`, `water`, `water_basis`, `common_electricity`, `generator_diesel`, `lift_amc`, `water_tanker`, `parking`, `unauthorised_parking`, `gst`, `advance_applied`, `rounding`, `bill_total`

### `ledger.csv`

One row per ledger posting in date order per flat (bills, interest, legal charge, payments, advance, transfer fee).

Columns, in order: `flat_id`, `posting_date`, `entry_type`, `reference`, `debit`, `credit`, `principal_balance`, `interest_balance`, `legal_balance`, `advance_balance`

### `defaulter_timeline.csv`

One row per escalation state change.

Columns, in order: `flat_id`, `change_date`, `from_state`, `to_state`, `arrears_months`, `amenities_suspended`, `legal_charge_added`

### `settlements.csv`

One row per ISSUE_NDC request.

Columns, in order: `flat_id`, `request_date`, `outstanding_principal`, `outstanding_interest`, `outstanding_legal`, `transfer_fee_paid`, `decision`, `reason`, `dues_carried_to_owner_id`

### `income_statement.csv`

One row per head for the PRINT_INCOME_STATEMENT period.

Columns, in order: `head`, `billed`, `collected`, `expense`, `surplus`

Binding choices: `billing_status` OWNER, TENANT or VACANT (as used for that month); `water_basis` METERED or PER_HEAD; interest = overdue principal x 18% / 365 per day from the 16th, rounded to paise per posting; `arrears_months` = number of past-due bills not fully settled; escalation states NORMAL, REMINDER, NOTICE, LEGAL; allocations (area share, equal shares) are rounded to paise per flat before the bill total is rounded to the rupee (half up); `decision` ISSUED or REFUSED; bill_id BILL-<flat_id>-<YYYY-MM>.
