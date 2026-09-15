from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    session
)

import pandas as pd
import os
import joblib
import sqlite3

from functools import wraps
from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)


# =========================================================
# FLASK APP
# =========================================================

app = Flask(__name__)

app.secret_key = os.environ.get(
    "SECRET_KEY",
    "smart-money-secret-key"
)


# =========================================================
# PROJECT PATHS
# =========================================================

BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

DATA_FILE = os.path.join(
    BASE_DIR,
    "data",
    "expenses.csv"
)

MODEL_FILE = os.path.join(
    BASE_DIR,
    "models",
    "expense_prediction_model.pkl"
)

DATABASE_FILE = os.path.join(
    BASE_DIR,
    "users.db"
)


# =========================================================
# LOAD ML MODEL
# =========================================================

model = None

try:

    model = joblib.load(
        MODEL_FILE
    )

    print(
        "ML model loaded successfully."
    )

except Exception as e:

    print(
        "Warning: ML model could not be loaded."
    )

    print(
        "Error:",
        e
    )


# =========================================================
# CATEGORY CODES
# IMPORTANT:
# These must match the model training codes.
# =========================================================

CATEGORY_CODES = {

    "Bills": 0,

    "Entertainment": 1,

    "Food": 2,

    "Health": 3,

    "Shopping": 4,

    "Travel": 5

}


# =========================================================
# BUDGET LIMITS
# =========================================================

BUDGET_LIMITS = {

    "Food": 3000,

    "Travel": 2000,

    "Shopping": 3000,

    "Bills": 2500,

    "Health": 1500,

    "Entertainment": 2000

}


# =========================================================
# DATABASE CONNECTION
# =========================================================

def get_db_connection():

    connection = sqlite3.connect(
        DATABASE_FILE
    )

    connection.row_factory = sqlite3.Row

    return connection


# =========================================================
# INITIALIZE DATABASE
# =========================================================

def init_db():
    connection = get_db_connection()

    # Users table
    connection.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            email TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL
        )
    """)

    # Savings Goal table
    connection.execute("""
        CREATE TABLE IF NOT EXISTS savings_goals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL UNIQUE,
            goal_name TEXT NOT NULL,
            target_amount REAL NOT NULL,
            saved_amount REAL NOT NULL DEFAULT 0,
            deadline TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    connection.commit()
    connection.close()


init_db()

# =========================================================
# LOGIN REQUIRED
# =========================================================

def login_required(function):

    @wraps(function)
    def decorated_function(*args, **kwargs):

        if "user_id" not in session:

            flash(
                "Please login to continue.",
                "error"
            )

            return redirect(
                url_for("login")
            )

        return function(
            *args,
            **kwargs
        )

    return decorated_function


# =========================================================
# LOAD EXPENSE DATA
# =========================================================

def load_expenses():

    try:

        if not os.path.exists(
            DATA_FILE
        ):

            return pd.DataFrame(
                columns=[
                    "Date",
                    "Category",
                    "Amount",
                    "Payment_Mode",
                    "Description"
                ]
            )


        df = pd.read_csv(
            DATA_FILE
        )


        required_columns = [

            "Date",

            "Category",

            "Amount",

            "Payment_Mode",

            "Description"

        ]


        for column in required_columns:

            if column not in df.columns:

                df[column] = ""


        df["Date"] = pd.to_datetime(
            df["Date"],
            errors="coerce"
        )


        df["Amount"] = pd.to_numeric(
            df["Amount"],
            errors="coerce"
        ).fillna(0)


        df["Category"] = (
            df["Category"]
            .fillna("")
            .astype(str)
            .str.strip()
        )


        df["Payment_Mode"] = (
            df["Payment_Mode"]
            .fillna("")
            .astype(str)
            .str.strip()
        )


        df["Description"] = (
            df["Description"]
            .fillna("")
            .astype(str)
            .str.strip()
        )


        return df


    except Exception as e:

        print(
            "Error loading expenses:",
            e
        )

        return pd.DataFrame(
            columns=[
                "Date",
                "Category",
                "Amount",
                "Payment_Mode",
                "Description"
            ]
        )


