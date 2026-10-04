import os
from functools import wraps
from flask import Flask, render_template, redirect, url_for, request, flash, abort
from flask_login import (
    LoginManager, UserMixin, login_user, logout_user,
    login_required, current_user,
)
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect
from werkzeug.security import generate_password_hash, check_password_hash
app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get(
    "SECRET_KEY",
    "dev-secret-deyishdirin"
)
app.config["SQLALCHEMY_DATABASE_URI"] = (
    "sqlite:///C:/Users/Ilqare/Downloads/university_cabinet/university_cabinet/university.db"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)
csrf = CSRFProtect(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"
login_manager.login_message = "Please log in to view this page."
login_manager.login_message_category = "warning"


# =========================================================
# MODELS
# =========================================================

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)

    username = db.Column(
        db.String(50),
        unique=True,
        nullable=False
    )

    email = db.Column(
        db.String(120),
        unique=True,
        nullable=False
    )

    password_hash = db.Column(
        db.String(255),
        nullable=False
    )

    # student | teacher | admin
    role = db.Column(
        db.String(10),
        nullable=False
    )

    # Student's group
    group_id = db.Column(
        db.Integer,
        db.ForeignKey("group.id"),
        nullable=True
    )

    group = db.relationship(
        "Group",
        back_populates="students"
    )

    grades = db.relationship(
        "Grade",
        back_populates="student",
        foreign_keys="Grade.student_id",
        cascade="all, delete-orphan",
        order_by="Grade.semester_id"
    )

    teacher_assignments = db.relationship(
        "TeacherAssignment",
        back_populates="teacher",
        foreign_keys="TeacherAssignment.teacher_id",
        cascade="all, delete-orphan"
    )

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(
            self.password_hash,
            password
        )


class Group(db.Model):
    id = db.Column(
        db.Integer,
        primary_key=True
    )

    name = db.Column(
        db.String(50),
        unique=True,
        nullable=False
    )

    students = db.relationship(
        "User",
        back_populates="group",
        foreign_keys="User.group_id"
    )

    teacher_assignments = db.relationship(
        "TeacherAssignment",
        back_populates="group",
        cascade="all, delete-orphan"
    )


class Subject(db.Model):
    id = db.Column(
        db.Integer,
        primary_key=True
    )

    name = db.Column(
        db.String(100),
        unique=True,
        nullable=False
    )

    teacher_assignments = db.relationship(
        "TeacherAssignment",
        back_populates="subject",
        cascade="all, delete-orphan"
    )

    grades = db.relationship(
        "Grade",
        back_populates="subject",
        cascade="all, delete-orphan"
    )
class AcademicYear(db.Model):
    id = db.Column(
        db.Integer,
        primary_key=True
    )
    name = db.Column(
        db.String(20),
        unique=True,
        nullable=False
    )
    semesters = db.relationship(
        "Semester",
        back_populates="academic_year",
        cascade="all, delete-orphan"
    )
class Semester(db.Model):
    id = db.Column(
        db.Integer,
        primary_key=True
    )
    name = db.Column(
        db.String(30),
        nullable=False
    )
    academic_year_id = db.Column(
        db.Integer,
        db.ForeignKey("academic_year.id"),
        nullable=False
    )
    academic_year = db.relationship(
        "AcademicYear",
        back_populates="semesters"
    )
    grades = db.relationship(
        "Grade",
        back_populates="semester",
        cascade="all, delete-orphan"
    )
    __table_args__ = (
        db.UniqueConstraint(
            "name",
            "academic_year_id",
            name="uq_semester_year"
        ),
    )
class TeacherAssignment(db.Model):
    id = db.Column(
        db.Integer,
        primary_key=True
    )
    teacher_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id"),
        nullable=False
    )
    subject_id = db.Column(
        db.Integer,
        db.ForeignKey("subject.id"),
        nullable=False
    )
    group_id = db.Column(
        db.Integer,
        db.ForeignKey("group.id"),
        nullable=False
    )
    teacher = db.relationship(
        "User",
        back_populates="teacher_assignments",
        foreign_keys=[teacher_id]
    )

    subject = db.relationship(
        "Subject",
        back_populates="teacher_assignments"
    )

    group = db.relationship(
        "Group",
        back_populates="teacher_assignments"
    )

    # Same Subject + Group cannot belong to two teachers
    __table_args__ = (
        db.UniqueConstraint(
            "subject_id",
            "group_id",
            name="uq_subject_group_teacher"
        ),
    )


