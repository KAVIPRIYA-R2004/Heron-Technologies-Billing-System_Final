-- =========================================================
-- Heron Technologies - Billing Management System
-- MySQL Database Schema
-- =========================================================
-- Usage:
--   mysql -u root -p < database.sql
--
-- Note: Flask-SQLAlchemy (via db.create_all() in seed.py) will
-- also create these tables automatically. This file is provided
-- for DBAs who prefer to provision the schema manually, or for
-- reference / documentation purposes.
-- =========================================================

CREATE DATABASE IF NOT EXISTS heron_billing
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE heron_billing;

-- ---------------------------------------------------------
-- Users (single admin account, no self-signup)
-- ---------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(80) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(120) DEFAULT 'Administrator',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- ---------------------------------------------------------
-- Clients
-- ---------------------------------------------------------
CREATE TABLE IF NOT EXISTS clients (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(150) NOT NULL,
    contact_number VARCHAR(30),
    email VARCHAR(150),
    address VARCHAR(255),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- ---------------------------------------------------------
-- Invoices
-- ---------------------------------------------------------
CREATE TABLE IF NOT EXISTS invoices (
    id INT AUTO_INCREMENT PRIMARY KEY,
    invoice_number VARCHAR(30) NOT NULL UNIQUE,
    client_id INT NOT NULL,
    project_title VARCHAR(200) NOT NULL,
    invoice_date DATE,
    delivery_date DATE,
    subtotal DECIMAL(12,2) DEFAULT 0,
    total DECIMAL(12,2) DEFAULT 0,
    status VARCHAR(20) DEFAULT 'Pending',   -- Paid, Pending, Partial
    notes VARCHAR(255),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_invoices_client FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- ---------------------------------------------------------
-- Invoice line items
-- ---------------------------------------------------------
CREATE TABLE IF NOT EXISTS invoice_items (
    id INT AUTO_INCREMENT PRIMARY KEY,
    invoice_id INT NOT NULL,
    particular VARCHAR(255) NOT NULL,
    quantity DECIMAL(10,2) DEFAULT 1,
    rate DECIMAL(12,2) DEFAULT 0,
    amount DECIMAL(12,2) DEFAULT 0,
    CONSTRAINT fk_items_invoice FOREIGN KEY (invoice_id) REFERENCES invoices(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- ---------------------------------------------------------
-- Payments
-- ---------------------------------------------------------
CREATE TABLE IF NOT EXISTS payments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    invoice_id INT NOT NULL,
    amount DECIMAL(12,2) NOT NULL,
    payment_date DATE,
    method VARCHAR(30) DEFAULT 'Cash',   -- Cash, Bank Transfer, UPI, Cheque, Card
    notes VARCHAR(255),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_payments_invoice FOREIGN KEY (invoice_id) REFERENCES invoices(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- ---------------------------------------------------------
-- Indexes for common lookups
-- ---------------------------------------------------------
CREATE INDEX idx_invoices_status ON invoices(status);
CREATE INDEX idx_invoices_client ON invoices(client_id);
CREATE INDEX idx_payments_invoice ON payments(invoice_id);
CREATE INDEX idx_payments_date ON payments(payment_date);

-- ---------------------------------------------------------
-- Default admin user
-- NOTE: The password hash below is a placeholder. It is
-- strongly recommended to create the admin user via
-- `python seed.py` instead, which uses Werkzeug's secure
-- password hashing (pbkdf2:sha256) and reads credentials
-- from the ADMIN_USERNAME / ADMIN_PASSWORD environment
-- variables (defaults: admin / Heron@2026).
-- ---------------------------------------------------------
-- INSERT INTO users (username, password_hash, full_name)
-- VALUES ('admin', '<generated-by-seed.py>', 'Administrator');