# =========================================================
# HOME / MODERN DASHBOARD
# =========================================================

@app.route("/")
@login_required
def home():

    df = load_expenses()

    # ==============================
    # SAVINGS GOAL DATA
    # ==============================

    user_id = session["user_id"]

    connection = get_db_connection()

    savings_goal = connection.execute(
        """
        SELECT *
        FROM savings_goals
        WHERE user_id = ?
        """,
        (user_id,)
    ).fetchone()

    connection.close()

    goal_name = None
    goal_target = 0
    goal_saved = 0
    goal_deadline = None
    goal_percentage = 0
    goal_remaining = 0

    if savings_goal:
        goal_name = savings_goal["goal_name"]
        goal_target = float(savings_goal["target_amount"])
        goal_saved = float(savings_goal["saved_amount"])
        goal_deadline = savings_goal["deadline"]

        if goal_target > 0:
            goal_percentage = (goal_saved / goal_target) * 100

        goal_percentage = min(goal_percentage, 100)
        goal_remaining = max(goal_target - goal_saved, 0)



    # =====================================================
    # BASIC STATISTICS
    # =====================================================

    total_expense = float(
        df["Amount"].sum()
    )


    average_expense = (

        float(
            df["Amount"].mean()
        )

        if len(df) > 0

        else 0

    )


    highest_expense = (

        float(
            df["Amount"].max()
        )

        if len(df) > 0

        else 0

    )


    total_entries = len(df)


    # =====================================================
    # CATEGORY EXPENSES
    # =====================================================

    if len(df) > 0:

        category_data = (

            df.groupby(
                "Category"
            )["Amount"]

            .sum()

            .sort_values(
                ascending=False
            )

        )


        category_expenses = [

            (
                str(category),
                float(amount)
            )

            for category, amount
            in category_data.items()

        ]

    else:

        category_expenses = []


    # =====================================================
    # CATEGORY PERCENTAGES
    # =====================================================

    category_percentages = []


    for category, amount in category_expenses:

        if total_expense > 0:

            percentage = (
                amount /
                total_expense *
                100
            )

        else:

            percentage = 0


        category_percentages.append({

            "category": category,

            "amount": amount,

            "percentage": round(
                percentage,
                1
            )

        })


    # =====================================================
    # PAYMENT MODE EXPENSES
    # =====================================================

    if len(df) > 0:

        payment_data = (

            df.groupby(
                "Payment_Mode"
            )["Amount"]

            .sum()

            .sort_values(
                ascending=False
            )

        )


        payment_expenses = [

            (
                str(payment),
                float(amount)
            )

            for payment, amount
            in payment_data.items()

        ]

    else:

        payment_expenses = []


    # =====================================================
    # MONTHLY SPENDING
    # =====================================================

    monthly_spending = {

        month: 0

        for month in range(
            1,
            13
        )

    }


    if len(df) > 0:

        valid_dates = df[
            df["Date"].notna()
        ].copy()


        if len(valid_dates) > 0:

            monthly_data = (

                valid_dates

                .groupby(
                    valid_dates["Date"].dt.month
                )["Amount"]

                .sum()

            )


            for month, amount in monthly_data.items():

                monthly_spending[
                    int(month)
                ] = round(
                    float(amount),
                    2
                )


    # =====================================================
    # MONTHLY SPENDING LABELS
    # =====================================================

    monthly_labels = [

        "Jan",
        "Feb",
        "Mar",
        "Apr",
        "May",
        "Jun",
        "Jul",
        "Aug",
        "Sep",
        "Oct",
        "Nov",
        "Dec"

    ]


    monthly_values = [

        monthly_spending[
            month
        ]

        for month in range(
            1,
            13
        )

    ]


    # =====================================================
    # RECENT TRANSACTIONS
    # =====================================================

    recent_expenses = []


    if len(df) > 0:

        recent_df = (

            df.sort_values(
                by="Date",
                ascending=False
            )

            .head(5)

            .copy()

        )


        for _, row in recent_df.iterrows():

            recent_expenses.append({

                "Date": (

                    row["Date"].strftime(
                        "%d %b %Y"
                    )

                    if pd.notna(
                        row["Date"]
                    )

                    else ""

                ),

                "Category": str(
                    row["Category"]
                ),

                "Amount": float(
                    row["Amount"]
                ),

                "Payment_Mode": str(
                    row["Payment_Mode"]
                ),

                "Description": str(
                    row["Description"]
                )

            })


    # =====================================================
    # BUDGET ALERTS
    # =====================================================

    budget_alerts = []


    for category, limit in BUDGET_LIMITS.items():

        if len(df) > 0:

            category_spending = df[

                df["Category"]
                .astype(str)
                .str.strip()
                .str.lower()

                == category.lower()

            ]["Amount"].sum()

        else:

            category_spending = 0


        spent = float(
            category_spending
        )


        percentage = (

            (
                spent /
                limit *
                100
            )

            if limit > 0

            else 0

        )


        if percentage >= 100:

            status = "Exceeded"

        elif percentage >= 80:

            status = "Warning"

        else:

            status = "Good"


        budget_alerts.append({

            "category": category,

            "spent": spent,

            "limit": float(limit),

            "percent": round(
                percentage,
                2
            ),

            "status": status

        })


    # =====================================================
    # TOP CATEGORY
    # =====================================================

    if category_expenses:

        top_category = (
            category_expenses[0][0]
        )

        top_category_amount = (
            category_expenses[0][1]
        )

    else:

        top_category = "No Data"

        top_category_amount = 0


    # =====================================================
    # OVERALL BUDGET STATUS
    # =====================================================

    exceeded_count = sum(

        1

        for item in budget_alerts

        if item["status"] == "Exceeded"

    )


    warning_count = sum(

        1

        for item in budget_alerts

        if item["status"] == "Warning"

    )


    if exceeded_count > 0:

        overall_status = (
            "Budget Exceeded"
        )

    elif warning_count > 0:

        overall_status = (
            "Needs Attention"
        )

    else:

        overall_status = (
            "Within Budget"
        )


    # =====================================================
    # AI NEXT-MONTH PREDICTION
    #
    # We take the existing transaction pattern,
    # move each transaction approximately one month
    # forward, and ask the trained ML model to predict
    # the future amount.
    # =====================================================

    dashboard_prediction = None


    if (
        model is not None
        and len(df) > 0
    ):

        try:

            prediction_values = []


            prediction_df = df[
                df["Date"].notna()
            ].copy()


            for _, row in prediction_df.iterrows():

                future_date = (
                    row["Date"]
                    + pd.DateOffset(
                        months=1
                    )
                )


                category = str(
                    row["Category"]
                ).strip()


                category_code = (
                    CATEGORY_CODES.get(
                        category,
                        0
                    )
                )


                input_data = [[

                    future_date.day,

                    future_date.month,

                    future_date.dayofweek,

                    category_code

                ]]


                predicted_amount = (
                    model.predict(
                        input_data
                    )[0]
                )


                prediction_values.append(

                    max(
                        0,
                        float(
                            predicted_amount
                        )
                    )

                )


            if prediction_values:

                dashboard_prediction = round(

                    sum(
                        prediction_values
                    ),

                    2

                )


        except Exception as e:

            print(
                "Dashboard prediction error:",
                e
            )


    # =====================================================
    # FALLBACK AI PREDICTION
    # =====================================================

    if dashboard_prediction is None:

        if total_expense > 0:

            dashboard_prediction = round(

                total_expense * 1.10,

                2

            )

        else:

            dashboard_prediction = 0


    # =====================================================
    # USER INFORMATION
    # =====================================================

    username = session.get(
        "username",
        "User"
    )


    email = session.get(
        "email",
        ""
    )

    return render_template(
        "index.html",
        username=username,
        email=email,
        total_expense=total_expense,
        average_expense=average_expense,
        highest_expense=highest_expense,
        total_entries=total_entries,
        category_expenses=category_expenses,
        category_percentages=category_percentages,
        payment_expenses=payment_expenses,
        recent_expenses=recent_expenses,
        budget_alerts=budget_alerts,
        top_category=top_category,
        top_category_amount=top_category_amount,
        overall_status=overall_status,
        monthly_spending=monthly_spending,
        monthly_labels=monthly_labels,
        monthly_values=monthly_values,
        dashboard_prediction=dashboard_prediction,
        goal_name=goal_name,
        goal_target=goal_target,
        goal_saved=goal_saved,
        goal_deadline=goal_deadline,
        goal_percentage=goal_percentage,
        goal_remaining=goal_remaining
    )

