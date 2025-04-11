from flask import Flask, render_template, request, session, redirect, send_file, jsonify
import pandas as pd
import joblib
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
import numpy as np
import pickle
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.units import inch
import io
import base64
import os
from datetime import datetime

app = Flask(__name__, template_folder="templates")
app.secret_key = "1234567890."
DATABASE = "course.db"
EXCEL_FILE = "student_inputs.xlsx"

# -------------------------------
# Database Manager & Table Creation
# -------------------------------
class DatabaseManager:
    def __init__(self, db_path: str):
        self.db_path = db_path

    def __enter__(self):
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        return self.conn.cursor()

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            self.conn.commit()
        self.conn.close()

def create_tables():
    with DatabaseManager(DATABASE) as cursor:
        cursor.execute('''CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            address TEXT,
            phone TEXT NOT NULL)''')

# Initialize Excel file if it doesn't exist
def init_excel_file():
    if not os.path.exists(EXCEL_FILE):
        # Define all columns for the Excel file
        columns = [
            'Student_ID', 'Final_Grade', 'Test_Score_Math', 'Test_Score_Science',
            'Test_Score_Literature', 'Test_Score_History', 'Test_Score_Physics',
            'Course_Completion_Rate', 'Time_Spent_on_Learning_Platforms',
            'Preferred_Course_Duration', 'Explored_Course_Topics',
            'Self-Declared_Interests', 'Hobbies_and_Passion', 'Extracurricular_Activities',
            'Online_Courses_Currently_Studying', 'Online_Learning_Platform_Used',
            'Long-Term_Career_Goals', 'Preferred_Course_Format',
            'Preferred_Course_Difficulty_Level', 'Preferred_Instructor_Teaching_Style',
            'Available_Certifications', 'Submission_Date'
        ]
        df = pd.DataFrame(columns=columns)
        df.to_excel(EXCEL_FILE, index=False)
        print(f"Created new Excel file: {EXCEL_FILE}")

