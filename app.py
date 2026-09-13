from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from pymongo import MongoClient
from bson.objectid import ObjectId
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os


# ============================================================
# LOAD ENVIRONMENT VARIABLES
# ============================================================

load_dotenv()


# ============================================================
# FLASK APPLICATION
# ============================================================

app = Flask(__name__)

app.secret_key = os.getenv(
    "SECRET_KEY",
    "integrated_exam_portal_secret_2026"
)

app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax"
)


# ============================================================
# MONGODB CONNECTION
# ============================================================

MONGO_URI = os.getenv("MONGO_URI")

if not MONGO_URI:
    raise RuntimeError(
        "MONGO_URI is not configured. Please check your .env file."
    )

client = MongoClient(MONGO_URI)

db = client["integrated_exam_portal"]

students_collection = db["students"]
admins_collection = db["admins"]
subjects_collection = db["subjects"]
registrations_collection = db["exam_registrations"]
examinations_collection = db["examinations"]
timetable_collection = db["timetable"]
hall_tickets_collection = db["hall_tickets"]


# ============================================================
# DATABASE INITIALIZATION
# ============================================================

def init_db():

    # --------------------------------------------------------
    # DEMO STUDENT
    # --------------------------------------------------------

    existing_student = students_collection.find_one(
        {"usn": "1SD23CS001"}
    )

    if not existing_student:

        students_collection.insert_one({
            "usn": "1SD23CS001",
            "name": "Demo Student",
            "password": "student123",
            "branch": "Computer Science & Engineering",
            "semester": 5
        })


    # --------------------------------------------------------
    # DEMO ADMIN
    # --------------------------------------------------------

    existing_admin = admins_collection.find_one(
        {"username": "admin"}
    )

    if not existing_admin:

        admins_collection.insert_one({
            "username": "admin",
            "password": "admin123",
            "name": "Portal Administrator"
        })


# ============================================================
# HOME
# ============================================================

@app.route("/")
def home():

    return render_template(
        "home.html"
    )


# ============================================================
# STUDENT LOGIN
# ============================================================

@app.route(
    "/student-login",
    methods=["GET", "POST"]
)
def student_login():

    if request.method == "POST":

        usn = request.form.get(
            "usn",
            ""
        ).strip().upper()

        password = request.form.get(
            "password",
            ""
        )

        student = students_collection.find_one({
            "usn": usn
        })

        if not student:

            return render_template(
                "student_login.html",
                error="Invalid USN or password."
            )


        stored_password = student.get(
            "password",
            ""
        )

        password_valid = False


        # ----------------------------------------------------
        # HASHED PASSWORD
        # ----------------------------------------------------

        try:

            password_valid = check_password_hash(
                stored_password,
                password
            )

        except Exception:

            password_valid = False


        # ----------------------------------------------------
        # BACKWARD COMPATIBILITY
        # ----------------------------------------------------

        if not password_valid and stored_password == password:

            password_valid = True

            students_collection.update_one(
                {
                    "_id": student["_id"]
                },
                {
                    "$set": {
                        "password":
                            generate_password_hash(password)
                    }
                }
            )


        if not password_valid:

            return render_template(
                "student_login.html",
                error="Invalid USN or password."
            )


        # ----------------------------------------------------
        # STUDENT SESSION
        # ----------------------------------------------------

        session.clear()

        session["student_id"] = str(
            student["_id"]
        )

        session["student_usn"] = student["usn"]

        session["student_name"] = student["name"]


        return redirect(
            url_for("student_dashboard")
        )


    return render_template(
        "student_login.html"
    )


# ============================================================
# STUDENT DASHBOARD
# ============================================================

@app.route("/student-dashboard")
def student_dashboard():

    if "student_id" not in session:

        return redirect(
            url_for("student_login")
        )


    try:

        student = students_collection.find_one(
            {
                "_id": ObjectId(
                    session["student_id"]
                )
            }
        )

    except Exception:

        student = None


    if not student:

        session.clear()

        return redirect(
            url_for("student_login")
        )


    registration = registrations_collection.find_one(
        {
            "usn": student["usn"]
        },
        sort=[
            ("_id", -1)
        ]
    )


    return render_template(
        "student_dashboard.html",
        student=student,
        registration=registration
    )


# ============================================================
# ADMIN LOGIN
# ============================================================

