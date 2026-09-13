from flask import Flask, render_template, request, redirect, url_for, session, flash
import pandas as pd
import joblib
import os
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps


app = Flask(__name__)

# Secret key for login sessions
app.secret_key = "smart-expense-secret-key-change-this"


# =========================================================
# FILE PATHS
# =========================================================

DATA_FILE = "data/expenses.csv"
MODEL_FILE = "models/expense_prediction_model.pkl"
DATABASE = "users.db"


# =========================================================
# DEFAULT BUDGETS
# =========================================================

DEFAULT_BUDGETS = {
    "Food": 3000,
    "Travel": 2000,
    "Shopping": 3000,
    "Bills": 2500,
    "Health": 1500,
    "Entertainment": 2000
}


# =========================================================
# DATABASE FUNCTIONS
# =========================================================

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db_connection()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()


# Create database when application starts
init_db()


# =========================================================
# LOGIN REQUIRED DECORATOR
# =========================================================

def login_required(route_function):

    @wraps(route_function)
    def wrapper(*args, **kwargs):

        if "user_id" not in session:
            flash("Please login to access your dashboard.", "warning")
            return redirect(url_for("login"))

        return route_function(*args, **kwargs)

    return wrapper


# =========================================================
# LOAD ML MODEL
# =========================================================

model = None

if os.path.exists(MODEL_FILE):
    model = joblib.load(MODEL_FILE)


# =========================================================
# LOAD EXPENSE DATA
# =========================================================

def load_expenses():

    if not os.path.exists(DATA_FILE):
        return pd.DataFrame(
            columns=[
                "Date",
                "Category",
                "Amount",
                "Payment_Mode",
                "Description"
            ]
        )

    data = pd.read_csv(DATA_FILE)

    if not data.empty:
        data["Date"] = pd.to_datetime(data["Date"])

    return data


# =========================================================
# BUDGET ALERT FUNCTION
# =========================================================

def create_budget_alerts(actual_expenses, budgets):

    alerts = []

    for category, budget in budgets.items():

        spent = actual_expenses.get(category, 0)

        percentage = (spent / budget * 100) if budget > 0 else 0

        if percentage >= 100:

            status = "danger"
            message = "Budget Exceeded"

        elif percentage >= 80:

            status = "warning"
            message = "Near Budget Limit"

        else:

            status = "success"
            message = "Within Budget"

        alerts.append({
            "category": category,
            "spent": spent,
            "budget": budget,
            "percentage": min(percentage, 100),
            "status": status,
            "message": message
        })

    return alerts


# =========================================================
# HOME / DASHBOARD
# =========================================================

@app.route("/")
@login_required
def home():

    data = load_expenses()

    if data.empty:

        total_expense = 0
        average_expense = 0
        highest_expense = 0
        transaction_count = 0

        category_expenses = []
        payment_expenses = []
        highest_category = "None"

        recent_expenses = []

    else:

        total_expense = float(data["Amount"].sum())

        average_expense = float(data["Amount"].mean())

        highest_expense = float(data["Amount"].max())

        transaction_count = len(data)

        # Category totals
        category_series = (
            data.groupby("Category")["Amount"]
            .sum()
            .sort_values(ascending=False)
        )

        category_expenses = [
            (category, float(amount))
            for category, amount in category_series.items()
        ]

        if category_expenses:
            highest_category = category_expenses[0][0]
        else:
            highest_category = "None"

        # Payment mode totals
        payment_series = (
            data.groupby("Payment_Mode")["Amount"]
            .sum()
            .sort_values(ascending=False)
        )

        payment_expenses = [
            (payment, float(amount))
            for payment, amount in payment_series.items()
        ]

        # Recent transactions
        recent_expenses = (
            data.tail(5)
            .iloc[::-1]
            .to_dict("records")
        )

    # Actual category spending
    actual_expenses = dict(category_expenses)

    # Budget alerts
    budget_alerts = create_budget_alerts(
        actual_expenses,
        DEFAULT_BUDGETS
    )

    warning_count = sum(
        1 for alert in budget_alerts
        if alert["status"] == "warning"
    )

    danger_count = sum(
        1 for alert in budget_alerts
        if alert["status"] == "danger"
    )

    return render_template(
        "index.html",
        total_expense=total_expense,
        average_expense=average_expense,
        highest_expense=highest_expense,
        transaction_count=transaction_count,
        category_expenses=category_expenses,
        payment_expenses=payment_expenses,
        highest_category=highest_category,
        budget_alerts=budget_alerts,
        warning_count=warning_count,
        danger_count=danger_count,
        recent_expenses=recent_expenses,
        username=session.get("username")
    )


