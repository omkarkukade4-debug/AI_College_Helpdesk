
import os
import sqlite3
from pathlib import Path
from functools import wraps
from dotenv import load_dotenv
from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash,
    jsonify,
)
from werkzeug.security import (
    generate_password_hash,
    check_password_hash,
)

def login_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if "student_id" not in session:
            flash("Please register or login to access this service.")
            return redirect(url_for("login", next=request.path))

        return view(*args, **kwargs)

    return wrapped_view

# --------------------------------------------------
# Configuration
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "college_faq.db"

# Load environment variables from the project's .env
load_dotenv(BASE_DIR / ".env")

app = Flask(__name__)

app.secret_key = os.environ.get("FLASK_SECRET_KEY")

if not app.secret_key:
    raise RuntimeError(
        "Please set FLASK_SECRET_KEY in your .env file."
    )


# --------------------------------------------------
# Database helpers
# --------------------------------------------------

def get_db_connection():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_student_db():
    """Create the students table if it does not exist."""
    conn = get_db_connection()

    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


def get_answer(question):
    """Find an FAQ answer using stored keywords."""
    question = question.lower().strip()

    if not question:
        return "Please enter a question."

    conn = get_db_connection()

    try:
        faqs = conn.execute(
            "SELECT keywords, answer FROM faqs"
        ).fetchall()
    except sqlite3.OperationalError:
        app.logger.exception("FAQ table is missing or unavailable.")
        return (
            "FAQ database is not ready yet. "
            "Please contact the administrator."
        )
    finally:
        conn.close()

    for faq in faqs:
        keywords = (faq["keywords"] or "").lower().split()

        if any(keyword in question for keyword in keywords):
            return faq["answer"]

    return (
        "Sorry, I don't have that information yet. "
        "Please contact your college office."
    )


# Create the students table at startup.
init_student_db()


# --------------------------------------------------
# Home page
# --------------------------------------------------

@app.route("/")
def home():
    return render_template("index.html")


# --------------------------------------------------
# Courses page
# --------------------------------------------------

@app.route("/courses")
@login_required
def courses():
    items = [
        "Bachelor of Computer Applications (BCA)",
        "Bachelor of Business Administration (BBA)",
        "Bachelor of Commerce (B.Com)",
        "Bachelor of Science (B.Sc)",
        "Bachelor of Arts (B.A)",
        "Master of Computer Applications (MCA)",
        "Master of Business Administration (MBA)",
    ]

    return render_template(
        "courses.html",
        title="Courses",
        description="Explore college courses and program information.",
        items=items,
    )


# --------------------------------------------------
# Admissions page
# --------------------------------------------------

@app.route("/admissions")
@login_required
def admissions():
    items = [
        "Check the official admission notification",
        "Review course eligibility requirements",
        "Prepare the required documents",
        "Contact the college office for application details",
    ]

    return render_template(
        "info_page.html",
        title="Admissions",
        description="Learn about admission procedures and requirements.",
        items=items,
    )


# --------------------------------------------------
# Exams page
# --------------------------------------------------

@app.route("/exams")
@login_required
def exams():
    items = [
        "Examination Timetable",
        "Syllabus",
        "Practical Examinations",
        "Exam Results",
        "Attendance Requirements",
    ]

    return render_template(
        "info_page.html",
        title="Exams Information",
        description="Find examination-related information and guidance.",
        items=items,
    )


# --------------------------------------------------
# Services page
# --------------------------------------------------

@app.route("/services")
@login_required
def services():
    items = [
        "Scholarship Information",
        "Bonafide Certificate",
        "Transfer Certificate",
        "Attendance Information",
        "College Holidays",
        "Library Information",
    ]

    return render_template(
        "info_page.html",
        title="Explore Services",
        description="Explore the college services available to students.",
        items=items,
    )


# --------------------------------------------------
# Scholarship page
# --------------------------------------------------