@app.route(
    "/admin-login",
    methods=["GET", "POST"]
)
def admin_login():

    if request.method == "POST":

        username = request.form.get(
            "username",
            ""
        ).strip()

        password = request.form.get(
            "password",
            ""
        )


        admin = admins_collection.find_one({
            "username": username
        })


        if not admin:

            return render_template(
                "admin/login.html",
                error="Invalid username or password."
            )


        stored_password = admin.get(
            "password",
            ""
        )

        password_valid = False


        # ----------------------------------------------------
        # HASHED PASSWORD
        # ----------------------------------------------------

        try:

            password_valid = check_password_hash(
                stored_password,
                password
            )

        except Exception:

            password_valid = False


        # ----------------------------------------------------
        # BACKWARD COMPATIBILITY
        # ----------------------------------------------------

        if not password_valid and stored_password == password:

            password_valid = True

            admins_collection.update_one(
                {
                    "_id": admin["_id"]
                },
                {
                    "$set": {
                        "password":
                            generate_password_hash(password)
                    }
                }
            )


        if not password_valid:

            return render_template(
                "admin/login.html",
                error="Invalid username or password."
            )


        # ----------------------------------------------------
        # ADMIN SESSION
        # ----------------------------------------------------

        session.clear()

        session["admin_id"] = str(
            admin["_id"]
        )

        session["admin_username"] = admin["username"]

        session["admin_name"] = admin.get(
            "name",
            "Administrator"
        )


        return redirect(
            url_for("admin_dashboard")
        )


    return render_template(
        "admin/login.html"
    )


# ============================================================
# ADMIN DASHBOARD
# ============================================================

@app.route("/admin-dashboard")
def admin_dashboard():

    if "admin_id" not in session:

        return redirect(
            url_for("admin_login")
        )


    total_students = students_collection.count_documents({})

    total_registrations = registrations_collection.count_documents({})


    # --------------------------------------------------------
    # TOTAL SUBJECTS REGISTERED
    # --------------------------------------------------------

    total_subjects_registered = 0

    registrations_for_count = registrations_collection.find({})


    for registration in registrations_for_count:

        selected_subjects = registration.get(
            "selected_subjects"
        )

        old_subjects = registration.get(
            "subjects"
        )


        if selected_subjects:

            total_subjects_registered += len(
                selected_subjects
            )

        elif old_subjects:

            total_subjects_registered += len(
                old_subjects
            )


    # --------------------------------------------------------
    # TOTAL EXAMINATIONS
    # --------------------------------------------------------

    total_examinations = examinations_collection.count_documents({})


    # --------------------------------------------------------
    # UPCOMING EXAMINATIONS
    # --------------------------------------------------------

    upcoming_examinations = []

    all_examinations = examinations_collection.find({}).sort(
        "_id",
        -1
    )


    today = datetime.now().date()


    for examination in all_examinations:

        exam_date_value = examination.get(
            "exam_date"
        )

        is_upcoming = False


        if exam_date_value:

            try:

                exam_date = datetime.strptime(
                    exam_date_value,
                    "%d-%m-%Y"
                ).date()

                if exam_date >= today:

                    is_upcoming = True

            except ValueError:

                try:

                    exam_date = datetime.strptime(
                        exam_date_value,
                        "%Y-%m-%d"
                    ).date()

                    if exam_date >= today:

                        is_upcoming = True

                except ValueError:

                    pass


        if is_upcoming:

            upcoming_examinations.append(
                examination
            )


    # --------------------------------------------------------
    # HALL TICKET STATISTICS
    # --------------------------------------------------------

    total_hall_tickets = hall_tickets_collection.count_documents({})


    published_hall_tickets = hall_tickets_collection.count_documents(
        {
            "published": True
        }
    )


    # --------------------------------------------------------
    # RECENT REGISTRATIONS
    # --------------------------------------------------------

    registrations = list(
        registrations_collection.find({})
        .sort("_id", -1)
        .limit(20)
    )


    admin_name = session.get(
        "admin_name",
        "Administrator"
    )


    return render_template(
        "admin/dashboard.html",

        admin_name=admin_name,

        total_students=total_students,

        total_registrations=total_registrations,

        total_subjects_registered=total_subjects_registered,

        total_examinations=total_examinations,

        upcoming_examinations=upcoming_examinations,

        published_hall_tickets=published_hall_tickets,

        total_hall_tickets=total_hall_tickets,

        registrations=registrations
    )


# ============================================================
# ADMIN - SUBJECT MANAGEMENT
# ============================================================

@app.route(
    "/admin-subjects",
    methods=["GET", "POST"]
)
def admin_subjects():

    if "admin_id" not in session:

        return redirect(
            url_for("admin_login")
        )


    if request.method == "POST":

        subject_code = request.form.get(
            "subject_code",
            ""
        ).strip().upper()

        subject_name = request.form.get(
            "subject_name",
            ""
        ).strip()

        semester = request.form.get(
            "semester",
            ""
        ).strip()


        if not subject_code or not subject_name or not semester:

            return render_template(
                "admin/subjects.html",
                error="Please fill all fields."
            )


        try:

            semester = int(semester)

        except ValueError:

            return render_template(
                "admin/subjects.html",
                error="Invalid semester."
            )


        duplicate = subjects_collection.find_one({
            "subject_code": subject_code,
            "semester": semester
        })


        if duplicate:

            return render_template(
                "admin/subjects.html",
                error="Subject code already exists for this semester."
            )


        subjects_collection.insert_one({

            "subject_code": subject_code,

            "subject_name": subject_name,

            "semester": semester

        })


        return redirect(
            url_for("admin_subjects")
        )


    subjects = list(
        subjects_collection.find({})
        .sort([
            ("semester", 1),
            ("subject_code", 1)
        ])
    )


    return render_template(
        "admin/subjects.html",
        subjects=subjects
    )