# =========================================================
# SIGNUP
# =========================================================

@app.route(
    "/signup",
    methods=["GET", "POST"]
)
def signup():

    if "user_id" in session:

        return redirect(
            url_for("home")
        )


    if request.method == "POST":

        username = request.form.get(
            "username",
            ""
        ).strip()


        email = request.form.get(
            "email",
            ""
        ).strip().lower()


        password = request.form.get(
            "password",
            ""
        )


        confirm_password = request.form.get(
            "confirm_password",
            ""
        )


        # -------------------------------------------------
        # VALIDATION
        # -------------------------------------------------

        if not username or not email or not password:

            flash(
                "Please fill in all fields.",
                "error"
            )

            return render_template(
                "signup.html"
            )


        if password != confirm_password:

            flash(
                "Passwords do not match.",
                "error"
            )

            return render_template(
                "signup.html"
            )


        if len(password) < 6:

            flash(
                "Password must contain at least 6 characters.",
                "error"
            )

            return render_template(
                "signup.html"
            )


        # -------------------------------------------------
        # CREATE USER
        # -------------------------------------------------

        try:

            connection = (
                get_db_connection()
            )


            existing_user = connection.execute(

                """
                SELECT id
                FROM users
                WHERE username = ?
                   OR email = ?
                """,

                (
                    username,
                    email
                )

            ).fetchone()


            if existing_user:

                connection.close()


                flash(
                    "Username or email already exists.",
                    "error"
                )


                return render_template(
                    "signup.html"
                )


            hashed_password = (
                generate_password_hash(
                    password
                )
            )


            connection.execute(

                """
                INSERT INTO users
                (username, email, password)
                VALUES (?, ?, ?)
                """,

                (
                    username,
                    email,
                    hashed_password
                )

            )


            connection.commit()

            connection.close()


            flash(
                "Account created successfully. Please login.",
                "success"
            )


            return redirect(
                url_for("login")
            )


        except Exception as e:

            flash(
                "Signup error: " + str(e),
                "error"
            )


    return render_template(
        "signup.html"
    )


