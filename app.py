```python
from flask import Flask, render_template, request, redirect, url_for, flash
import pandas as pd
import os
import joblib
from datetime import datetime


# ============================================================
# FLASK APPLICATION
# ============================================================

app = Flask(__name__)

# Secret key is only needed for Flask flash messages
app.secret_key = "smart-money-secret-key"


# ============================================================
# FILE PATHS
# ============================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

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


# ============================================================
# LOAD MACHINE LEARNING MODEL
# ============================================================

model = None

try:
    model = joblib.load(MODEL_FILE)
    print("ML model loaded successfully.")
except Exception as e:
    print("Warning: ML model could not be loaded.")
    print("Error:", e)


# ============================================================
# CATEGORY CODES
# These must match the codes used while training the model.
# ============================================================

CATEGORY_CODES = {
    "Bills": 0,
    "Entertainment": 1,
    "Food": 2,
    "Health": 3,
    "Shopping": 4,
    "Travel": 5
}


# ============================================================
# HELPER FUNCTION - LOAD EXPENSE DATA
# ============================================================

def load_expenses():
    """
    Load expenses from CSV.
    If the CSV does not exist, create an empty DataFrame.
    """

    try:
        df = pd.read_csv(DATA_FILE)

        if df.empty:
            return pd.DataFrame(
                columns=[
                    "Date",
                    "Category",
                    "Amount",
                    "Payment_Mode",
                    "Description"
                ]
            )

        return df

    except FileNotFoundError:

        return pd.DataFrame(
            columns=[
                "Date",
                "Category",
                "Amount",
                "Payment_Mode",
                "Description"
            ]
        )

    except Exception as e:

        print("Error loading expenses:", e)

        return pd.DataFrame(
            columns=[
                "Date",
                "Category",
                "Amount",
                "Payment_Mode",
                "Description"
            ]
        )


# ============================================================
# HOME / DASHBOARD
# ============================================================

@app.route("/")
def home():

    df = load_expenses()

    # --------------------------------------------------------
    # Empty data handling
    # --------------------------------------------------------

    if df.empty:

        total_expense = 0
        average_expense = 0
        highest_expense = 0
        total_entries = 0

        category_expenses = []
        payment_expenses = []
        recent_transactions = []

        budget_alerts = []

        top_category = "No data"
        budget_status = "No data"

    else:

        # Make sure Amount is numeric
        df["Amount"] = pd.to_numeric(
            df["Amount"],
            errors="coerce"
        ).fillna(0)

        # ----------------------------------------------------
        # Expense overview
        # ----------------------------------------------------

        total_expense = df["Amount"].sum()

        average_expense = df["Amount"].mean()

        highest_expense = df["Amount"].max()

        total_entries = len(df)

        # ----------------------------------------------------
        # Category spending
        # ----------------------------------------------------

        category_data = (
            df.groupby("Category")["Amount"]
            .sum()
            .sort_values(ascending=False)
        )

        category_expenses = [
            (category, float(amount))
            for category, amount in category_data.items()
        ]

        # ----------------------------------------------------
        # Payment mode spending
        # ----------------------------------------------------

        payment_data = (
            df.groupby("Payment_Mode")["Amount"]
            .sum()
            .sort_values(ascending=False)
        )

        payment_expenses = [
            (payment, float(amount))
            for payment, amount in payment_data.items()
        ]

        # ----------------------------------------------------
        # Recent transactions
        # ----------------------------------------------------

        recent_df = df.copy()

        try:
            recent_df["Date"] = pd.to_datetime(
                recent_df["Date"],
                errors="coerce"
            )

            recent_df = recent_df.sort_values(
                "Date",
                ascending=False
            )

        except Exception:
            pass

        recent_transactions = recent_df.head(5).to_dict(
            orient="records"
        )

        # ----------------------------------------------------
        # Budget limits
        # ----------------------------------------------------

        budget_limits = {
            "Food": 3000,
            "Travel": 2000,
            "Shopping": 3000,
            "Bills": 2500,
            "Health": 1500,
            "Entertainment": 2000
        }

        budget_alerts = []

        for category, limit in budget_limits.items():

            spent = float(
                category_data.get(category, 0)
            )

            percentage = (
                (spent / limit) * 100
                if limit > 0
                else 0
            )

            if percentage >= 90:
                status = "Critical"

            elif percentage >= 75:
                status = "Warning"

            else:
                status = "Good"

            budget_alerts.append({
                "category": category,
                "spent": spent,
                "limit": limit,
                "percentage": round(percentage, 1),
                "status": status
            })

        # ----------------------------------------------------
        # Top category
        # ----------------------------------------------------

        if len(category_data) > 0:
            top_category = category_data.idxmax()
        else:
            top_category = "No data"

        # ----------------------------------------------------
        # Overall budget status
        # ----------------------------------------------------

        warning_count = sum(
            1
            for item in budget_alerts
            if item["status"] in ["Warning", "Critical"]
        )

        if warning_count == 0:
            budget_status = "Good"

        elif warning_count <= 2:
            budget_status = "Attention"

        else:
            budget_status = "High Spending"

    return render_template(
        "index.html",
        total_expense=total_expense,
        average_expense=average_expense,
        highest_expense=highest_expense,
        total_entries=total_entries,
        category_expenses=category_expenses,
        payment_expenses=payment_expenses,
        recent_transactions=recent_transactions,
        budget_alerts=budget_alerts,
        top_category=top_category,
        budget_status=budget_status
    )


# ============================================================
# PREDICT EXPENSE
# ============================================================

@app.route("/predict", methods=["GET", "POST"])
def predict():

    prediction = None

    if request.method == "POST":

        try:

            date = request.form.get("date")
            category = request.form.get("category")

            # ------------------------------------------------
            # Validate input
            # ------------------------------------------------

            if not date or not category:

                flash(
                    "Please select a date and category.",
                    "warning"
                )

                return render_template(
                    "predict.html",
                    prediction=None
                )

            # ------------------------------------------------
            # Convert date
            # ------------------------------------------------

            selected_date = pd.to_datetime(date)

            day = selected_date.day

            month = selected_date.month

            day_of_week = selected_date.dayofweek

            # ------------------------------------------------
            # Category code
            # ------------------------------------------------

            category_code = CATEGORY_CODES.get(
                category,
                0
            )

            # ------------------------------------------------
            # ML prediction
            # ------------------------------------------------

            if model is not None:

                features = [[
                    day,
                    month,
                    day_of_week,
                    category_code
                ]]

                prediction = model.predict(
                    features
                )[0]

                prediction = round(
                    float(prediction),
                    2
                )

            else:

                flash(
                    "Prediction model is not available.",
                    "danger"
                )

        except Exception as e:

            print("Prediction error:", e)

            flash(
                "Unable to make prediction. Please check your input.",
                "danger"
            )

    return render_template(
        "predict.html",
        prediction=prediction
    )


# ============================================================
# BUDGET PLANNER
# ============================================================

@app.route("/budget")
def budget():

    df = load_expenses()

    # --------------------------------------------------------
    # Convert Amount to numeric
    # --------------------------------------------------------

    if not df.empty:

        df["Amount"] = pd.to_numeric(
            df["Amount"],
            errors="coerce"
        ).fillna(0)

        category_data = (
            df.groupby("Category")["Amount"]
            .sum()
        )

    else:

        category_data = pd.Series(dtype=float)

    # --------------------------------------------------------
    # Default budget limits
    # --------------------------------------------------------

    budget_limits = {
        "Food": 3000,
        "Travel": 2000,
        "Shopping": 3000,
        "Bills": 2500,
        "Health": 1500,
        "Entertainment": 2000
    }

    budgets = []

    for category, limit in budget_limits.items():

        spent = float(
            category_data.get(category, 0)
        )

        remaining = limit - spent

        percentage = (
            (spent / limit) * 100
            if limit > 0
            else 0
        )

        budgets.append({
            "category": category,
            "budget": limit,
            "spent": spent,
            "remaining": remaining,
            "percentage": round(
                percentage,
                1
            )
        })

    return render_template(
        "budget.html",
        budgets=budgets
    )


# ============================================================
# ADD EXPENSE
# ============================================================

@app.route("/add-expense", methods=["GET", "POST"])
def add_expense():

    if request.method == "POST":

        try:

            date = request.form.get("date")
            category = request.form.get("category")
            amount = request.form.get("amount")
            payment_mode = request.form.get("payment_mode")
            description = request.form.get("description")

            # ------------------------------------------------
            # Validation
            # ------------------------------------------------

            if not date:
                flash(
                    "Please select a date.",
                    "warning"
                )

                return redirect(
                    url_for("add_expense")
                )

            if not category:
                flash(
                    "Please select a category.",
                    "warning"
                )

                return redirect(
                    url_for("add_expense")
                )

            if not amount:
                flash(
                    "Please enter an amount.",
                    "warning"
                )

                return redirect(
                    url_for("add_expense")
                )

            try:

                amount = float(amount)

            except ValueError:

                flash(
                    "Amount must be a valid number.",
                    "warning"
                )

                return redirect(
                    url_for("add_expense")
                )

            if amount <= 0:

                flash(
                    "Amount must be greater than zero.",
                    "warning"
                )

                return redirect(
                    url_for("add_expense")
                )

            # ------------------------------------------------
            # Create expense record
            # ------------------------------------------------

            new_expense = pd.DataFrame([{
                "Date": date,
                "Category": category,
                "Amount": amount,
                "Payment_Mode": payment_mode,
                "Description": description
            }])

            # ------------------------------------------------
            # Save to CSV
            # ------------------------------------------------

            os.makedirs(
                os.path.dirname(DATA_FILE),
                exist_ok=True
            )

            if os.path.exists(DATA_FILE):

                existing_data = pd.read_csv(
                    DATA_FILE
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

            return redirect(
                url_for("home")
            )

        except Exception as e:

            print("Add expense error:", e)

            flash(
                "Unable to add expense.",
                "danger"
            )

            return redirect(
                url_for("add_expense")
            )

    return render_template(
        "add_expense.html"
    )


# ============================================================
# EXPENSE HISTORY
# ============================================================

@app.route("/history")
def history():

    df = load_expenses()

    if not df.empty:

        # Convert amount
        df["Amount"] = pd.to_numeric(
            df["Amount"],
            errors="coerce"
        ).fillna(0)

        # Sort newest first
        try:

            df["Date"] = pd.to_datetime(
                df["Date"],
                errors="coerce"
            )

            df = df.sort_values(
                "Date",
                ascending=False
            )

            # Convert date back to readable format
            df["Date"] = df["Date"].dt.strftime(
                "%Y-%m-%d"
            )

        except Exception:
            pass

    expenses = df.to_dict(
        orient="records"
    )

    return render_template(
        "history.html",
        expenses=expenses
    )


# ============================================================
# OPTIONAL LOGIN ROUTES
# ------------------------------------------------------------
# These routes are kept so existing login/signup HTML files
# don't cause problems, but the dashboard DOES NOT require
# login.
# ============================================================

@app.route("/login")
def login():

    return render_template(
        "login.html"
    )


@app.route("/signup")
def signup():

    return render_template(
        "signup.html"
    )


# ============================================================
# HEALTH CHECK
# ------------------------------------------------------------
# Useful for checking whether the Render server is running.
# ============================================================

@app.route("/health")
def health():

    return "Smart Money is running successfully!"


# ============================================================
# RUN APPLICATION
# ============================================================

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )
```
