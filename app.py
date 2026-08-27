import os
from datetime import date, datetime, timedelta

from flask import (
    Flask, render_template, redirect, url_for, request,
    flash, jsonify, send_file, session, abort
)
from flask_login import (
    LoginManager, login_user, logout_user, login_required, current_user
)
from sqlalchemy import func, extract

from config import Config
from extensions import db, login_manager
from models import User, Client, Invoice, InvoiceItem, Payment


def create_app():
    app = Flask(__name__)

    app.config.from_object(Config)

    app.secret_key = "heron-technologies-secret-key-change-in-production"

    db.init_app(app)
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    register_routes(app)
    return app


def generate_invoice_number():
    """HERON-YYYY-000X sequential invoice numbers."""
    year = date.today().year
    prefix = f"HRN-{year}-"
    last = (
        Invoice.query.filter(Invoice.invoice_number.like(f"{prefix}%"))
        .order_by(Invoice.id.desc())
        .first()
    )
    if last:
        try:
            last_seq = int(last.invoice_number.split("-")[-1])
        except ValueError:
            last_seq = 0
    else:
        last_seq = 0
    return f"{prefix}{last_seq + 1:04d}"


def register_routes(app):

    # ---------------------------------------------------------------
    # AUTH
    # ---------------------------------------------------------------
    @app.route("/login", methods=["GET", "POST"])
    def login():
        if current_user.is_authenticated:
            return redirect(url_for("dashboard"))

        if request.method == "POST":
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "")
            user = User.query.filter_by(username=username).first()

            if user and user.check_password(password):
                login_user(user, remember=True)
                session.permanent = True
                flash("Welcome back, " + (user.full_name or "Admin") + "!", "success")
                next_page = request.args.get("next")
                return redirect(next_page or url_for("dashboard"))
            else:
                flash("Invalid username or password.", "danger")

        return render_template("login.html")

    @app.route("/logout")
    @login_required
    def logout():
        logout_user()
        flash("You have been logged out successfully.", "info")
        return redirect(url_for("login"))

    # ---------------------------------------------------------------
    # DASHBOARD
    # ---------------------------------------------------------------
    @app.route("/")
    @login_required
    def dashboard():
        total_revenue = db.session.query(func.coalesce(func.sum(Payment.amount), 0)).scalar()
        total_invoices = Invoice.query.count()
        total_clients = Client.query.count()
        pending_amount = db.session.query(
            func.coalesce(func.sum(Invoice.total), 0)
        ).filter(Invoice.status != "Paid").scalar()
        pending_paid_offset = db.session.query(
            func.coalesce(func.sum(Payment.amount), 0)
        ).join(Invoice).filter(Invoice.status != "Paid").scalar()
        pending_payments = float(pending_amount) - float(pending_paid_offset)

        recent_invoices = Invoice.query.order_by(Invoice.created_at.desc()).limit(6).all()

        # Monthly revenue for the last 6 months (for Chart.js)
        months_labels = []
        months_data = []
        today = date.today()
        for i in range(5, -1, -1):
            year = today.year
            month = today.month - i
            while month <= 0:
                month += 12
                year -= 1
            total = db.session.query(func.coalesce(func.sum(Payment.amount), 0)).filter(
                extract("year", Payment.payment_date) == year,
                extract("month", Payment.payment_date) == month,
            ).scalar()
            months_labels.append(date(year, month, 1).strftime("%b %Y"))
            months_data.append(float(total))

        status_counts = {
            "Paid": Invoice.query.filter_by(status="Paid").count(),
            "Pending": Invoice.query.filter_by(status="Pending").count(),
            "Partial": Invoice.query.filter_by(status="Partial").count(),
        }

        return render_template(
            "dashboard.html",
            total_revenue=total_revenue,
            total_invoices=total_invoices,
            total_clients=total_clients,
            pending_payments=pending_payments,
            recent_invoices=recent_invoices,
            months_labels=months_labels,
            months_data=months_data,
            status_counts=status_counts,
        )

    # ---------------------------------------------------------------
    # INVOICES
    # ---------------------------------------------------------------
    @app.route("/invoices")
    @login_required
    def invoices_list():
        search = request.args.get("q", "").strip()
        status = request.args.get("status", "").strip()

        query = Invoice.query.join(Client)
        if search:
            like = f"%{search}%"
            query = query.filter(
                db.or_(
                    Invoice.invoice_number.ilike(like),
                    Client.name.ilike(like),
                    Invoice.project_title.ilike(like),
                )
            )
        if status:
            query = query.filter(Invoice.status == status)

        invoices = query.order_by(Invoice.created_at.desc()).all()
        return render_template("invoices/list.html", invoices=invoices, search=search, status=status)

    @app.route("/invoices/create", methods=["GET", "POST"])
    @login_required
    def invoice_create():
        clients = Client.query.order_by(Client.name).all()

        if request.method == "POST":
            client_name = request.form.get("client_name", "").strip()
            contact_number = request.form.get("contact_number", "").strip()
            client_gstin = request.form.get("client_gstin", "").strip()
            client_address = request.form.get("client_address", "").strip()
            project_title = request.form.get("project_title", "").strip()
            delivery_date_str = request.form.get("delivery_date", "")
            due_date_str = request.form.get("due_date", "")
            status = request.form.get("status", "Pending")
            place_of_supply = request.form.get("place_of_supply", "Tamil Nadu (33)").strip()
            reverse_charge = request.form.get("reverse_charge", "No")
            payment_terms = request.form.get("payment_terms", "Immediate").strip()
            gst_rate_str = request.form.get("gst_rate", "18")
            bank_name = request.form.get("bank_name", "").strip()
            bank_account_name = request.form.get("bank_account_name", "").strip()
            bank_account_number = request.form.get("bank_account_number", "").strip()
            bank_ifsc = request.form.get("bank_ifsc", "").strip()
            bank_branch = request.form.get("bank_branch", "").strip()

            if not client_name or not project_title:
                flash("Client name and project title are required.", "danger")
                return redirect(url_for("invoice_create"))

            client = Client.query.filter_by(name=client_name).first()
            if not client:
                client = Client(
                    name=client_name, contact_number=contact_number,
                    gstin=client_gstin, address=client_address,
                )
                db.session.add(client)
                db.session.flush()
            else:
                if contact_number and not client.contact_number:
                    client.contact_number = contact_number
                if client_gstin:
                    client.gstin = client_gstin
                if client_address:
                    client.address = client_address

            delivery_date = None
            if delivery_date_str:
                try:
                    delivery_date = datetime.strptime(delivery_date_str, "%Y-%m-%d").date()
                except ValueError:
                    delivery_date = None

            due_date = None
            if due_date_str:
                try:
                    due_date = datetime.strptime(due_date_str, "%Y-%m-%d").date()
                except ValueError:
                    due_date = None

            try:
                gst_rate = float(gst_rate_str)
            except ValueError:
                gst_rate = 18

            invoice = Invoice(
                invoice_number=generate_invoice_number(),
                client_id=client.id,
                project_title=project_title,
                delivery_date=delivery_date,
                due_date=due_date,
                status=status,
                place_of_supply=place_of_supply,
                reverse_charge=reverse_charge,
                payment_terms=payment_terms,
                gst_rate=gst_rate,
                bank_name=bank_name or None,
                bank_account_name=bank_account_name or None,
                bank_account_number=bank_account_number or None,
                bank_ifsc=bank_ifsc or None,
                bank_branch=bank_branch or None,
            )
            db.session.add(invoice)
            db.session.flush()

            particulars = request.form.getlist("particular[]")
            hsn_codes = request.form.getlist("hsn_sac[]")
            quantities = request.form.getlist("quantity[]")
            rates = request.form.getlist("rate[]")

            for p, h, q, r in zip(particulars, hsn_codes, quantities, rates):
                if not p.strip():
                    continue
                q_val = float(q) if q else 1
                r_val = float(r) if r else 0
                amount = q_val * r_val
                db.session.add(InvoiceItem(
                    invoice_id=invoice.id, particular=p.strip(), hsn_sac=h.strip() or "8537",
                    quantity=q_val, rate=r_val, amount=amount
                ))

            db.session.flush()
            invoice.recompute_totals()

            if status == "Paid":
                db.session.add(Payment(invoice_id=invoice.id, amount=invoice.total, method="Cash"))

            db.session.commit()
            flash(f"Invoice {invoice.invoice_number} created successfully.", "success")
            return redirect(url_for("invoices_list"))

        next_number = generate_invoice_number()
        return render_template("invoices/create.html", clients=clients, next_number=next_number, today=date.today(), company=Config)

    @app.route("/invoices/<int:invoice_id>/edit", methods=["GET", "POST"])
    @login_required
    def invoice_edit(invoice_id):
        invoice = Invoice.query.get_or_404(invoice_id)
        clients = Client.query.order_by(Client.name).all()

        if request.method == "POST":
            client_name = request.form.get("client_name", "").strip()
            contact_number = request.form.get("contact_number", "").strip()
            client_gstin = request.form.get("client_gstin", "").strip()
            client_address = request.form.get("client_address", "").strip()
            invoice.project_title = request.form.get("project_title", "").strip()
            delivery_date_str = request.form.get("delivery_date", "")
            due_date_str = request.form.get("due_date", "")
            invoice.status = request.form.get("status", invoice.status)
            invoice.place_of_supply = request.form.get("place_of_supply", invoice.place_of_supply).strip()
            invoice.reverse_charge = request.form.get("reverse_charge", invoice.reverse_charge)
            invoice.payment_terms = request.form.get("payment_terms", invoice.payment_terms).strip()
            invoice.bank_name = request.form.get("bank_name", "").strip() or None
            invoice.bank_account_name = request.form.get("bank_account_name", "").strip() or None
            invoice.bank_account_number = request.form.get("bank_account_number", "").strip() or None
            invoice.bank_ifsc = request.form.get("bank_ifsc", "").strip() or None
            invoice.bank_branch = request.form.get("bank_branch", "").strip() or None

            gst_rate_str = request.form.get("gst_rate", "")
            if gst_rate_str:
                try:
                    invoice.gst_rate = float(gst_rate_str)
                except ValueError:
                    pass

            client = Client.query.filter_by(name=client_name).first()
            if not client:
                client = Client(
                    name=client_name, contact_number=contact_number,
                    gstin=client_gstin, address=client_address,
                )
                db.session.add(client)
                db.session.flush()
            else:
                client.contact_number = contact_number or client.contact_number
                if client_gstin:
                    client.gstin = client_gstin
                if client_address:
                    client.address = client_address
            invoice.client_id = client.id

            if delivery_date_str:
                try:
                    invoice.delivery_date = datetime.strptime(delivery_date_str, "%Y-%m-%d").date()
                except ValueError:
                    pass

            if due_date_str:
                try:
                    invoice.due_date = datetime.strptime(due_date_str, "%Y-%m-%d").date()
                except ValueError:
                    pass

            InvoiceItem.query.filter_by(invoice_id=invoice.id).delete()

            particulars = request.form.getlist("particular[]")
            hsn_codes = request.form.getlist("hsn_sac[]")
            quantities = request.form.getlist("quantity[]")
            rates = request.form.getlist("rate[]")

            for p, h, q, r in zip(particulars, hsn_codes, quantities, rates):
                if not p.strip():
                    continue
                q_val = float(q) if q else 1
                r_val = float(r) if r else 0
                amount = q_val * r_val
                db.session.add(InvoiceItem(
                    invoice_id=invoice.id, particular=p.strip(), hsn_sac=h.strip() or "8537",
                    quantity=q_val, rate=r_val, amount=amount
                ))

            db.session.flush()
            invoice.recompute_totals()
            invoice.refresh_status()

            db.session.commit()
            flash(f"Invoice {invoice.invoice_number} updated successfully.", "success")
            return redirect(url_for("invoices_list"))

        return render_template("invoices/edit.html", invoice=invoice, clients=clients, company=Config)

    @app.route("/invoices/<int:invoice_id>/delete", methods=["POST"])
    @login_required
    def invoice_delete(invoice_id):
        invoice = Invoice.query.get_or_404(invoice_id)
        number = invoice.invoice_number
        db.session.delete(invoice)
        db.session.commit()
        flash(f"Invoice {number} deleted.", "info")
        return redirect(url_for("invoices_list"))

    @app.route("/invoices/<int:invoice_id>/print")
    @login_required
    def invoice_print(invoice_id):
        invoice = Invoice.query.get_or_404(invoice_id)
        logo_src = url_for("static", filename="img/logo.png")
        return render_template(
            "invoices/print.html", invoice=invoice, company=Config,
            pdf_mode=False, logo_src=logo_src
        )

    @app.route("/invoices/<int:invoice_id>/pdf")
    @login_required
    def invoice_pdf(invoice_id):
        invoice = Invoice.query.get_or_404(invoice_id)
        from utils.pdf_generator import generate_invoice_pdf
        pdf_bytes = generate_invoice_pdf(invoice, app)
        return send_file(
            pdf_bytes,
            mimetype="application/pdf",
            as_attachment=True,
            download_name=f"{invoice.invoice_number}.pdf",
        )

    # ---------------------------------------------------------------
    # CLIENTS
    # ---------------------------------------------------------------
    @app.route("/clients")
    @login_required
    def clients_list():
        search = request.args.get("q", "").strip()
        query = Client.query
        if search:
            like = f"%{search}%"
            query = query.filter(db.or_(Client.name.ilike(like), Client.email.ilike(like)))
        clients = query.order_by(Client.name).all()
        return render_template("clients/list.html", clients=clients, search=search)

    @app.route("/clients/create", methods=["POST"])
    @login_required
    def client_create():
        name = request.form.get("name", "").strip()
        if not name:
            flash("Client name is required.", "danger")
            return redirect(url_for("clients_list"))

        client = Client(
            name=name,
            contact_number=request.form.get("contact_number", "").strip(),
            email=request.form.get("email", "").strip(),
            address=request.form.get("address", "").strip(),
        )
        db.session.add(client)
        db.session.commit()
        flash(f"Client '{name}' added successfully.", "success")
        return redirect(url_for("clients_list"))

    @app.route("/clients/<int:client_id>/edit", methods=["POST"])
    @login_required
    def client_edit(client_id):
        client = Client.query.get_or_404(client_id)
        client.name = request.form.get("name", client.name).strip()
        client.contact_number = request.form.get("contact_number", "").strip()
        client.email = request.form.get("email", "").strip()
        client.address = request.form.get("address", "").strip()
        db.session.commit()
        flash("Client updated successfully.", "success")
        return redirect(url_for("clients_list"))

    @app.route("/clients/<int:client_id>/delete", methods=["POST"])
    @login_required
    def client_delete(client_id):
        client = Client.query.get_or_404(client_id)
        db.session.delete(client)
        db.session.commit()
        flash("Client deleted.", "info")
        return redirect(url_for("clients_list"))

    # ---------------------------------------------------------------
    # PAYMENTS
    # ---------------------------------------------------------------
    @app.route("/payments")
    @login_required
    def payments_list():
        payments = Payment.query.order_by(Payment.payment_date.desc()).all()
        unpaid_invoices = Invoice.query.filter(Invoice.status != "Paid").order_by(Invoice.created_at.desc()).all()
        return render_template("payments/list.html", payments=payments, unpaid_invoices=unpaid_invoices)

    @app.route("/payments/create", methods=["POST"])
    @login_required
    def payment_create():
        invoice_id = request.form.get("invoice_id")
        amount = request.form.get("amount")
        method = request.form.get("method", "Cash")
        payment_date_str = request.form.get("payment_date", "")
        notes = request.form.get("notes", "")

        invoice = Invoice.query.get_or_404(invoice_id)

        try:
            amount_val = float(amount)
        except (TypeError, ValueError):
            flash("Invalid payment amount.", "danger")
            return redirect(url_for("payments_list"))

        payment_date = date.today()
        if payment_date_str:
            try:
                payment_date = datetime.strptime(payment_date_str, "%Y-%m-%d").date()
            except ValueError:
                pass

        payment = Payment(
            invoice_id=invoice.id, amount=amount_val, method=method,
            payment_date=payment_date, notes=notes
        )
        db.session.add(payment)
        db.session.flush()
        invoice.refresh_status()
        db.session.commit()

        flash(f"Payment of ₹{amount_val:,.2f} recorded for {invoice.invoice_number}.", "success")
        return redirect(url_for("payments_list"))

    @app.route("/payments/<int:payment_id>/delete", methods=["POST"])
    @login_required
    def payment_delete(payment_id):
        payment = Payment.query.get_or_404(payment_id)
        invoice = payment.invoice
        db.session.delete(payment)
        db.session.flush()
        invoice.refresh_status()
        db.session.commit()
        flash("Payment record removed.", "info")
        return redirect(url_for("payments_list"))

    # ---------------------------------------------------------------
    # REPORTS
    # ---------------------------------------------------------------
    @app.route("/reports")
    @login_required
    def reports():
        start_str = request.args.get("start")
        end_str = request.args.get("end")

        today = date.today()
        start = datetime.strptime(start_str, "%Y-%m-%d").date() if start_str else today.replace(day=1)
        end = datetime.strptime(end_str, "%Y-%m-%d").date() if end_str else today

        invoices = Invoice.query.filter(Invoice.invoice_date.between(start, end)).all()
        payments = Payment.query.filter(Payment.payment_date.between(start, end)).all()

        total_billed = sum(float(i.total) for i in invoices)
        total_collected = sum(float(p.amount) for p in payments)
        total_outstanding = total_billed - total_collected

        by_client = {}
        for inv in invoices:
            by_client.setdefault(inv.client.name, {"count": 0, "total": 0})
            by_client[inv.client.name]["count"] += 1
            by_client[inv.client.name]["total"] += float(inv.total)

        return render_template(
            "reports/list.html",
            invoices=invoices,
            payments=payments,
            total_billed=total_billed,
            total_collected=total_collected,
            total_outstanding=total_outstanding,
            by_client=by_client,
            start=start,
            end=end,
        )

    # ---------------------------------------------------------------
    # API (Chart.js live data / AJAX helpers)
    # ---------------------------------------------------------------
    @app.route("/api/client/<int:client_id>")
    @login_required
    def api_client(client_id):
        client = Client.query.get_or_404(client_id)
        return jsonify({"name": client.name, "contact_number": client.contact_number or ""})

    @app.errorhandler(404)
    def not_found(e):
        return render_template("404.html"), 404


app = create_app()

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