class Grade(db.Model):
    id = db.Column(
        db.Integer,
        primary_key=True
    )

    student_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id"),
        nullable=False
    )

    subject_id = db.Column(
        db.Integer,
        db.ForeignKey("subject.id"),
        nullable=False
    )

    semester_id = db.Column(
        db.Integer,
        db.ForeignKey("semester.id"),
        nullable=False
    )

    grade = db.Column(
        db.Float,
        nullable=False
    )

    student = db.relationship(
        "User",
        back_populates="grades",
        foreign_keys=[student_id]
    )

    subject = db.relationship(
        "Subject",
        back_populates="grades"
    )

    semester = db.relationship(
        "Semester",
        back_populates="grades"
    )

    # One student cannot have two grades
    # for the same subject in the same semester.
    __table_args__ = (
        db.UniqueConstraint(
            "student_id",
            "subject_id",
            "semester_id",
            name="uq_student_subject_semester"
        ),
    )


# =========================================================
# LOGIN
# =========================================================

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(
        User,
        int(user_id)
    )


# =========================================================
# ROLE DECORATOR
# =========================================================

def role_required(role):

    def decorator(f):

        @wraps(f)
        @login_required
        def wrapper(*args, **kwargs):

            if current_user.role != role:
                abort(403)

            return f(*args, **kwargs)

        return wrapper

    return decorator
# =========================================================
# INDEX
# =========================================================
@app.route("/")
def index():

    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))

    return redirect(url_for("login"))
# =========================================================
# REGISTER
# =========================================================
@app.route("/register", methods=["GET", "POST"])
def register():

    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))

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

        confirm = request.form.get(
            "confirm",
            ""
        )

        role = request.form.get(
            "role",
            ""
        )

        error = None

        if not username or not email or not password:
            error = "Please fill in all fields."

        elif role not in ("student", "teacher"):
            error = "Please select a valid role."

        elif len(password) < 6:
            error = "Password must be at least 6 characters."

        elif password != confirm:
            error = "Passwords do not match."

        elif User.query.filter_by(
            username=username
        ).first():

            error = "This username already exists."

        elif User.query.filter_by(
            email=email
        ).first():

            error = "This email is already registered."

        if error:

            flash(
                error,
                "danger"
            )

        else:

            user = User(
                username=username,
                email=email,
                role=role
            )

            user.set_password(password)

            db.session.add(user)
            db.session.commit()

            flash(
                "Registration successful! You can now log in.",
                "success"
            )

            return redirect(
                url_for("login")
            )

    return render_template(
        "register.html"
    )


# =========================================================
# LOGIN
# =========================================================

@app.route("/login", methods=["GET", "POST"])
def login():

    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))

    if request.method == "POST":

        username = request.form.get(
            "username",
            ""
        ).strip()

        password = request.form.get(
            "password",
            ""
        )

        user = User.query.filter_by(
            username=username
        ).first()

        if user and user.check_password(password):

            login_user(user)

            return redirect(
                url_for("dashboard")
            )

        flash(
            "Incorrect username or password.",
            "danger"
        )

    return render_template(
        "login.html"
    )


# =========================================================
# LOGOUT
# =========================================================

@app.route("/logout", methods=["POST"])
@login_required
def logout():

    logout_user()

    flash(
        "You have been logged out.",
        "info"
    )

    return redirect(
        url_for("login")
    )


# =========================================================
# DASHBOARD REDIRECT
# =========================================================

@app.route("/dashboard")
@login_required
def dashboard():

    if current_user.role == "admin":

        return redirect(
            url_for("admin_dashboard")
        )

    if current_user.role == "teacher":

        return redirect(
            url_for("teacher_dashboard")
        )

    return redirect(
        url_for("student_dashboard")
    )