# ============================================================
# ADMIN - EDIT SUBJECT
# ============================================================

@app.route(
    "/admin-subjects/edit/<subject_id>",
    methods=["GET", "POST"]
)
def edit_subject(subject_id):

    if "admin_id" not in session:

        return redirect(
            url_for("admin_login")
        )


    try:

        subject = subjects_collection.find_one(
            {
                "_id": ObjectId(subject_id)
            }
        )

    except Exception:

        return redirect(
            url_for("admin_subjects")
        )


    if not subject:

        return redirect(
            url_for("admin_subjects")
        )


    if request.method == "POST":

        subject_code = request.form.get(
            "subject_code",
            ""
        ).strip().upper()

        subject_name = request.form.get(
            "subject_name",
            ""
        ).strip()

        semester = request.form.get(
            "semester",
            ""
        ).strip()


        if not subject_code or not subject_name or not semester:

            return render_template(
                "admin/edit_subject.html",
                subject=subject,
                error="Please fill all fields."
            )


        try:

            semester = int(semester)

        except ValueError:

            return render_template(
                "admin/edit_subject.html",
                subject=subject,
                error="Invalid semester."
            )


        duplicate = subjects_collection.find_one({
            "subject_code": subject_code,
            "semester": semester,
            "_id": {
                "$ne": subject["_id"]
            }
        })


        if duplicate:

            return render_template(
                "admin/edit_subject.html",
                subject=subject,
                error="Another subject with this code already exists."
            )


        subjects_collection.update_one(
            {
                "_id": subject["_id"]
            },
            {
                "$set": {
                    "subject_code": subject_code,
                    "subject_name": subject_name,
                    "semester": semester
                }
            }
        )


        return redirect(
            url_for("admin_subjects")
        )


    return render_template(
        "admin/edit_subject.html",
        subject=subject
    )


# ============================================================
# ADMIN - DELETE SUBJECT
# ============================================================

@app.route(
    "/admin-subjects/delete/<subject_id>"
)
def delete_subject(subject_id):

    if "admin_id" not in session:

        return redirect(
            url_for("admin_login")
        )


    try:

        subjects_collection.delete_one(
            {
                "_id": ObjectId(subject_id)
            }
        )

    except Exception:

        pass


    return redirect(
        url_for("admin_subjects")
    )


# ============================================================
# ADMIN - STUDENT MANAGEMENT
# ============================================================

@app.route(
    "/admin-students",
    methods=["GET", "POST"]
)
def admin_students():

    if "admin_id" not in session:

        return redirect(
            url_for("admin_login")
        )


    if request.method == "POST":

        usn = request.form.get(
            "usn",
            ""
        ).strip().upper()

        name = request.form.get(
            "name",
            ""
        ).strip()

        password = request.form.get(
            "password",
            ""
        )

        branch = request.form.get(
            "branch",
            ""
        ).strip()

        semester = request.form.get(
            "semester",
            ""
        ).strip()


        if not all([
            usn,
            name,
            password,
            branch,
            semester
        ]):

            return render_template(
                "admin/students.html",
                error="Please fill all fields."
            )


        try:

            semester = int(semester)

        except ValueError:

            return render_template(
                "admin/students.html",
                error="Invalid semester."
            )


        existing_student = students_collection.find_one({
            "usn": usn
        })


        if existing_student:

            return render_template(
                "admin/students.html",
                error="Student with this USN already exists."
            )


        students_collection.insert_one({

            "usn": usn,

            "name": name,

            "password": generate_password_hash(
                password
            ),

            "branch": branch,

            "semester": semester

        })


        return redirect(
            url_for("admin_students")
        )


    students = list(
        students_collection.find({})
        .sort("usn", 1)
    )


    return render_template(
        "admin/students.html",
        students=students
    )


# ============================================================
# ADMIN - DELETE STUDENT
# ============================================================

@app.route(
    "/admin-students/delete/<student_id>"
)
def delete_student(student_id):

    if "admin_id" not in session:

        return redirect(
            url_for("admin_login")
        )


    try:

        students_collection.delete_one(
            {
                "_id": ObjectId(student_id)
            }
        )

    except Exception:

        pass


    return redirect(
        url_for("admin_students")
    )


# ============================================================
# ADMIN - EDIT STUDENT
# ============================================================

