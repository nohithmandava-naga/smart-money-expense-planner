import pandas as pd

# Load expense dataset
data = pd.read_csv("data/expenses.csv")

print("Expense data loaded successfully!")
print(data.head())

# Calculate actual expenses for each category
actual_expenses = data.groupby("Category")["Amount"].sum()

print("\nActual Expenses by Category:")
print(actual_expenses)

# Define monthly budget
budget = {
    "Food": 3000,
    "Travel": 2000,
    "Shopping": 3000,
    "Bills": 2500,
    "Health": 1500,
    "Entertainment": 2000
}

print("\nMonthly Budget:")
print(budget)

# Compare budget with actual expenses
print("\nBudget Analysis:")

for category, budget_amount in budget.items():

    actual_amount = actual_expenses.get(category, 0)

    remaining = budget_amount - actual_amount

    print("\nCategory:", category)
    print("Budget: ₹", budget_amount)
    print("Actual Expense: ₹", actual_amount)

    if remaining >= 0:
        print("Remaining: ₹", remaining)
        print("Status: Within Budget")
    else:
        print("Exceeded By: ₹", abs(remaining))
        print("Status: Over Budget")