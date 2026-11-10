
# T014-PS-095 – Apartment Maintenance Management System

<p align="center">
  <strong>A Web-Based Apartment Maintenance and Billing Management Solution</strong>
</p>

<p align="center">
  <a href="https://t014-ps-095-1.onrender.com">🌐 Live Website</a> |
  <a href="https://github.com/fathimanoorain557-stack/T014-PS-095">💻 GitHub Repository</a>
</p>

---

## 1. Project Overview

The **Apartment Maintenance Management System** is a Python-based web application developed to simplify and automate apartment maintenance activities.

The system helps apartment administrators manage maintenance billing, resident information, payments, outstanding dues, defaulters, water consumption and ownership transfers through a centralized web dashboard.

It provides an organized approach to apartment financial management, reduces manual calculations and helps maintain accurate records.

**Project ID:** T014-PS-095

## 2. Project Objectives

- Automate monthly apartment maintenance billing.
- Manage flat and owner information.
- Record and track resident payments.
- Calculate outstanding balances and interest.
- Identify defaulters based on overdue payments.
- Manage No-Dues Certificates (NDC).
- Track ownership transfers and resale settlements.
- Monitor water meter readings and consumption.
- Generate financial reports and billing records.

## 3. Technologies Used

| Technology | Purpose |
|---|---|
| Python | Backend programming |
| Flask | Web application framework |
| HTML | Web page structure |
| CSS | Website styling |
| JavaScript | Frontend interactions |
| SQLite | Database management |
| Pandas | Data processing |
| CSV | Input data and reports |

## 4. Main Features

### 4.1 Dashboard
- Displays total flats and towers.
- Shows monthly billing information.
- Displays payment and outstanding summaries.
- Provides navigation to different management modules.

### 4.2 Residents Management
- Displays flat and owner details.
- Shows tower, floor and occupancy information.
- Organizes resident records.

### 4.3 Monthly Billing
- Generates monthly maintenance bills.
- Displays detailed bill information and amounts.
- Supports printing bills.

### 4.4 Payments Management
- Records and tracks resident payments.
- Displays payment dates and amounts.
- Helps monitor outstanding balances.

### 4.5 Defaulter Management
- Generates defaulter reports.
- Shows overdue principal and outstanding amounts.
- Helps identify residents with pending dues.

### 4.6 Ownership Management
- Manages No-Dues Certificate requests.
- Tracks ownership transfers.
- Generates resale settlement information.

### 4.7 Water Management
- Records water meter readings.
- Tracks water consumption.
- Helps monitor water usage records.

## 5. Project Folder Structure

```text
T014-PS-095/
│
├── app.py
├── database.py
├── check_database.py
├── requirements.txt
├── README.md
├── .gitignore
│
├── database/
│
├── engine/
│
├── input/
│
├── outputs/
│
├── static/
│   └── style.css
│
├── templates/
│   ├── dashboard.html
│   ├── residents.html
│   ├── monthly_bills.html
│   ├── payments.html
│   ├── defaulters.html
│   ├── ownership.html
│   └── water.html
│
└── tests/
```

## 6. Installation and Setup

Follow these steps to run the project locally.

### Step 1: Clone the Repository

```bash
git clone https://github.com/fathimanoorain557-stack/T014-PS-095.git
```

### Step 2: Open the Project Folder

```bash
cd T014-PS-095
```

### Step 3: Create a Virtual Environment

```bash
python -m venv .venv
```

### Step 4: Activate the Virtual Environment

**Windows:**

```bash
.venv\Scripts\activate
```

### Step 5: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 6: Run the Application

```bash
python app.py
```

### Step 7: Open the Website

Open the following address in your browser:

```text
http://127.0.0.1:5000
```

## 7. Live Deployment

The application is deployed using Render.

**Live Application:**

https://t014-ps-095-1.onrender.com

The live application can be accessed through a web browser without running the project locally.

*Note: The free hosting service may take some time to start after a period of inactivity.*

## 8. GitHub Repository

The complete project source code and documentation are available here:

https://github.com/fathimanoorain557-stack/T014-PS-095

## 9. Project Team

This project is developed collaboratively as part of the T014-PS-095 project assignment.

---

<p align="center">
  <strong>T014-PS-095</strong><br>
  Apartment Maintenance Management System<br>
  Academic Project | 2026
</p>