@app.route(
    "/admin-students/edit/<student_id>",
    methods=["GET", "POST"]
)
def edit_student(student_id):

    if "admin_id" not in session:

        return redirect(
            url_for("admin_login")
        )


    try:

        student = students_collection.find_one(
            {
                "_id": ObjectId(student_id)
            }
        )

    except Exception:

        return redirect(
            url_for("admin_students")
        )


    if not student:

        return redirect(
            url_for("admin_students")
        )


    if request.method == "POST":

        usn = request.form.get(
            "usn",
            ""
        ).strip().upper()

        name = request.form.get(
            "name",
            ""
        ).strip()

        password = request.form.get(
            "password",
            ""
        )

        branch = request.form.get(
            "branch",
            ""
        ).strip()

        semester = request.form.get(
            "semester",
            ""
        ).strip()


        if not usn or not name or not branch or not semester:

            return render_template(
                "admin/students.html",
                error="Please fill all required fields.",
                students=list(
                    students_collection.find({})
                    .sort("usn", 1)
                ),
                edit_student=student
            )


        try:

            semester = int(semester)

        except ValueError:

            return render_template(
                "admin/students.html",
                error="Invalid semester.",
                students=list(
                    students_collection.find({})
                    .sort("usn", 1)
                ),
                edit_student=student
            )


        duplicate = students_collection.find_one({
            "usn": usn,
            "_id": {
                "$ne": student["_id"]
            }
        })


        if duplicate:

            return render_template(
                "admin/students.html",
                error="Another student already uses this USN.",
                students=list(
                    students_collection.find({})
                    .sort("usn", 1)
                ),
                edit_student=student
            )


        update_data = {

            "usn": usn,

            "name": name,

            "branch": branch,

            "semester": semester

        }


        if password:

            update_data["password"] = generate_password_hash(
                password
            )


        students_collection.update_one(

            {
                "_id": student["_id"]
            },

            {
                "$set": update_data
            }

        )


        return redirect(
            url_for("admin_students")
        )


    students = list(
        students_collection.find({})
        .sort("usn", 1)
    )


    return render_template(
        "admin/students.html",
        students=students,
        edit_student=student
    )


# ============================================================
# LOGOUT
# ============================================================

@app.route("/logout")
def logout():

    session.clear()

    return redirect(
        url_for("home")
    )


# ============================================================
# STUDENT EXAM REGISTRATION
# ============================================================

@app.route(
    "/exam-registration",
    methods=["GET", "POST"]
)
def exam_registration():

    # --------------------------------------------------------
    # LOGIN CHECK
    # --------------------------------------------------------

    if "student_id" not in session:

        return redirect(
            url_for("student_login")
        )


    # --------------------------------------------------------
    # GET STUDENT
    # --------------------------------------------------------

    try:

        student = students_collection.find_one(
            {
                "_id": ObjectId(
                    session["student_id"]
                )
            }
        )

    except Exception:

        student = None


    if not student:

        session.clear()

        return redirect(
            url_for("student_login")
        )


    # --------------------------------------------------------
    # GET STUDENT SEMESTER
    # --------------------------------------------------------

    semester = student.get(
        "semester"
    )


    try:

        semester = int(semester)

    except (TypeError, ValueError):

        semester = 0


    # --------------------------------------------------------
    # LOAD SUBJECTS
    # --------------------------------------------------------

    subjects = list(
        subjects_collection.find({
            "semester": semester
        }).sort(
            "subject_code",
            1
        )
    )


    # ========================================================
    # POST - SUBMIT REGISTRATION
    # ========================================================

    if request.method == "POST":

        # ----------------------------------------------------
        # ACCEPT MULTIPLE POSSIBLE CHECKBOX NAMES
        # ----------------------------------------------------

        selected_subject_ids = request.form.getlist(
            "subjects"
        )


        if not selected_subject_ids:

            selected_subject_ids = request.form.getlist(
                "selected_subject_ids"
            )


        if not selected_subject_ids:

            selected_subject_ids = request.form.getlist(
                "selected_subjects"
            )


        # ----------------------------------------------------
        # REMOVE DUPLICATES / EMPTY VALUES
        # ----------------------------------------------------

        selected_subject_ids = list(dict.fromkeys([
            subject_id.strip()
            for subject_id in selected_subject_ids
            if subject_id and subject_id.strip()
        ]))


        # ----------------------------------------------------
        # BUILD SELECTED SUBJECT DATA
        # ----------------------------------------------------

        selected_subjects = []


        for subject_id in selected_subject_ids:

            try:

                subject_object_id = ObjectId(
                    subject_id
                )

            except Exception:

                continue


            subject = subjects_collection.find_one(
                {
                    "_id": subject_object_id,

                    "semester": semester
                }
            )


            if subject:

                selected_subjects.append({

                    "subject_id": str(
                        subject["_id"]
                    ),

                    "subject_code": subject.get(
                        "subject_code",
                        ""
                    ),

                    "subject_name": subject.get(
                        "subject_name",
                        ""
                    )

                })


        # ----------------------------------------------------
        # NO VALID SUBJECT
        # ----------------------------------------------------

        if not selected_subjects:

            return render_template(
                "exam_registration.html",

                student=student,

                subjects=subjects,

                error="Please select at least one subject."
            )


        # ----------------------------------------------------
        # SAVE REGISTRATION
        # ----------------------------------------------------

        registration_data = {

            "usn": student["usn"],

            "student_name": student["name"],

            "branch": student.get(
                "branch",
                ""
            ),

            "semester": semester,

            "selected_subjects": selected_subjects,

            # Old format retained for compatibility
            "subjects": [
                subject["subject_name"]
                for subject in selected_subjects
            ],

            "registered_at": datetime.now().strftime(
                "%d-%m-%Y %H:%M:%S"
            )

        }


        registrations_collection.insert_one(
            registration_data
        )


        # ----------------------------------------------------
        # REGISTRATION SUCCESS PAGE
        # ----------------------------------------------------

        return render_template(
            "registration_success.html",

            student=student,

            selected_subjects=selected_subjects,

            selected_count=len(
                selected_subjects
            )
        )


    # ========================================================
    # GET - SHOW REGISTRATION PAGE
    # ========================================================

    return render_template(
        "exam_registration.html",

        student=student,

        subjects=subjects
    )