# =========================================================
# LOGIN
# =========================================================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        connection = get_db_connection()

        user = connection.execute(
            """
            SELECT * FROM users
            WHERE username = ? AND email = ?
            """,
            (username, email)
        ).fetchone()

        connection.close()

        if user and check_password_hash(
            user["password"],
            password
        ):

            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session["email"] = user["email"]

            return redirect(url_for("home"))

        flash(
            "Invalid username, email, or password.",
            "error"
        )

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


    return redirect(
        url_for("login")
    )


# =========================================================
# PREDICT EXPENSE
# =========================================================

@app.route(
    "/predict",
    methods=["GET", "POST"]
)
@login_required
def predict():

    prediction = None

    selected_date = ""

    selected_category = ""


    if request.method == "POST":

        selected_date = request.form.get(
            "date",
            ""
        )


        selected_category = request.form.get(
            "category",
            ""
        )


        try:

            if not selected_date:

                flash(
                    "Please select a date.",
                    "error"
                )


                return render_template(

                    "predict.html",

                    prediction=prediction,

                    selected_date=selected_date,

                    selected_category=selected_category

                )


            if not selected_category:

                flash(
                    "Please select a category.",
                    "error"
                )


                return render_template(

                    "predict.html",

                    prediction=prediction,

                    selected_date=selected_date,

                    selected_category=selected_category

                )


            date_value = pd.to_datetime(
                selected_date
            )


            day = date_value.day

            month = date_value.month

            day_of_week = (
                date_value.dayofweek
            )


            category_code = (
                CATEGORY_CODES.get(
                    selected_category,
                    0
                )
            )


            input_data = [[

                day,

                month,

                day_of_week,

                category_code

            ]]


            if model is None:

                flash(
                    "Prediction model is not available.",
                    "error"
                )

            else:

                result = model.predict(
                    input_data
                )[0]


                prediction = round(
                    float(result),
                    2
                )


        except Exception as e:

            flash(
                "Prediction error: " + str(e),
                "error"
            )


    return render_template(

        "predict.html",

        prediction=prediction,

        selected_date=selected_date,

        selected_category=selected_category

    )