# Save student input data to Excel
def save_to_excel(data):
    try:
        # Ensure all subject marks are captured correctly
        subject_keys = [
            'Test_Score_Math', 'Test_Score_Science',
            'Test_Score_Literature', 'Test_Score_History', 'Test_Score_Physics'
        ]
        for key in subject_keys:
            val = data.get(key, None)
            if val is None or val == "":
                print(f"[Warning] Missing or empty field: {key}")
                data[key] = 0.0
            else:
                data[key] = float(val)

        # Convert other numeric fields
        numeric_fields = ['Final_Grade', 'Course_Completion_Rate', 'Time_Spent_on_Learning_Platforms']
        for key in numeric_fields:
            val = data.get(key, None)
            if val is None or val == "":
                data[key] = 0.0
            else:
                data[key] = float(val)

        data['Submission_Date'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Save logic continues...
        ...

        # Read existing Excel file if available; else create new DataFrame
        if os.path.exists(EXCEL_FILE):
            df = pd.read_excel(EXCEL_FILE)
        else:
            df = pd.DataFrame(columns=[
                'Student_ID', 'Final_Grade', 'Test_Score_Math', 'Test_Score_Science',
                'Test_Score_Literature', 'Test_Score_History', 'Test_Score_Physics',
                'Course_Completion_Rate', 'Time_Spent_on_Learning_Platforms',
                'Preferred_Course_Duration', 'Explored_Course_Topics',
                'Self-Declared_Interests', 'Hobbies_and_Passion', 'Extracurricular_Activities',
                'Online_Courses_Currently_Studying', 'Online_Learning_Platform_Used',
                'Long-Term_Career_Goals', 'Preferred_Course_Format',
                'Preferred_Course_Difficulty_Level', 'Preferred_Instructor_Teaching_Style',
                'Available_Certifications', 'Submission_Date'
            ])
        
        # Create DataFrame from new data
        new_row = pd.DataFrame([data])
        
        # Concatenate the new row with the existing data
        df = pd.concat([df, new_row], ignore_index=True)
        
        # Save the updated DataFrame back to Excel
        df.to_excel(EXCEL_FILE, index=False)
        return True
    except Exception as e:
        print(f"Error saving to Excel: {str(e)}")
        return False


# -------------------------------
# User Routes: Login / Register / Logout
# -------------------------------
# Add to the login route to handle admin login
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        # Admin login check
        if email == "admin@gmail.com" and password == "admin123":  # Use a more secure password in production
            session["user_id"] = 0  # Special ID for admin
            session["email"] = email
            session["username"] = "Admin"
            session["is_admin"] = True
            return redirect("/admin_dashboard")

        with DatabaseManager(DATABASE) as cursor:
            cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
            user = cursor.fetchone()
            if user and check_password_hash(user["password"], password):
                session["user_id"] = user["id"]
                session["email"] = user["email"]
                session["username"] = user["username"]
                return redirect("/form")
            else:
                return "Invalid email or password!", 401
    return render_template("login.html")

@app.route("/admin_dashboard")
def admin_dashboard():
    # Check if user is admin
    if not session.get("is_admin", False):
        return redirect("/login")
        
    # Read student data from Excel file
    if os.path.exists(EXCEL_FILE):
        students_df = pd.read_excel(EXCEL_FILE)
        students = students_df.to_dict('records')
    else:
        students = []
        
    return render_template("admin_dashboard.html", students=students)


@app.route("/admin/view_student/<student_id>")
def view_student(student_id):
    # Check if user is admin
    if not session.get("is_admin", False):
        return redirect("/login")
        
    # Read student data from Excel file
    if os.path.exists(EXCEL_FILE):
        students_df = pd.read_excel(EXCEL_FILE)
        student_records = students_df[students_df['Student_ID'] == student_id].to_dict('records')
        if student_records:
            student = student_records[0]
            
            # Prepare scores for radar chart (Pentagon chart)
            scores = []
            for score_field in ['Test_Score_Math', 'Test_Score_Science', 'Test_Score_Literature', 
                                'Test_Score_History', 'Test_Score_Physics']:
                try:
                    scores.append(float(student[score_field]))
                except (ValueError, TypeError, KeyError):
                    scores.append(0.0)
            
            # Get recommendation results
            result = {
                "Preferred_Course_Format": student.get("Preferred_Course_Format", "Not Available"),
                "Preferred_Course_Difficulty_Level": student.get("Preferred_Course_Difficulty_Level", "Not Available"),
                "Preferred_Instructor_Teaching_Style": student.get("Preferred_Instructor_Teaching_Style", "Not Available"),
                "Available_Certifications": student.get("Available_Certifications", "Not Available")
            }
            
            # Prepare student info
            student_info = {
                "Student_ID": student_id,
                "Final_Grade": student.get("Final_Grade", "Not Provided")
            }
            
            # Render the admin view template.
            # IMPORTANT: Use bracket notation in the template for keys with hyphens.
            return render_template("admin_view_student.html", 
                                   student=student, 
                                   scores=scores, 
                                   result=result, 
                                   student_info=student_info,
                                   form_data=student)
    return "Student not found", 404


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        email = request.form["email"]
        password = generate_password_hash(request.form["password"])
        address = request.form["address"]
        phone = request.form["phone"]
        with DatabaseManager(DATABASE) as cursor:
            try:
                cursor.execute("""
                    INSERT INTO users (username, email, password, address, phone) 
                    VALUES (?, ?, ?, ?, ?)""",
                    (username, email, password, address, phone))
                return redirect("/login")
            except sqlite3.IntegrityError:
                return "Email already registered!", 400
    return render_template("register.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

@app.route('/')
def home():
    return render_template("home.html")

# -------------------------------
# Load Model and Encoders
# -------------------------------
model = joblib.load("student_course_model.pkl")
encoders = joblib.load("student_course_encoders.pkl")
cat_columns = joblib.load("categorical_input_columns_fixed.pkl")

input_columns = [
    'Final_Grade', 'Test_Score_Math', 'Test_Score_Science',
    'Test_Score_Literature', 'Test_Score_History', 'Test_Score_Physics',
    'Course_Completion_Rate', 'Time_Spent_on_Learning_Platforms',
    'Preferred_Course_Duration', 'Explored_Course_Topics',
    'Self-Declared_Interests', 'Hobbies_and_Passion', 'Extracurricular_Activities',
    'Online_Courses_Currently_Studying', 'Online_Learning_Platform_Used',
    'Long-Term_Career_Goals'
]
output_labels = [
    'Preferred_Course_Format',
    'Preferred_Course_Difficulty_Level',
    'Preferred_Instructor_Teaching_Style',
    'Available_Certifications'
]

# -------------------------------
# Precomputed Dropdown Options (Unique values) – load from pickle if exists
# -------------------------------
try:
    dropdown_options = joblib.load("dropdown_options.pkl")
except Exception:
    # If not available, compute from dataset once
    df_full = pd.read_excel("Domain_Intelligent_Student_Dataset_100000.xlsx")
    dropdown_options = {
        col: sorted(df_full[col].dropna().unique().tolist())
        for col in input_columns
    }
    joblib.dump(dropdown_options, "dropdown_options.pkl")

# -------------------------------
# Form & Prediction Routes
# -------------------------------
@app.route("/form")
def form():
    # Render form with dropdown_options
    return render_template("form.html", input_columns=input_columns, dropdown_options=dropdown_options)

@app.route("/predict", methods=["POST"])
def predict():
    form_data = {col: request.form.get(col) for col in input_columns}

    # Get scores directly from field names sent in the form
    score_fields = [
        'Test_Score_Math', 'Test_Score_Science',
        'Test_Score_Literature', 'Test_Score_History', 'Test_Score_Physics'
    ]
    metric_fields = ['Course_Completion_Rate', 'Time_Spent_on_Learning_Platforms']
    numeric_fields = ['Final_Grade'] + score_fields + metric_fields

    for field in numeric_fields:
        raw = request.form.get(field)
        form_data[field] = raw if raw else '0'  # Ensure string for safe conversion

    # Create DataFrame
    input_df = pd.DataFrame([form_data])

    # Convert numeric columns
    for col in numeric_fields:
        input_df[col] = pd.to_numeric(input_df[col], errors='coerce').fillna(0.0)

    # Encode categorical features
    for col in cat_columns:
        le = encoders.get(f"X__{col}")
        if le:
            val = form_data.get(col, "")
            if not val:
                val = le.classes_[0] if len(le.classes_) > 0 else ""
            if val not in le.classes_:
                le.classes_ = np.append(le.classes_, val)
            input_df.at[0, col] = le.transform([val])[0]

    # Align column order
    input_df = input_df[model.estimators_[0].feature_names_in_]

    # Prediction
    predictions = model.predict(input_df)[0]

    result = {}
    for i, col in enumerate(output_labels):
        le = encoders.get(f"y__{col}")
        result[col] = le.inverse_transform([predictions[i]])[0]

    # Prepare data for radar chart
    scores = [float(form_data[field]) for field in score_fields]

    student_info = {
        "Student_ID": request.form.get("Student_ID", "Not Provided"),
        "Final_Grade": form_data.get("Final_Grade", "Not Provided")
    }

    # Prepare Excel data (merged form + result)
    excel_data = {**form_data, **result, 'Student_ID': student_info['Student_ID']}

    # Convert necessary fields for Excel
    for field in numeric_fields:
        try:
            excel_data[field] = float(excel_data[field])
        except:
            excel_data[field] = 0.0

    # Save to Excel
    save_to_excel(excel_data)

    return render_template("result.html", result=result, scores=scores, student_info=student_info, form_data=form_data)

# -------------------------------
# Download PDF Route: Generates a PDF with student details, prediction, and chart image.
# (For chart images, we expect base64 strings from the client in hidden fields)
# -------------------------------


import io
from reportlab.lib import colors

@app.route("/download", methods=["POST"])
def download():
    highlight_color = colors.HexColor("#dc3545")

    student_id = request.form.get("Student_ID", "Not Provided")
    final_grade = request.form.get("Final_Grade", "Not Provided")

    test_scores = {
        "Mathematics": request.form.get("Test_Score_Math", "N/A"),
        "Science": request.form.get("Test_Score_Science", "N/A"),
        "Literature": request.form.get("Test_Score_Literature", "N/A"),
        "History": request.form.get("Test_Score_History", "N/A"),
        "Physics": request.form.get("Test_Score_Physics", "N/A")
    }

    additional_info = [
        ["Information", "Value"],
        ["Course Completion Rate", request.form.get("Course_Completion_Rate", "None")],
        ["Learning Platform Time", request.form.get("Time_Spent_on_Learning_Platforms", "None")],
        ["Preferred Course Duration", request.form.get("Preferred_Course_Duration", "None")],
        ["Explored Topics", request.form.get("Explored_Course_Topics", "None")],
        ["Interests", request.form.get("Self-Declared_Interests", "None")],
        ["Hobbies", request.form.get("Hobbies_and_Passion", "None")],
        ["Extracurricular Activities", request.form.get("Extracurricular_Activities", "None")],
        ["Online Courses", request.form.get("Online_Courses_Currently_Studying", "None")],
        ["Learning Platform Used", request.form.get("Online_Learning_Platform_Used", "None")],
        ["Career Goals", request.form.get("Long-Term_Career_Goals", "None")]
    ]

    recommendations = [
        ["Recommendation Category", "Predicted Preference"],
        ["Course Format", request.form.get("Preferred_Course_Format", "Not Available")],
        ["Difficulty Level", request.form.get("Preferred_Course_Difficulty_Level", "Not Available")],
        ["Instructor Teaching Style", request.form.get("Preferred_Instructor_Teaching_Style", "Not Available")],
        ["Available Certifications", request.form.get("Available_Certifications", "Not Available")]
    ]

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.5*inch, bottomMargin=0.5*inch)
    styles = getSampleStyleSheet()
    elements = []

    rose_color = colors.HexColor("#ffcccc")

    elements.append(Paragraph("Course Recommendation Report", styles['Title']))
    elements.append(Spacer(1, 0.3 * inch))

    # Student Info Table
    elements.append(Paragraph("Student Information", styles['Heading2']))
    student_table = Table([
        ["Student ID", student_id],
        ["Final Grade", final_grade]
    ], colWidths=[3 * inch, 3 * inch])
    student_table.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.5, highlight_color),
        ('BACKGROUND', (0, 0), (1, 0), highlight_color),

        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('PADDING', (0, 0), (-1, -1), 6)
    ]))
    elements.append(student_table)
    elements.append(Spacer(1, 0.2 * inch))

    # Test Scores Table
    elements.append(Paragraph("Test Scores", styles['Heading2']))
    score_table = Table([["Subject", "Score"]] + [[k, v] for k, v in test_scores.items()], colWidths=[3 * inch, 3 * inch])
    score_table.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.5, rose_color),
        ('BACKGROUND', (0, 0), (1, 0), rose_color),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('PADDING', (0, 0), (-1, -1), 6)
    ]))
    elements.append(score_table)
    elements.append(Spacer(1, 0.2 * inch))

    # Additional Info Table
    elements.append(Paragraph("Additional Student Information", styles['Heading2']))
    add_info_table = Table(additional_info, colWidths=[3 * inch, 3 * inch])
    add_info_table.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.5, rose_color),
        ('BACKGROUND', (0, 0), (1, 0), rose_color),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('PADDING', (0, 0), (-1, -1), 6)
    ]))
    elements.append(add_info_table)
    elements.append(Spacer(1, 0.2 * inch))

    # Recommendations Table
    elements.append(Paragraph("Course Recommendations", styles['Heading2']))
    rec_table = Table(recommendations, colWidths=[3 * inch, 3 * inch])
    rec_table.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.5, rose_color),
        ('BACKGROUND', (0, 0), (1, 0), rose_color),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('PADDING', (0, 0), (-1, -1), 6)
    ]))
    elements.append(rec_table)

    # Summary
    elements.append(Spacer(1, 0.3 * inch))
    elements.append(Paragraph("Recommendation Summary", styles['Heading2']))

    summary = f"""Based on the student's academic performance and preferences, the optimal learning environment would be
{request.form.get("Preferred_Course_Format", "Self-paced")} courses at a {request.form.get("Preferred_Course_Difficulty_Level", "Intermediate")} difficulty level with {request.form.get("Preferred_Instructor_Teaching_Style", "Hands-on")} instructors. The student should pursue
courses that offer {request.form.get("Available_Certifications", "Advanced AI")} certifications to align with their career goals."""

    elements.append(Paragraph(summary, styles['BodyText']))

    doc.build(elements)
    buffer.seek(0)

    return send_file(buffer, download_name="Course_Recommendation_Report.pdf", as_attachment=True, mimetype='application/pdf')


if __name__ == '__main__':
    create_tables()
    init_excel_file()  # Initialize Excel file if doesn't exist
    app.run(debug=True)