# ============================================================
# ADMIN - EXAMINATION MANAGEMENT
# ============================================================

@app.route(
    "/admin/examinations",
    methods=["GET", "POST"]
)
def admin_examinations():

    if "admin_id" not in session:

        return redirect(
            url_for("admin_login")
        )


    if request.method == "POST":

        exam_name = request.form.get(
            "exam_name",
            ""
        ).strip()

        exam_type = request.form.get(
            "exam_type",
            ""
        ).strip()

        semester = request.form.get(
            "semester",
            ""
        ).strip()

        exam_date = request.form.get(
            "exam_date",
            ""
        ).strip()

        last_date = request.form.get(
            "last_date",
            ""
        ).strip()


        if not all([
            exam_name,
            exam_type,
            semester,
            exam_date,
            last_date
        ]):

            return render_template(
                "admin/examinations.html",
                error="Please fill all fields."
            )


        try:

            semester = int(semester)

        except ValueError:

            return render_template(
                "admin/examinations.html",
                error="Invalid semester."
            )


        examinations_collection.insert_one({

            "exam_name": exam_name,

            "exam_type": exam_type,

            "semester": semester,

            "exam_date": exam_date,

            "last_date": last_date,

            "created_at": datetime.now().strftime(
                "%d-%m-%Y %H:%M:%S"
            )

        })


        return redirect(
            url_for("admin_examinations")
        )


    examinations = list(
        examinations_collection.find({})
        .sort("_id", -1)
    )


    return render_template(
        "admin/examinations.html",
        examinations=examinations
    )


# ============================================================
# ADMIN - DELETE EXAMINATION
# ============================================================

@app.route(
    "/admin/examinations/delete/<exam_id>"
)
def delete_examination(exam_id):

    if "admin_id" not in session:

        return redirect(
            url_for("admin_login")
        )


    try:

        examinations_collection.delete_one(
            {
                "_id": ObjectId(exam_id)
            }
        )

    except Exception:

        pass


    return redirect(
        url_for("admin_examinations")
    )


# ============================================================
# ADMIN - TIMETABLE MANAGEMENT
# ============================================================