# =========================================================
# BUDGET
# =========================================================

@app.route("/budget")
@login_required
def budget():

    df = load_expenses()

    budget_data = []


    for category, limit in BUDGET_LIMITS.items():

        if len(df) > 0:

            spent = df[

                df["Category"]
                .astype(str)
                .str.strip()
                .str.lower()

                == category.lower()

            ]["Amount"].sum()

        else:

            spent = 0


        spent = float(
            spent
        )


        remaining = float(
            limit - spent
        )


        percentage = (

            (
                spent /
                limit *
                100
            )

            if limit > 0

            else 0

        )


        if percentage >= 100:

            status = "Exceeded"

        elif percentage >= 80:

            status = "Warning"

        else:

            status = "Good"


        budget_data.append({

            "category": category,

            "budget": float(limit),

            "spent": spent,

            "remaining": remaining,

            "percentage": round(
                percentage,
                2
            ),

            "status": status

        })


    return render_template(

        "budget.html",

        budget_data=budget_data,

        budget_limits=BUDGET_LIMITS

    )


# =========================================================
# ADD EXPENSE
# =========================================================

@app.route(
    "/add-expense",
    methods=["GET", "POST"]
)
@login_required
def add_expense():

    if request.method == "POST":

        date = request.form.get(
            "date",
            ""
        ).strip()


        category = request.form.get(
            "category",
            ""
        ).strip()


        amount = request.form.get(
            "amount",
            ""
        ).strip()


        payment_mode = request.form.get(
            "payment_mode",
            ""
        ).strip()


        description = request.form.get(
            "description",
            ""
        ).strip()


        # -------------------------------------------------
        # VALIDATION
        # -------------------------------------------------

        if not date:

            flash(
                "Please select a date.",
                "error"
            )

            return redirect(
                url_for("add_expense")
            )


        if not category:

            flash(
                "Please select a category.",
                "error"
            )

            return redirect(
                url_for("add_expense")
            )


        if not amount:

            flash(
                "Please enter an amount.",
                "error"
            )

            return redirect(
                url_for("add_expense")
            )


        if not payment_mode:

            flash(
                "Please select a payment mode.",
                "error"
            )

            return redirect(
                url_for("add_expense")
            )


        try:

            amount_value = float(
                amount
            )


            if amount_value <= 0:

                raise ValueError


        except ValueError:

            flash(
                "Please enter a valid amount.",
                "error"
            )

            return redirect(
                url_for("add_expense")
            )


        # -------------------------------------------------
        # NEW EXPENSE
        # -------------------------------------------------

        new_expense = pd.DataFrame([{

            "Date": date,

            "Category": category,

            "Amount": amount_value,

            "Payment_Mode": payment_mode,

            "Description": description

        }])


        # -------------------------------------------------
        # SAVE TO CSV
        # -------------------------------------------------

        try:

            if os.path.exists(
                DATA_FILE
            ):

                existing_data = pd.read_csv(
                    DATA_FILE
                )


                columns = [

                    "Date",

                    "Category",

                    "Amount",

                    "Payment_Mode",

                    "Description"

                ]


                for column in columns:

                    if column not in existing_data.columns:

                        existing_data[column] = ""


                existing_data = (
                    existing_data[columns]
                )


                updated_data = pd.concat(

                    [

                        existing_data,

                        new_expense

                    ],

                    ignore_index=True

                )

            else:

                updated_data = new_expense


            updated_data.to_csv(

                DATA_FILE,

                index=False

            )


            flash(

                "Expense added successfully!",

                "success"

            )


        except Exception as e:

            flash(

                "Could not save expense: "
                + str(e),

                "error"

            )


        return redirect(
            url_for("home")
        )


    return render_template(
        "add_expense.html"
    )


