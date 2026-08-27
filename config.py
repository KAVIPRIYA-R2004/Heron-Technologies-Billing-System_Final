import os
from datetime import timedelta

basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.environ.get(
        "SECRET_KEY",
        "heron-technologies-secret-key-change-in-production"
    )

    # SQLite Database
    SQLALCHEMY_DATABASE_URI = "sqlite:///" + os.path.join(
        basedir,
        "heron_billing.db"
    )

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    PERMANENT_SESSION_LIFETIME = timedelta(hours=8)

    COMPANY_NAME = "HERON TECHNOLOGIES"
    COMPANY_TAGLINE = "EMBEDDED SOLUTIONS | SMART IOT | PCB ENGINEERING | R&D"
    COMPANY_ADDRESS = "6B, 3rd Floor, Gokhale St, Ram Nagar, Gandhipuram, Tamil Nadu 641009"
    COMPANY_PHONE = "+91 0422 4790591"
    COMPANY_EMAIL = "info@herontechnologies.com"
    COMPANY_PROPRIETOR = "Dineshkumar Ayyasamy"
    COMPANY_LOCATION = "Coimbatore"
    COMPANY_PRODUCT = "Electronics"

    # --- GST / statutory details (update with your real registration) ---
    COMPANY_GSTIN = "33CISPD6508A1ZL"
    COMPANY_PAN = "CISPD6508A"
    COMPANY_STATE = "Tamil Nadu"
    COMPANY_STATE_CODE = "33"

    # --- Bank details for NEFT/RTGS, shown on the invoice.
    #     Fixed defaults below; editable per-invoice from the create/edit form. ---
    BANK_NAME = "TAMILNAD MERCANTILE BANK"
    BANK_ACCOUNT_NAME = "HERON TECHNOLOGIES"
    BANK_ACCOUNT_NUMBER = "121150050802282"
    BANK_IFSC = "TMBL0000121"
    BANK_BRANCH = "Coimbatore"

    AUTHORIZED_SIGNATORY = ""

    ADMIN_USERNAME = "admin"
    ADMIN_PASSWORD = "Heron@2026"