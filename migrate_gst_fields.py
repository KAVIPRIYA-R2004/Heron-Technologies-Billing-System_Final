"""
One-time migration: adds the GST tax-invoice columns to an existing
heron_billing.db (SQLite) without touching existing data.

Safe to run multiple times - it skips any column that already exists.

Usage:
    python migrate_gst_fields.py
"""
import sqlite3
from config import Config

DB_PATH = Config.SQLALCHEMY_DATABASE_URI.replace("sqlite:///", "")

COLUMNS = {
    "clients": [
        ("gstin", "VARCHAR(20)"),
    ],
    "invoices": [
        ("due_date", "DATE"),
        ("gst_rate", "NUMERIC(5,2) DEFAULT 18"),
        ("place_of_supply", "VARCHAR(80) DEFAULT 'Tamil Nadu (33)'"),
        ("reverse_charge", "VARCHAR(10) DEFAULT 'No'"),
        ("payment_terms", "VARCHAR(50) DEFAULT 'Immediate'"),
        ("bank_name", "VARCHAR(100)"),
        ("bank_account_name", "VARCHAR(150)"),
        ("bank_account_number", "VARCHAR(40)"),
        ("bank_ifsc", "VARCHAR(20)"),
        ("bank_branch", "VARCHAR(120)"),
    ],
    "invoice_items": [
        ("hsn_sac", "VARCHAR(20) DEFAULT '8537'"),
    ],
}


def column_exists(cur, table, column):
    cur.execute(f"PRAGMA table_info({table})")
    return any(row[1] == column for row in cur.fetchall())


def migrate():
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    for table, columns in COLUMNS.items():
        for column, ddl_type in columns:
            if column_exists(cur, table, column):
                print(f"  - {table}.{column} already exists, skipping.")
                continue
            cur.execute(f"ALTER TABLE {table} ADD COLUMN {column} {ddl_type}")
            print(f"  + added {table}.{column}")

    # Backfill: existing invoices had `total` == pre-tax subtotal.
    # Recompute grand total (subtotal + 18% GST) so old invoices display
    # correctly under the new tax-inclusive `total` convention.
    cur.execute("SELECT id, subtotal, gst_rate FROM invoices")
    rows = cur.fetchall()
    for invoice_id, subtotal, gst_rate in rows:
        subtotal = subtotal or 0
        rate = gst_rate if gst_rate is not None else 18
        grand_total = round(float(subtotal) * (1 + float(rate) / 100), 2)
        cur.execute("UPDATE invoices SET total = ? WHERE id = ?", (grand_total, invoice_id))

    con.commit()
    con.close()
    print(f"\nMigration complete on {DB_PATH} ({len(rows)} invoice(s) recalculated).")


if __name__ == "__main__":
    migrate()