@app.route(
    "/admin/timetable",
    methods=["GET", "POST"]
)
def admin_timetable():

    if "admin_id" not in session:

        return redirect(
            url_for("admin_login")
        )


    if request.method == "POST":

        exam_id = request.form.get(
            "exam_id",
            ""
        ).strip()

        semester = request.form.get(
            "semester",
            ""
        ).strip()

        subject_id = request.form.get(
            "subject_id",
            ""
        ).strip()

        exam_date = request.form.get(
            "exam_date",
            ""
        ).strip()

        start_time = request.form.get(
            "start_time",
            ""
        ).strip()

        end_time = request.form.get(
            "end_time",
            ""
        ).strip()

        venue = request.form.get(
            "venue",
            ""
        ).strip()


        if not all([
            exam_id,
            semester,
            subject_id,
            exam_date,
            start_time,
            end_time,
            venue
        ]):

            return render_template(
                "admin/timetable.html",

                error="Please fill all timetable fields.",

                examinations=list(
                    examinations_collection.find({})
                    .sort("_id", -1)
                ),

                subjects=list(
                    subjects_collection.find({})
                    .sort("subject_code", 1)
                ),

                timetable=list(
                    timetable_collection.find({})
                    .sort("_id", -1)
                )
            )


        try:

            semester = int(semester)

        except ValueError:

            return render_template(
                "admin/timetable.html",

                error="Invalid semester.",

                examinations=list(
                    examinations_collection.find({})
                ),

                subjects=list(
                    subjects_collection.find({})
                ),

                timetable=list(
                    timetable_collection.find({})
                )
            )


        # ----------------------------------------------------
        # EXAMINATION VALIDATION
        # ----------------------------------------------------

        try:

            examination = examinations_collection.find_one(
                {
                    "_id": ObjectId(exam_id)
                }
            )

        except Exception:

            examination = None


        if not examination:

            return render_template(
                "admin/timetable.html",

                error="Selected examination was not found.",

                examinations=list(
                    examinations_collection.find({})
                ),

                subjects=list(
                    subjects_collection.find({})
                ),

                timetable=list(
                    timetable_collection.find({})
                )
            )


        try:

            examination_semester = int(
                examination.get(
                    "semester",
                    0
                )
            )

        except (TypeError, ValueError):

            examination_semester = 0


        if examination_semester != semester:

            return render_template(
                "admin/timetable.html",

                error="Selected semester does not match the examination.",

                examinations=list(
                    examinations_collection.find({})
                ),

                subjects=list(
                    subjects_collection.find({})
                ),

                timetable=list(
                    timetable_collection.find({})
                )
            )


        # ----------------------------------------------------
        # SUBJECT VALIDATION
        # ----------------------------------------------------

        try:

            subject = subjects_collection.find_one(
                {
                    "_id": ObjectId(subject_id),

                    "semester": semester
                }
            )

        except Exception:

            subject = None


        if not subject:

            return render_template(
                "admin/timetable.html",

                error="Selected subject is invalid for this semester.",

                examinations=list(
                    examinations_collection.find({})
                ),

                subjects=list(
                    subjects_collection.find({})
                ),

                timetable=list(
                    timetable_collection.find({})
                )
            )


        # ----------------------------------------------------
        # DUPLICATE CHECK
        # ----------------------------------------------------

        duplicate = timetable_collection.find_one({

            "exam_id": str(
                examination["_id"]
            ),

            "subject_id": str(
                subject["_id"]
            )

        })


        if duplicate:

            return render_template(
                "admin/timetable.html",

                error="This subject already has a timetable entry for the selected examination.",

                examinations=list(
                    examinations_collection.find({})
                ),

                subjects=list(
                    subjects_collection.find({})
                ),

                timetable=list(
                    timetable_collection.find({})
                )
            )


        # ----------------------------------------------------
        # SAVE TIMETABLE
        # ----------------------------------------------------

        timetable_collection.insert_one({

            "exam_id": str(
                examination["_id"]
            ),

            "exam_name": examination.get(
                "exam_name",
                ""
            ),

            "exam_type": examination.get(
                "exam_type",
                ""
            ),

            "semester": semester,

            "subject_id": str(
                subject["_id"]
            ),

            "subject_code": subject.get(
                "subject_code",
                ""
            ),

            "subject_name": subject.get(
                "subject_name",
                ""
            ),

            "exam_date": exam_date,

            "start_time": start_time,

            "end_time": end_time,

            "venue": venue

        })


        return redirect(
            url_for("admin_timetable")
        )


    examinations = list(
        examinations_collection.find({})
        .sort("_id", -1)
    )


    subjects = list(
        subjects_collection.find({})
        .sort([
            ("semester", 1),
            ("subject_code", 1)
        ])
    )


    timetable = list(
        timetable_collection.find({})
        .sort("_id", -1)
    )


    return render_template(
        "admin/timetable.html",

        examinations=examinations,

        subjects=subjects,

        timetable=timetable
    )


# ============================================================
# ADMIN - DELETE TIMETABLE
# ============================================================

@app.route(
    "/admin/timetable/delete/<timetable_id>"
)
def delete_timetable(timetable_id):

    if "admin_id" not in session:

        return redirect(
            url_for("admin_login")
        )


    try:

        timetable_collection.delete_one(
            {
                "_id": ObjectId(timetable_id)
            }
        )

    except Exception:

        pass


    return redirect(
        url_for("admin_timetable")
    )


# ============================================================
# STUDENT TIMETABLE
# ============================================================

@app.route("/student-timetable")
def student_timetable():

    if "student_id" not in session:

        return redirect(
            url_for("student_login")
        )


    try:

        student = students_collection.find_one(
            {
                "_id": ObjectId(
                    session["student_id"]
                )
            }
        )

    except Exception:

        student = None


    if not student:

        session.clear()

        return redirect(
            url_for("student_login")
        )


    semester = student.get(
        "semester"
    )


    try:

        semester = int(semester)

    except (TypeError, ValueError):

        semester = 0


    timetable = list(
        timetable_collection.find({
            "semester": semester
        }).sort(
            [
                ("exam_date", 1),
                ("start_time", 1)
            ]
        )
    )


    return render_template(
        "student/timetable.html",

        timetable=timetable,

        student=student
    )


# ============================================================
# ADMIN - HALL TICKET MANAGEMENT
# ============================================================