@app.route("/scholarship")
@login_required
def scholarship():
    items = [
        "Check eligibility criteria for scholarships.",
        "Keep income and education documents ready.",
        "Check official scholarship application deadlines.",
        "Contact the college office for verified details.",
    ]

    return render_template(
        "info_page.html",
        title="Scholarship Information",
        description="Explore scholarship information and application guidance.",
        items=items,
    )


# --------------------------------------------------
# Chatbot page
# --------------------------------------------------

@app.route("/chatbot")
@login_required
def chatbot():
    return render_template("chatbot.html")


# --------------------------------------------------
# Chatbot API
# --------------------------------------------------

@app.route("/ask", methods=["POST"])
@login_required
def ask():
    data = request.get_json(silent=True) or {}
    question = data.get("question", "")

    if not isinstance(question, str) or not question.strip():
        return jsonify({"answer": "Please enter a question."}), 400

    answer = get_answer(question)
    return jsonify({"answer": answer})


# --------------------------------------------------
# Admin FAQ page
# --------------------------------------------------

@app.route("/admin", methods=["GET", "POST"])
@login_required
def admin():
    message = ""

    if request.method == "POST":
        keywords = request.form.get(
            "keywords", ""
        ).strip().lower()
        answer = request.form.get("answer", "").strip()

        if not keywords or not answer:
            message = "Please enter both keywords and answer."
        else:
            conn = get_db_connection()

            try:
                conn.execute(
                    """
                    INSERT INTO faqs (keywords, answer)
                    VALUES (?, ?)
                    """,
                    (keywords, answer),
                )
                conn.commit()
                message = "FAQ saved successfully!"

            except sqlite3.Error:
                app.logger.exception("Could not save FAQ.")
                message = (
                    "Could not save the FAQ. "
                    "Check whether the FAQs table exists."
                )
            finally:
                conn.close()

    return render_template("admin.html", message=message)


# --------------------------------------------------
# Student registration
# --------------------------------------------------

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not name or not email or not password:
            flash("Please fill all fields.")
            return redirect(url_for("register"))

        if len(password) < 8:
            flash("Password must be at least 8 characters.")
            return redirect(url_for("register"))

        conn = get_db_connection()

        try:
            conn.execute(
                """
                INSERT INTO students (name, email, password_hash)
                VALUES (?, ?, ?)
                """,
                (
                    name,
                    email,
                    generate_password_hash(password),
                ),
            )
            conn.commit()

        except sqlite3.IntegrityError:
            flash("This email is already registered.")
            return redirect(url_for("register"))

        except sqlite3.Error:
            app.logger.exception("Registration database error.")
            flash("Registration failed due to a database error.")
            return redirect(url_for("register"))

        finally:
            conn.close()

        flash("Registration successful. Please login.")
        return redirect(url_for("login"))

    return render_template("register.html")


# --------------------------------------------------
# Student login
# --------------------------------------------------

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        conn = get_db_connection()

        try:
            student = conn.execute(
                "SELECT * FROM students WHERE email = ?",
                (email,),
            ).fetchone()
        finally:
            conn.close()

        if student and check_password_hash(
            student["password_hash"], password
        ):
            session.clear()
            session["student_id"] = student["id"]
            session["student_name"] = student["name"]

            return redirect(url_for("student_dashboard"))

        flash("Invalid email or password.")

    return render_template("login.html")


# --------------------------------------------------
# Student dashboard
# --------------------------------------------------

@app.route("/student-dashboard")
def student_dashboard():
    if "student_id" not in session:
        flash("Please login to access your dashboard.")
        return redirect(url_for("login"))

    return render_template(
        "student_dashboard.html",
        name=session.get("student_name", "Student"),
    )


# --------------------------------------------------
# Logout
# --------------------------------------------------

@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.")
    return redirect(url_for("login"))


# --------------------------------------------------
# Run application
# --------------------------------------------------

if __name__ == "__main__":
    app.run(debug=True)