# =========================================================
# EXPENSE HISTORY
# =========================================================

@app.route("/history")
@login_required
def history():

    df = load_expenses()

    expenses = []


    if len(df) > 0:

        df = df.sort_values(

            by="Date",

            ascending=False

        )


        for _, row in df.iterrows():

            expenses.append({

                "Date": (

                    row["Date"].strftime(
                        "%Y-%m-%d"
                    )

                    if pd.notna(
                        row["Date"]
                    )

                    else ""

                ),

                "Category": str(
                    row["Category"]
                ),

                "Amount": float(
                    row["Amount"]
                ),

                "Payment_Mode": str(
                    row["Payment_Mode"]
                ),

                "Description": str(
                    row["Description"]
                )

            })


    return render_template(

        "history.html",

        expenses=expenses

    )


# =========================================================
# HEALTH CHECK
# =========================================================

@app.route("/health")
def health():

    return (
        "Smart Money is running successfully!"
    )
#======================================================
# SAVINGS GOAL
#======================================================

@app.route("/savings-goal", methods=["GET", "POST"])
@login_required
def savings_goal():

    user_id = session["user_id"]

    if request.method == "POST":

        goal_name = request.form.get("goal_name", "").strip()
        goal_target = request.form.get("goal_target", "0").strip()
        goal_saved = request.form.get("goal_saved", "0").strip()
        goal_deadline = request.form.get("goal_deadline", "").strip()

        if not goal_name:
            flash("Please enter a savings goal name.", "error")
            return redirect(url_for("savings_goal"))

        try:
            goal_target = float(goal_target)
            goal_saved = float(goal_saved)

            if goal_target <= 0:
                raise ValueError

            if goal_saved < 0:
                raise ValueError

        except Exception:
            flash("Please enter valid goal amounts.", "error")
            return redirect(url_for("savings_goal"))

        connection = get_db_connection()

        existing_goal = connection.execute(
            """
            SELECT id FROM savings_goals
            WHERE user_id = ?
            """,
            (user_id,)
        ).fetchone()

        if existing_goal:
            connection.execute(
                """
                UPDATE savings_goals
                SET goal_name = ?,
                    target_amount = ?,
                    saved_amount = ?,
                    deadline = ?
                WHERE user_id = ?
                """,
                (
                    goal_name,
                    goal_target,
                    goal_saved,
                    goal_deadline,
                    user_id
                )
            )
        else:
            connection.execute(
                """
                INSERT INTO savings_goals
                (user_id, goal_name, target_amount, saved_amount, deadline)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    goal_name,
                    goal_target,
                    goal_saved,
                    goal_deadline
                )
            )

        connection.commit()
        connection.close()

        flash("Savings goal saved successfully!", "success")
        return redirect(url_for("home"))

    # GET request: load existing goal for prefill
    connection = get_db_connection()
    existing_goal = connection.execute(
        """
        SELECT * FROM savings_goals
        WHERE user_id = ?
        """,
        (user_id,)
    ).fetchone()
    connection.close()

    goal_name = existing_goal["goal_name"] if existing_goal else ""
    goal_target = existing_goal["target_amount"] if existing_goal else ""
    goal_saved = existing_goal["saved_amount"] if existing_goal else ""
    goal_deadline = existing_goal["deadline"] if existing_goal else ""

    return render_template(
        "savings.html",
        goal_name=goal_name,
        goal_target=goal_target,
        goal_saved=goal_saved,
        goal_deadline=goal_deadline
    )

# =========================================================
# RUN APPLICATION
# =========================================================

if __name__ == "__main__":

    app.run(

        host="0.0.0.0",

        port=5000,

        debug=True

    )