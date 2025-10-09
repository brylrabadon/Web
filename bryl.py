from flask import Flask, render_template, request, redirect, session, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import os

bryl = Flask(__name__)
bryl.secret_key = "bryl_secret_key"

# --- DATABASE CONFIG (use absolute path for safety) ---
db_path = r"C:\rabadon\Web\loan_system.db"
bryl.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_path.replace(os.sep, '/')}"
bryl.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(bryl)

# --- MODELS ---
class User(db.Model):
    __tablename__ = "tbl_users"
    u_id = db.Column(db.Integer, primary_key=True)
    u_name = db.Column(db.String(), unique=True, nullable=False)
    u_password = db.Column(db.String(), nullable=False)
    u_role = db.Column(db.String(), nullable=False)  # admin / borrower
    u_status = db.Column(db.String(), default="Pending")  # Approved / Pending

    def set_password(self, password):
        self.u_password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.u_password, password)


class Loan(db.Model):
    __tablename__ = "tbl_loans"
    loan_id = db.Column(db.Integer, primary_key=True)
    u_id = db.Column(db.Integer, db.ForeignKey("tbl_users.u_id"), nullable=False)
    loan_amount = db.Column(db.Float, nullable=False)
    interest_rate = db.Column(db.Float, nullable=False)
    loan_status = db.Column(db.String(), default="Pending")  # Pending / Approved / Rejected


# --- ROUTES ---
@bryl.route("/")
def index():
    return render_template("index.html")


# --- REGISTER ---
@bryl.route("/register", methods=["POST"])
def register():
    username = request.form["username"]
    password = request.form["password"]
    role = request.form["role"]

    existing_user = User.query.filter_by(u_name=username).first()
    if existing_user:
        flash("Username already exists!")
        return redirect(url_for("index"))

    new_user = User(u_name=username, u_role=role)
    new_user.set_password(password)

    if role.lower() == "admin":
        new_user.u_status = "Approved"
        flash("Admin registered successfully!")
    else:
        new_user.u_status = "Pending"
        flash("Borrower registration submitted for approval.")

    db.session.add(new_user)
    db.session.commit()
    return redirect(url_for("index"))


# --- LOGIN (with automatic password rehashing for old accounts) ---
@bryl.route("/login", methods=["POST"])
def login():
    username = request.form["username"]
    password = request.form["password"]
    role = request.form["role"]

    user = User.query.filter_by(u_name=username, u_role=role).first()

    if user:
        # ✅ Detect old plain-text password and fix it
        if not user.u_password.startswith("pbkdf2:sha256:"):
            old_pw = user.u_password
            user.set_password(old_pw)
            db.session.commit()
            print(f"[INFO] Password for user '{user.u_name}' was plain text. Re-hashed automatically.")

        # ✅ Now check normally
        if user.check_password(password):
            if user.u_status == "Approved":
                session["username"] = user.u_name
                session["role"] = user.u_role

                if user.u_role == "admin":
                    return redirect(url_for("admin_dashboard"))
                else:
                    return redirect(url_for("borrower_dashboard"))
            else:
                flash("Your account is still pending admin approval.")
                return redirect(url_for("index"))

    flash("Invalid username or password.")
    return redirect(url_for("index"))


# --- ADMIN DASHBOARD ---
@bryl.route("/admin")
def admin_dashboard():
    if "role" not in session or session["role"] != "admin":
        return redirect(url_for("index"))

    pending_borrowers = User.query.filter_by(u_role="borrower", u_status="Pending").all()
    loans = Loan.query.all()
    return render_template("admin.html", pending_borrowers=pending_borrowers, loans=loans)


# --- BORROWER DASHBOARD ---
@bryl.route("/borrower")
def borrower_dashboard():
    if "role" not in session or session["role"] != "borrower":
        return redirect(url_for("index"))

    user = User.query.filter_by(u_name=session["username"]).first()
    loans = Loan.query.filter_by(u_id=user.u_id).all()
    return render_template("borrower.html", username=user.u_name, loans=loans)


# --- APPROVE / REJECT BORROWER ---
@bryl.route("/approve_borrower/<int:user_id>")
def approve_borrower(user_id):
    if "role" not in session or session["role"] != "admin":
        return redirect(url_for("index"))

    borrower = User.query.get(user_id)
    if borrower:
        borrower.u_status = "Approved"
        db.session.commit()
        flash(f"Borrower '{borrower.u_name}' approved!")
    return redirect(url_for("admin_dashboard"))


@bryl.route("/reject_borrower/<int:user_id>")
def reject_borrower(user_id):
    if "role" not in session or session["role"] != "admin":
        return redirect(url_for("index"))

    borrower = User.query.get(user_id)
    if borrower:
        db.session.delete(borrower)
        db.session.commit()
        flash("Borrower rejected and removed.")
    return redirect(url_for("admin_dashboard"))


# --- APPLY FOR LOAN ---
@bryl.route("/apply_loan", methods=["POST"])
def apply_loan():
    if "role" not in session or session["role"] != "borrower":
        return redirect(url_for("index"))

    user = User.query.filter_by(u_name=session["username"]).first()
    amount = float(request.form["amount"])
    interest = float(request.form["interest"])

    new_loan = Loan(u_id=user.u_id, loan_amount=amount, interest_rate=interest)
    db.session.add(new_loan)
    db.session.commit()
    flash("Loan application submitted!")
    return redirect(url_for("borrower_dashboard"))


# --- LOGOUT ---
@bryl.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.")
    return redirect(url_for("index"))


# --- MAIN ---
if __name__ == "__main__":
    with bryl.app_context():
        db.create_all()
        print("✅ Connected to database at:", os.path.abspath(db_path))

    bryl.run(debug=True)
