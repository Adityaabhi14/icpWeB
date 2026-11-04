# 💰 SpendWise Pro — Personal Expenses & Cash Flow Tracker

A modern, full-stack personal finance application engineered with **Python**, **Flask**, **SQLite**, **Tailwind CSS**, and **Chart.js**.

---

## 🌟 Expanded Pro Features

### 1. 💵 Dual Inflow & Outflow Tracking (Cash Flow)
- Record both **Expenses** (outflows) and **Income** (salary, freelance, investments, dividends).
- Live calculation of **Net Savings** (`Total Income - Total Expenses`) and **Savings Rate %**.
- Dual comparative bar chart displaying month-over-month Income vs. Expenses.

### 2. 🔁 Subscriptions & Recurring Bills Manager (`/subscriptions`)
- Manage fixed recurring expenses: Netflix, Spotify, Gym, Rent, Fiber Internet, Cloud servers, etc.
- Support for **Monthly**, **Yearly**, and **Weekly** billing cycles with automatic monthly cost normalization.
- **Renewal Alerts**: Highlights bills due within the next 7 days.
- **One-Click Payment Logging**: Logs the bill payment as an expense and automatically advances the next renewal date!
- Status toggle: Pause or Resume subscriptions anytime.

### 3. 🎯 Category-Specific Budgets
- Set individual monthly budget caps per category (e.g., *Groceries: $400*, *Dining: $200*, *Entertainment: $100*).
- Dynamic progress meters with status cues (Green: `<80%`, Amber: `80-99%`, Red: `≥100% Exceeded`).
- Inline target editing directly from the Categories page.

### 4. 🧾 Receipt Attachment Upload & In-App Viewer
- Upload invoice or receipt images (`.png`, `.jpg`, `.jpeg`, `.webp`, `.pdf`) directly when recording or editing an expense.
- Secure, hashed file storage in `static/uploads/receipts/`.
- In-app modal viewer to inspect receipts right from the transaction ledger.

### 5. 🧠 Smart Financial Health Score & Actionable Insights
- Algorithmic **0–100 Financial Health Score** with status badge (*Excellent*, *Good*, *Fair*, *Needs Attention*).
- Actionable automated insights:
  - **Savings Rate Analysis**: Evaluates adherence to the 50/30/20 financial rule.
  - **Budget Burn Rate**: Warns when spending pace outstrips elapsed days in the month.
  - **Subscription Load**: Identifies when recurring bills consume > 15% of total income.

### 6. 📥 CSV Statement Import & Export
- **Bulk CSV Import**: Upload transaction statements from your bank or other budgeting apps; automatically creates missing categories and batches transactions.
- **CSV Export**: Filtered or complete ledger download in one click.

### 7. 🔐 Multi-Tenant Security & Isolation
- Salted password hashing via `werkzeug.security`.
- Strict user data isolation by `user_id`.
- One-click realistic sample data generator for instant visual demonstration.

---

## 🏗️ Architecture & File Structure

```
c:\icp\
├── app.py                  # Application Factory & Blueprint registry
├── config.py               # Application configuration, upload limits, secret keys
├── database.py             # SQLite connection management & automated additive migration
├── models.py               # Data Access Objects (User, Expense, Subscription, Budget, Insights)
├── auth.py                 # Authentication blueprint (Login, Register, Logout, Profile)
├── expenses.py             # Transactions blueprint (CRUD, Multi-filtering, Receipt uploads, CSV Import/Export)
├── subscriptions.py        # Recurring bills & subscription manager blueprint
├── analytics.py            # Dashboard overview, Health Score, Category Budgets & Chart API
├── schema.sql              # Relational database schema with foreign keys and indexes
├── requirements.txt        # Python dependency manifest
├── test_app.py             # Automated unit & integration test suite (7 tests, 100% pass)
├── static/
│   ├── css/style.css       # Custom styling, KPI gradients, and modal styles
│   ├── js/dashboard.js     # Chart.js initialization, async APIs, and modal controls
│   └── uploads/receipts/   # Secure directory for uploaded receipt files
└── templates/
    ├── base.html           # Master navigation, global Add/Edit modal, Receipt viewer
    ├── dashboard.html      # Cashflow overview, Health Score, Dual trend charts, Category budgets
    ├── expenses.html       # Full transaction ledger with search, type toggle, and pagination
    ├── subscriptions.html  # Subscriptions management, renewal alerts, and quick pay
    ├── categories.html     # Category budget targets and custom category creator
    ├── profile.html        # Settings, budget ceiling, and password security
    ├── 404.html            # User-friendly 404 error page
    ├── 500.html            # User-friendly 500 server error page
    └── auth/
        ├── login.html      # Sign in page
        └── register.html   # Registration page
```

---

## 🚀 Running the Application

### 1. Launch the Server
```powershell
python app.py
```

### 2. Access in Browser
Navigate to **[http://127.0.0.1:5000](http://127.0.0.1:5000)**.
- Create an account or sign in.
- Pre-loaded realistic sample data will instantly demonstrate all cashflow graphs, subscription reminders, and category budget meters.

---

## 🧪 Automated Test Suite

Run the full automated test suite anytime:

```powershell
python -m unittest test_app.py
```

```text
.......
----------------------------------------------------------------------
Ran 7 tests in 1.654s

OK
```
All unit tests verify database initialization, user auth, income vs. expense cash flow calculations, subscription renewal lifecycle, category budget tracking, financial health scoring, and CSV statement importing.