@app.route(
    "/admin/hall-tickets",
    methods=["GET", "POST"]
)
def admin_hall_tickets():

    if "admin_id" not in session:

        return redirect(
            url_for("admin_login")
        )


    # ========================================================
    # LOAD DATA FOR DROPDOWNS
    #
    # IMPORTANT FIX:
    # The old code only sent hall_tickets to the template.
    # Now students and examinations are also sent.
    # ========================================================

    students = list(
        students_collection.find({})
        .sort("usn", 1)
    )


    examinations = list(
        examinations_collection.find({})
        .sort("_id", -1)
    )


    if request.method == "POST":

        usn = request.form.get(
            "usn",
            ""
        ).strip().upper()


        # ----------------------------------------------------
        # GET SELECTED EXAMINATION
        # ----------------------------------------------------

        exam_id = request.form.get(
            "exam_id",
            ""
        ).strip()


        student = students_collection.find_one({
            "usn": usn
        })


        if not student:

            return render_template(
                "admin/hall_tickets.html",

                students=students,

                examinations=examinations,

                hall_tickets=list(
                    hall_tickets_collection.find({})
                    .sort("_id", -1)
                ),

                error="Student not found."
            )


        # ----------------------------------------------------
        # GET STUDENT REGISTRATION
        # ----------------------------------------------------

        registration = registrations_collection.find_one(
            {
                "usn": usn
            },
            sort=[
                ("_id", -1)
            ]
        )


        if not registration:

            return render_template(
                "admin/hall_tickets.html",

                students=students,

                examinations=examinations,

                hall_tickets=list(
                    hall_tickets_collection.find({})
                    .sort("_id", -1)
                ),

                error="No examination registration found for this student."
            )


        # ----------------------------------------------------
        # GET SEMESTER
        # ----------------------------------------------------

        semester = registration.get(
            "semester",
            student.get("semester")
        )


        try:

            semester = int(semester)

        except (TypeError, ValueError):

            try:

                semester = int(
                    student.get(
                        "semester",
                        0
                    )
                )

            except (TypeError, ValueError):

                semester = 0


        # ----------------------------------------------------
        # GET SELECTED SUBJECTS
        # ----------------------------------------------------

        selected_subjects = registration.get(
            "selected_subjects",
            []
        )


        # ----------------------------------------------------
        # OLD FORMAT SUPPORT
        # ----------------------------------------------------

        if not selected_subjects:

            old_subject_names = registration.get(
                "subjects",
                []
            )


            for subject_name in old_subject_names:

                subject = subjects_collection.find_one({

                    "subject_name": subject_name,

                    "semester": semester

                })


                if subject:

                    selected_subjects.append({

                        "subject_id": str(
                            subject["_id"]
                        ),

                        "subject_code": subject.get(
                            "subject_code",
                            ""
                        ),

                        "subject_name": subject.get(
                            "subject_name",
                            ""
                        )

                    })


        # ----------------------------------------------------
        # FIND EXAMINATION
        #
        # If exam_id was submitted, use that examination.
        # Otherwise use latest examination for student's semester.
        # ----------------------------------------------------

        examination = None


        if exam_id:

            try:

                examination = examinations_collection.find_one(
                    {
                        "_id": ObjectId(exam_id)
                    }
                )

            except Exception:

                examination = None


        if not examination:

            examination = examinations_collection.find_one(
                {
                    "semester": semester
                },
                sort=[
                    ("_id", -1)
                ]
            )


        if not examination:

            return render_template(
                "admin/hall_tickets.html",

                students=students,

                examinations=examinations,

                hall_tickets=list(
                    hall_tickets_collection.find({})
                    .sort("_id", -1)
                ),

                error="No examination has been created for this semester."
            )


        # ----------------------------------------------------
        # CHECK EXAMINATION SEMESTER
        # ----------------------------------------------------

        try:

            examination_semester = int(
                examination.get(
                    "semester",
                    0
                )
            )

        except (TypeError, ValueError):

            examination_semester = 0


        if examination_semester != semester:

            return render_template(
                "admin/hall_tickets.html",

                students=students,

                examinations=examinations,

                hall_tickets=list(
                    hall_tickets_collection.find({})
                    .sort("_id", -1)
                ),

                error="Selected examination does not belong to the student's semester."
            )


        # ----------------------------------------------------
        # BUILD HALL TICKET SUBJECTS
        # ----------------------------------------------------

        hall_ticket_subjects = []


        for subject in selected_subjects:

            subject_id = subject.get(
                "subject_id"
            )

            subject_code = subject.get(
                "subject_code"
            )


            timetable_entry = None


            # ------------------------------------------------
            # EXACT EXAM + SUBJECT ID
            # ------------------------------------------------

            if subject_id:

                timetable_entry = timetable_collection.find_one({

                    "exam_id": str(
                        examination["_id"]
                    ),

                    "subject_id": str(
                        subject_id
                    )

                })


            # ------------------------------------------------
            # FALLBACK EXAM + SUBJECT CODE
            # ------------------------------------------------

            if not timetable_entry and subject_code:

                timetable_entry = timetable_collection.find_one({

                    "exam_id": str(
                        examination["_id"]
                    ),

                    "subject_code": subject_code

                })


            # ------------------------------------------------
            # SUBJECT ENTRY
            # ------------------------------------------------

            hall_ticket_subjects.append({

                "subject_id": subject_id,

                "subject_code": subject.get(
                    "subject_code",
                    ""
                ),

                "subject_name": subject.get(
                    "subject_name",
                    ""
                ),

                "exam_date": (

                    timetable_entry.get(
                        "exam_date",
                        examination.get(
                            "exam_date",
                            ""
                        )
                    )

                    if timetable_entry

                    else examination.get(
                        "exam_date",
                        ""
                    )

                ),

                "start_time": (

                    timetable_entry.get(
                        "start_time",
                        ""
                    )

                    if timetable_entry

                    else ""

                ),

                "end_time": (

                    timetable_entry.get(
                        "end_time",
                        ""
                    )

                    if timetable_entry

                    else ""

                ),

                "venue": (

                    timetable_entry.get(
                        "venue",
                        ""
                    )

                    if timetable_entry

                    else ""

                )

            })


        # ----------------------------------------------------
        # HALL TICKET NUMBER
        # ----------------------------------------------------

        hall_ticket_number = (
            f"VTU-{semester}-{usn}"
        )


        # ----------------------------------------------------
        # UPSERT HALL TICKET
        # ----------------------------------------------------

        hall_tickets_collection.update_one(

            {
                "usn": usn,

                "exam_id": str(
                    examination["_id"]
                )
            },

            {

                "$set": {

                    # New field
                    "hall_ticket_number":
                        hall_ticket_number,

                    # Compatibility with templates that
                    # use hall_ticket_no
                    "hall_ticket_no":
                        hall_ticket_number,

                    "usn":
                        usn,

                    "student_name":
                        student.get(
                            "name",
                            ""
                        ),

                    "branch":
                        student.get(
                            "branch",
                            ""
                        ),

                    "semester":
                        semester,

                    "exam_name":
                        examination.get(
                            "exam_name",
                            ""
                        ),

                    "exam_type":
                        examination.get(
                            "exam_type",
                            ""
                        ),

                    "exam_id":
                        str(
                            examination["_id"]
                        ),

                    "subjects":
                        hall_ticket_subjects,

                    "published":
                        True,

                    "generated_at":
                        datetime.now().strftime(
                            "%d-%m-%Y %H:%M:%S"
                        )

                }

            },

            upsert=True

        )


        return redirect(
            url_for("admin_hall_tickets")
        )


    # ========================================================
    # GET - LOAD HALL TICKETS
    # ========================================================

    hall_tickets = list(
        hall_tickets_collection.find({})
        .sort("_id", -1)
    )


    return render_template(
        "admin/hall_tickets.html",

        # IMPORTANT:
        # These three variables fix the empty dropdown issue.
        students=students,

        examinations=examinations,

        hall_tickets=hall_tickets
    )