# =========================================================
# SIGNUP
# =========================================================

@app.route("/signup", methods=["GET", "POST"])
def signup():

    if request.method == "POST":

        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        # Check empty fields
        if not username or not email or not password:

            flash("Please fill all fields.", "danger")
            return redirect(url_for("signup"))

        # Check password confirmation
        if password != confirm_password:

            flash("Passwords do not match.", "danger")
            return redirect(url_for("signup"))

        # Minimum password length
        if len(password) < 6:

            flash("Password must contain at least 6 characters.", "danger")
            return redirect(url_for("signup"))

        # Hash password
        hashed_password = generate_password_hash(password)

        conn = get_db_connection()

        try:

            conn.execute(
                """
                INSERT INTO users
                (username, email, password)
                VALUES (?, ?, ?)
                """,
                (username, email, hashed_password)
            )

            conn.commit()

            flash(
                "Account created successfully. Please login.",
                "success"
            )

            return redirect(url_for("login"))

        except sqlite3.IntegrityError:

            flash(
                "Username or email already exists.",
                "danger"
            )

            return redirect(url_for("signup"))

        finally:

            conn.close()

    return render_template("signup.html")


# =========================================================
# LOGIN
# =========================================================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        conn = get_db_connection()

        user = conn.execute(
            """
            SELECT *
            FROM users
            WHERE username = ?
            """,
            (username,)
        ).fetchone()

        conn.close()

        if user and check_password_hash(
            user["password"],
            password
        ):

            session["user_id"] = user["id"]
            session["username"] = user["username"]

            flash(
                "Login successful!",
                "success"
            )

            return redirect(url_for("home"))

        else:

            flash(
                "Invalid username or password.",
                "danger"
            )

            return redirect(url_for("login"))

    return render_template("login.html")


# =========================================================
# LOGOUT
# =========================================================

@app.route("/logout")
def logout():

    session.clear()

    flash(
        "You have been logged out.",
        "success"
    )

    return redirect(url_for("login"))


# =========================================================
# PREDICT
# =========================================================

@app.route("/predict", methods=["GET", "POST"])
@login_required
def predict():

    prediction = None

    if request.method == "POST":

        date = request.form.get("date")
        category = request.form.get("category")

        if model is not None and date and category:

            date = pd.to_datetime(date)

            category_codes = {
                "Bills": 0,
                "Entertainment": 1,
                "Food": 2,
                "Health": 3,
                "Shopping": 4,
                "Travel": 5
            }

            category_code = category_codes.get(
                category,
                0
            )

            input_data = [[
                date.day,
                date.month,
                date.dayofweek,
                category_code
            ]]

            prediction = model.predict(input_data)[0]

    return render_template(
        "predict.html",
        prediction=prediction
    )


# =========================================================
# BUDGET
# =========================================================

@app.route("/budget")
@login_required
def budget():

    data = load_expenses()

    if data.empty:

        actual_expenses = {}

    else:

        category_series = (
            data.groupby("Category")["Amount"]
            .sum()
        )

        actual_expenses = category_series.to_dict()

    budget_alerts = create_budget_alerts(
        actual_expenses,
        DEFAULT_BUDGETS
    )

    return render_template(
        "budget.html",
        budget_alerts=budget_alerts,
        budgets=DEFAULT_BUDGETS
    )


# =========================================================
# ADD EXPENSE
# =========================================================

@app.route("/add-expense", methods=["GET", "POST"])
@login_required
def add_expense():

    if request.method == "POST":

        date = request.form.get("date")
        category = request.form.get("category")
        amount = request.form.get("amount")
        payment_mode = request.form.get("payment_mode")
        description = request.form.get("description")

        new_expense = pd.DataFrame([{
            "Date": date,
            "Category": category,
            "Amount": float(amount),
            "Payment_Mode": payment_mode,
            "Description": description
        }])

        if os.path.exists(DATA_FILE):

            data = pd.read_csv(DATA_FILE)

            data = pd.concat(
                [data, new_expense],
                ignore_index=True
            )

        else:

            data = new_expense

        data.to_csv(
            DATA_FILE,
            index=False
        )

        flash(
            "Expense added successfully!",
            "success"
        )

        return redirect(url_for("home"))

    return render_template("add_expense.html")


# =========================================================
# HISTORY
# =========================================================

@app.route("/history")
@login_required
def history():

    data = load_expenses()

    if data.empty:
        expenses = []
    else:
        expenses = (
            data.iloc[::-1]
            .to_dict("records")
        )

    return render_template(
        "history.html",
        expenses=expenses
    )


# =========================================================
# RUN APPLICATION
# =========================================================

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)