# Total expense
total_expense = data["Amount"].sum()
print("\nTotal Expense:", total_expense)

# Average expense
average_expense = data["Amount"].mean()
print("Average Expense:", average_expense)

# Highest expense
highest_expense = data["Amount"].max()
print("Highest Expense:", highest_expense)

# Category-wise expenses
category_expense = data.groupby("Category")["Amount"].sum()

print("\nCategory-wise Expenses:")
print(category_expense)


import matplotlib.pyplot as plt

# Create category-wise expense chart
category_expense.plot(kind="bar")

plt.title("Category-wise Expenses")
plt.xlabel("Category")
plt.ylabel("Amount (₹)")
plt.xticks(rotation=45)
plt.tight_layout()
plt.show()