from datetime import datetime, date
from decimal import Decimal, ROUND_HALF_UP
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from extensions import db
from utils.number_to_words import amount_in_words_inr


def _q2(value):
    """Round a numeric value to 2 decimal places using Decimal."""
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(120), default="Administrator")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Client(db.Model):
    __tablename__ = "clients"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    contact_number = db.Column(db.String(30))
    email = db.Column(db.String(150))
    address = db.Column(db.String(255))
    gstin = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    invoices = db.relationship("Invoice", backref="client", lazy=True, cascade="all, delete-orphan")

    @property
    def total_billed(self):
        return sum(inv.total for inv in self.invoices)

    @property
    def total_paid(self):
        return sum(p.amount for inv in self.invoices for p in inv.payments)

    @property
    def total_invoices(self):
        return len(self.invoices)


class Invoice(db.Model):
    __tablename__ = "invoices"

    id = db.Column(db.Integer, primary_key=True)
    invoice_number = db.Column(db.String(30), unique=True, nullable=False)
    client_id = db.Column(db.Integer, db.ForeignKey("clients.id"), nullable=False)
    project_title = db.Column(db.String(200), nullable=False)
    invoice_date = db.Column(db.Date, default=date.today)
    delivery_date = db.Column(db.Date)
    due_date = db.Column(db.Date)
    subtotal = db.Column(db.Numeric(12, 2), default=0)   # taxable value (pre-GST)
    total = db.Column(db.Numeric(12, 2), default=0)       # grand total (GST-inclusive)
    status = db.Column(db.String(20), default="Pending")  # Paid, Pending, Partial
    notes = db.Column(db.String(255))

    # --- GST / tax-invoice fields ---
    gst_rate = db.Column(db.Numeric(5, 2), default=18)          # total GST %, split evenly CGST+SGST
    place_of_supply = db.Column(db.String(80), default="Tamil Nadu (33)")
    reverse_charge = db.Column(db.String(10), default="No")
    payment_terms = db.Column(db.String(50), default="Immediate")

    # --- Bank details shown on this invoice (optional per-invoice override;
    #     falls back to the company defaults in config.py when blank) ---
    bank_name = db.Column(db.String(100))
    bank_account_name = db.Column(db.String(150))
    bank_account_number = db.Column(db.String(40))
    bank_ifsc = db.Column(db.String(20))
    bank_branch = db.Column(db.String(120))

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    items = db.relationship("InvoiceItem", backref="invoice", lazy=True, cascade="all, delete-orphan")
    payments = db.relationship("Payment", backref="invoice", lazy=True, cascade="all, delete-orphan")

    @property
    def amount_paid(self):
        return sum(p.amount for p in self.payments)

    @property
    def balance_due(self):
        return float(self.total) - float(self.amount_paid)

    @property
    def tax_amount(self):
        """Total GST (CGST + SGST) on the taxable value."""
        rate = Decimal(str(self.gst_rate or 0))
        return _q2(Decimal(str(self.subtotal or 0)) * rate / Decimal("100"))

    @property
    def cgst_amount(self):
        return _q2(self.tax_amount / Decimal("2"))

    @property
    def sgst_amount(self):
        return self.tax_amount - self.cgst_amount

    @property
    def cgst_rate(self):
        return _q2(Decimal(str(self.gst_rate or 0)) / Decimal("2"))

    @property
    def sgst_rate(self):
        return self.cgst_rate

    @property
    def grand_total(self):
        return _q2(Decimal(str(self.subtotal or 0)) + self.tax_amount)

    @property
    def amount_in_words(self):
        return amount_in_words_inr(self.total or 0)

    def bank_details(self, company_config):
        """Effective bank details for this invoice: per-invoice override if
        set, otherwise the company defaults from config.py."""
        return {
            "name": self.bank_name or company_config.BANK_NAME,
            "account_name": self.bank_account_name or company_config.BANK_ACCOUNT_NAME,
            "account_number": self.bank_account_number or company_config.BANK_ACCOUNT_NUMBER,
            "ifsc": self.bank_ifsc or company_config.BANK_IFSC,
            "branch": self.bank_branch or company_config.BANK_BRANCH,
        }

    def recompute_totals(self):
        """Recalculate subtotal, tax and grand total from line items."""
        subtotal = sum((float(item.amount) for item in self.items), 0.0)
        self.subtotal = _q2(subtotal)
        self.total = self.grand_total

    def refresh_status(self):
        paid = float(self.amount_paid)
        total = float(self.total)
        if paid <= 0:
            self.status = "Pending"
        elif paid >= total:
            self.status = "Paid"
        else:
            self.status = "Partial"


class InvoiceItem(db.Model):
    __tablename__ = "invoice_items"

    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey("invoices.id"), nullable=False)
    particular = db.Column(db.String(255), nullable=False)
    hsn_sac = db.Column(db.String(20), default="8537")
    quantity = db.Column(db.Numeric(10, 2), default=1)
    rate = db.Column(db.Numeric(12, 2), default=0)
    amount = db.Column(db.Numeric(12, 2), default=0)


class Payment(db.Model):
    __tablename__ = "payments"

    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey("invoices.id"), nullable=False)
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    payment_date = db.Column(db.Date, default=date.today)
    method = db.Column(db.String(30), default="Cash")  # Cash, Bank Transfer, UPI, Cheque, Card
    notes = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
