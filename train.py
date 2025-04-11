import pandas as pd
import os
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder
from sklearn.multioutput import MultiOutputClassifier
from sklearn.metrics import accuracy_score
import joblib

# === 1. Load dataset ===
df = pd.read_excel("Domain_Intelligent_Student_Dataset_100000_noisy.xlsx")

# === 2. Define output and input columns ===
output_columns = [
    'Preferred_Course_Format',
    'Preferred_Course_Difficulty_Level',
    'Preferred_Instructor_Teaching_Style',
    'Available_Certifications'
]
input_columns = df.columns.difference(output_columns + ['Student_ID'])

X = df[input_columns].copy()
y = df[output_columns].copy()

# === 3. Encode categorical columns ===
encoders = {}

# Encode X (input features)
for col in X.select_dtypes(include='object').columns:
    le = LabelEncoder()
    X[col] = le.fit_transform(X[col])
    encoders[f"X__{col}"] = le

# Encode y (output labels)
for col in y.columns:
    le = LabelEncoder()
    y[col] = le.fit_transform(y[col])
    encoders[f"y__{col}"] = le

# === 4. Train/Test Split and Model Training ===
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

model = MultiOutputClassifier(RandomForestClassifier(n_estimators=100, random_state=42))
model.fit(X_train, y_train)

# === 5. Evaluate Model ===
print("\n📊 Accuracy (All Inputs ➡ Predict Last 4 Columns):")
y_pred = model.predict(X_test)
for i, col in enumerate(output_columns):
    acc = accuracy_score(y_test[col], y_pred[:, i])
    print(f"{col}: {acc:.2%}")

# Optional: Print overall accuracy (only if all 4 predictions are correct)
all_correct = (y_pred == y_test.to_numpy()).all(axis=1).sum()
overall_accuracy = all_correct / len(y_test)
print(f"\n🎯 Overall Multi-Target Accuracy: {overall_accuracy:.2%}")

# === 6. Save model and encoders ===
os.makedirs("model", exist_ok=True)
joblib.dump(model, "model/student_course_model.pkl")
joblib.dump(encoders, "model/student_course_encoders.pkl")
joblib.dump(list(X.select_dtypes(include='object').columns), "model/categorical_input_columns.pkl")

print("\n✅ Model, encoders, and column info saved successfully in 'model/' folder.")
