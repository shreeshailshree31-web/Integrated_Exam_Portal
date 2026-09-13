from flask import Flask, render_template, request
from pymongo import MongoClient
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

app = Flask(__name__)

# MongoDB connection
MONGO_URI = os.getenv("MONGO_URI")

client = MongoClient(MONGO_URI)

# Database
db = client["exam_portal"]

# Collections
students_collection = db["students"]


# ---------------- CREATE DEMO STUDENT ----------------

def init_db():

    existing_student = students_collection.find_one({
        "usn": "1SD23CS001"
    })

    if not existing_student:

        students_collection.insert_one({
            "usn": "1SD23CS001",
            "name": "Demo Student",
            "password": "student123",
            "branch": "Computer Science & Engineering",
            "semester": 5
        })


# ---------------- HOME ----------------

@app.route("/")
def home():

    return render_template("home.html")


# ---------------- STUDENT LOGIN ----------------

@app.route("/student-login", methods=["GET", "POST"])
def student_login():

    if request.method == "POST":

        usn = request.form["usn"]
        password = request.form["password"]

        student = students_collection.find_one({
            "usn": usn,
            "password": password
        })

        if student:

            return render_template(
                "student_dashboard.html",
                student=student
            )

        else:

            return "Invalid USN or Password"

    return render_template("student_login.html")


# ---------------- STUDENT DASHBOARD ----------------

@app.route("/student-dashboard")
def student_dashboard():

    usn = "1SD23CS001"

    student = students_collection.find_one({
        "usn": usn
    })

    return render_template(
        "student_dashboard.html",
        student=student
    )


# ---------------- EXAM REGISTRATION ----------------

@app.route("/exam-registration", methods=["GET", "POST"])
def exam_registration():

    usn = "1SD23CS001"

    student = students_collection.find_one({
        "usn": usn
    })

    return render_template(
        "exam_registration.html",
        student=student
    )


# ---------------- RUN APPLICATION ----------------

if __name__ == "__main__":

    init_db()

    app.run(debug=True)