@app.route("/admin/groups", methods=["GET", "POST"])
@login_required
def manage_groups():

    if current_user.role != "admin":
        abort(403)

    if request.method == "POST":
        name = request.form.get("name", "").strip()

        if name:
            existing_group = Group.query.filter_by(name=name).first()

            if not existing_group:
                group = Group(name=name)
                db.session.add(group)
                db.session.commit()

        return redirect(url_for("manage_groups"))

    groups = Group.query.order_by(Group.name).all()

    return render_template(
        "manage_groups.html",
        groups=groups
    )

# =========================================================
# STUDENT DASHBOARD
# =========================================================

@app.route("/student")
@role_required("student")
def student_dashboard():

    grades = current_user.grades

    average = (
        round(
            sum(g.grade for g in grades) / len(grades),
            2
        )
        if grades
        else None
    )

    return render_template(
        "student_dashboard.html",
        grades=grades,
        average=average
    )


# =========================================================
# TEACHER DASHBOARD
# =========================================================

@app.route("/teacher")
@role_required("teacher")
def teacher_dashboard():

    assignments = TeacherAssignment.query.filter_by(
        teacher_id=current_user.id
    ).all()

    return render_template(
        "teacher_dashboard.html",
        assignments=assignments
    )


# =========================================================
# SAVE GRADE
# =========================================================

@app.route("/teacher/grade", methods=["POST"])
@role_required("teacher")
def save_grade():

    student_id = request.form.get(
        "student_id",
        type=int
    )

    assignment_id = request.form.get(
        "assignment_id",
        type=int
    )

    semester_id = request.form.get(
        "semester_id",
        type=int
    )

    grade_value = request.form.get(
        "grade",
        type=float
    )

    student = (
        db.session.get(User, student_id)
        if student_id
        else None
    )

    assignment = (
        db.session.get(
            TeacherAssignment,
            assignment_id
        )
        if assignment_id
        else None
    )

    semester = (
        db.session.get(
            Semester,
            semester_id
        )
        if semester_id
        else None
    )

    if not student or student.role != "student":

        flash(
            "Student not found.",
            "danger"
        )

    elif not assignment:

        flash(
            "Assignment not found.",
            "danger"
        )

    elif assignment.teacher_id != current_user.id:

        abort(403)

    elif student.group_id != assignment.group_id:

        flash(
            "This student is not in your assigned group.",
            "danger"
        )

    elif not semester:

        flash(
            "Semester not found.",
            "danger"
        )

    elif grade_value is None or not (
        0 <= grade_value <= 100
    ):

        flash(
            "Grade must be between 0 and 100.",
            "danger"
        )

    else:

        existing = Grade.query.filter_by(
            student_id=student.id,
            subject_id=assignment.subject_id,
            semester_id=semester.id
        ).first()

        if existing:

            existing.grade = grade_value

            flash(
                f"Grade for '{student.username}' was updated.",
                "success"
            )

        else:

            db.session.add(
                Grade(
                    student_id=student.id,
                    subject_id=assignment.subject_id,
                    semester_id=semester.id,
                    grade=grade_value
                )
            )

            flash(
                f"Grade for '{student.username}' was added.",
                "success"
            )

        db.session.commit()

    return redirect(
        url_for("teacher_dashboard")
    )
# =========================================================
# ADMIN DASHBOARD
# =========================================================
@app.route("/admin")
@role_required("admin")
def admin_dashboard():

    student_count = User.query.filter_by(
        role="student"
    ).count()

    teacher_count = User.query.filter_by(
        role="teacher"
    ).count()

    group_count = Group.query.count()

    subject_count = Subject.query.count()

    return render_template(
        "admin_dashboard.html",
        student_count=student_count,
        teacher_count=teacher_count,
        group_count=group_count,
        subject_count=subject_count
    )
# =========================================================
# ERROR 403
# =========================================================
@app.errorhandler(403)
def forbidden(_):
    return render_template(
        "base.html",
        forbidden=True
    ), 403
# =========================================================
# CREATE DATABASE
# =========================================================
with app.app_context():
    db.create_all()

    if not User.query.filter_by(username="admin").first():
        admin = User(
            username="admin",
            email="admin@gmail.com",
            role="admin"
        )
        admin.set_password("admin123")
        db.session.add(admin)
        db.session.commit()
# =========================================================
# RUN
# =========================================================

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=os.environ.get("FLASK_DEBUG") == "1"
    )