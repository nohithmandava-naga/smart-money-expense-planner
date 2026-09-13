import pandas as pd
import joblib
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

# Load dataset
data = pd.read_csv("data/expenses.csv")

# Convert Date to datetime
data["Date"] = pd.to_datetime(data["Date"])

print("Dataset loaded successfully!")
print(data.head())

# Create useful date features
data["Day"] = data["Date"].dt.day
data["Month"] = data["Date"].dt.month
data["DayOfWeek"] = data["Date"].dt.dayofweek

print("\nDataset with new features:")
print(data.head())


# Convert Category into numerical values
data["Category_Code"] = data["Category"].astype("category").cat.codes

print("\nCategory codes:")
print(data[["Category", "Category_Code"]].drop_duplicates())

# Select input features
X = data[["Day", "Month", "DayOfWeek", "Category_Code"]]

# Select target variable
y = data["Amount"]


# Split data into training and testing sets
X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.2,
    random_state=42
)

print("\nTraining data:")
print(X_train)

print("\nTesting data:")
print(X_test)

print("\nTraining data size:", len(X_train))
print("Testing data size:", len(X_test))


# Create Linear Regression model
model = LinearRegression()

# Train the model
model.fit(X_train, y_train)

print("\nModel training completed successfully!")


# Make predictions using testing data
y_pred = model.predict(X_test)

print("\nPredicted Expenses:")
print(y_pred)

print("\nActual Expenses:")
print(y_test.values)

# Calculate evaluation metrics
mae = mean_absolute_error(y_test, y_pred)
mse = mean_squared_error(y_test, y_pred)
r2 = r2_score(y_test, y_pred)

print("\nModel Evaluation:")
print("Mean Absolute Error (MAE):", mae)
print("Mean Squared Error (MSE):", mse)
print("R2 Score:", r2)

# Save the trained model
joblib.dump(model, "models/expense_prediction_model.pkl")

print("\nModel saved successfully!")

print("\nInput Features:")
print(X)

print("\nTarget Amount:")
print(y)