# ============================================================
# ADMIN - GET STUDENT SUBJECTS
# ============================================================

@app.route(
    "/admin/hall-tickets/student-subjects/<usn>"
)
def student_subjects(usn):

    if "admin_id" not in session:

        return jsonify({
            "error": "Unauthorized"
        }), 401


    usn = usn.strip().upper()


    registration = registrations_collection.find_one(
        {
            "usn": usn
        },
        sort=[
            ("_id", -1)
        ]
    )


    if not registration:

        return jsonify({
            "subjects": []
        })


    selected_subjects = registration.get(
        "selected_subjects"
    )


    if selected_subjects:

        return jsonify({
            "subjects": selected_subjects
        })


    # --------------------------------------------------------
    # OLD FORMAT SUPPORT
    # --------------------------------------------------------

    semester = registration.get(
        "semester"
    )


    try:

        semester = int(semester)

    except (TypeError, ValueError):

        semester = 0


    result = []


    for subject_name in registration.get(
        "subjects",
        []
    ):

        subject = subjects_collection.find_one({

            "subject_name": subject_name,

            "semester": semester

        })


        if subject:

            result.append({

                "subject_id": str(
                    subject["_id"]
                ),

                "subject_code": subject.get(
                    "subject_code",
                    ""
                ),

                "subject_name": subject.get(
                    "subject_name",
                    ""
                )

            })


    return jsonify({
        "subjects": result
    })


# ============================================================
# ADMIN - DELETE HALL TICKET
# ============================================================

@app.route(
    "/admin/hall-tickets/delete/<hall_ticket_id>"
)
def delete_hall_ticket(hall_ticket_id):

    if "admin_id" not in session:

        return redirect(
            url_for("admin_login")
        )


    try:

        hall_tickets_collection.delete_one(
            {
                "_id": ObjectId(hall_ticket_id)
            }
        )

    except Exception:

        pass


    return redirect(
        url_for("admin_hall_tickets")
    )


# ============================================================
# STUDENT - HALL TICKET
# ============================================================

@app.route("/student/hall-ticket")
def student_hall_ticket():

    if "student_id" not in session:

        return redirect(
            url_for("student_login")
        )


    usn = session.get(
        "student_usn"
    )


    hall_ticket = hall_tickets_collection.find_one({

        "usn": usn,

        "published": True

    }, sort=[

        ("_id", -1)

    ])


    if not hall_ticket:

        return render_template(
            "student/hall_ticket.html",
            hall_ticket=None
        )


    return render_template(
        "student/hall_ticket.html",
        hall_ticket=hall_ticket
    )


# ============================================================
# APPLICATION START
# ============================================================

if __name__ == "__main__":

    init_db()

    app.run(
        debug=True
    )