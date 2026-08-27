# Heron Technologies — Billing Management System

A production-ready internal billing application built for **Heron Technologies**.
Single-admin login, invoice creation with auto-numbering, client management,
payment tracking, dashboard analytics, and PDF/print invoice generation that
recreates the company's official invoice format exactly.

---

## Tech Stack

| Layer          | Technology                                  |
|----------------|----------------------------------------------|
| Backend        | Python, Flask                                |
| ORM / Database | SQLAlchemy, MySQL (SQLite fallback for dev)  |
| Auth           | Flask-Login (single admin account)           |
| Frontend       | HTML, CSS, Bootstrap 5, vanilla JavaScript   |
| Charts         | Chart.js                                     |
| PDF Generation | WeasyPrint (primary), ReportLab (fallback)   |

---

## Folder Structure

```
heron_billing/
├── app.py                  # Flask app factory + all routes
├── config.py                # Environment-driven configuration
├── extensions.py             # db, login_manager singletons
├── models.py                  # SQLAlchemy models
├── seed.py                     # Creates admin user + sample data
├── database.sql                 # MySQL schema (manual provisioning)
├── requirements.txt
├── .env.example
├── utils/
│   └── pdf_generator.py         # WeasyPrint + ReportLab invoice PDF
├── static/
│   ├── css/style.css             # Premium ERP-style theme (brand colors)
│   ├── js/                        # (reserved for future custom scripts)
│   └── img/logo.png                # Heron Technologies logo
└── templates/
    ├── base.html                    # Sidebar layout shell
    ├── login.html
    ├── dashboard.html
    ├── 404.html
    ├── invoices/
    │   ├── list.html
    │   ├── create.html
    │   ├── edit.html
    │   └── print.html                  # Exact recreation of the reference invoice
    ├── clients/list.html
    ├── payments/list.html
    └── reports/list.html
```

---

## 1. Setup

### 1.1 Clone & create a virtual environment

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

> **WeasyPrint system dependencies:** WeasyPrint needs Pango, Cairo and
> GDK-Pixbuf installed at the OS level.
> - Ubuntu/Debian: `sudo apt-get install libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf2.0-0 libffi-dev`
> - macOS (Homebrew): `brew install pango`
> - Windows: follow the official WeasyPrint installation guide.
>
> If these aren't available, the app **automatically falls back to
> ReportLab** for PDF generation — no code changes needed.

### 1.2 Configure the database

**Option A — MySQL (recommended for production)**

1. Create the database and tables:
   ```bash
   mysql -u root -p < database.sql
   ```
2. Set environment variables (copy `.env.example` to `.env` and edit, or
   export directly):
   ```bash
   export DB_USER=root
   export DB_PASSWORD=your_mysql_password
   export DB_HOST=localhost
   export DB_PORT=3306
   export DB_NAME=heron_billing
   ```

**Option B — SQLite (zero-config, for quick local testing)**

```bash
export USE_SQLITE=1
```

### 1.3 Seed the admin user (and optional sample data)

```bash
python seed.py
```

This creates the tables (if they don't already exist), a single admin
account, and a handful of sample clients/invoices/payments so the
dashboard has data to display immediately.

Default admin credentials (change via `ADMIN_USERNAME` / `ADMIN_PASSWORD`
environment variables, or update the user afterward):

```
Username: admin
Password: Heron@2026
```

### 1.4 Run the app

```bash
python app.py
```

Visit **http://localhost:5000** and log in.

---

## 2. Features

- **Single Admin Login** — no signup or forgot-password flow; the only
  account is the one created by `seed.py`.
- **Dashboard** — total revenue, invoice count, client count, pending
  payments, a 6-month revenue trend chart, an invoice-status donut chart,
  and a recent invoices table.
- **Create Invoice** — auto-generated invoice numbers (`HRN-YYYY-000X`),
  delivery date, client name/contact (autocompletes existing clients),
  project title, a dynamic add/remove item table with live amount and
  grand-total calculation, and payment status.
- **Invoice History** — search by invoice number/client/project, filter by
  status, edit, delete (with confirmation), print, and download as PDF.
- **Clients** — add/edit/delete clients, see totals billed per client.
- **Payments** — record payments against any unpaid/partially-paid
  invoice; invoice status (`Pending` / `Partial` / `Paid`) updates
  automatically based on amounts received.
- **Reports** — date-range filtered summary of billed vs. collected vs.
  outstanding amounts, broken down by client.
- **Invoice Print/PDF** — recreates the official Heron Technologies
  invoice layout (logo, address block, meta table, item table, totals,
  amount status) pixel-for-pixel from the reference design, with dynamic
  data.

---

## 3. Security Notes

- Passwords are hashed with Werkzeug's `pbkdf2:sha256` (never stored in
  plain text).
- Change `SECRET_KEY` and the default admin password before deploying to
  production.
- This app has no public signup — provision the single admin account only
  through `seed.py` or directly in the database.

---

## 4. Customization

- **Company details** (name, address) live in `config.py` under the
  `Config` class — update `COMPANY_NAME`, `COMPANY_ADDRESS`, etc.
- **Brand colors** are defined as CSS variables at the top of
  `static/css/style.css` (`--hrn-teal`, `--hrn-cyan`, `--hrn-navy`, ...),
  sampled directly from the Heron Technologies logo.
- **Invoice numbering format** can be changed in the
  `generate_invoice_number()` function in `app.py`.

---

## 5. License

Internal software built for Heron Technologies. All rights reserved.
