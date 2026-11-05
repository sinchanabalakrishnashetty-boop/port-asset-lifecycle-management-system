# ================= PORT ASSET MANAGEMENT SYSTEM =================
from flask import Flask, render_template, request, redirect, session, g, url_for, jsonify, make_response
import sqlite3
from datetime import date, datetime
import os
import re
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "supersecretkey"
app.config['UPLOAD_FOLDER'] = os.path.join('static', 'uploads')

# Ensure upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)


PHONE_PATTERN = re.compile(r"^\d{10}$")
EMAIL_PATTERN = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
NAME_PATTERN = re.compile(r"^[A-Za-z. ]+$")
LABEL_PATTERN = re.compile(r"^[A-Za-z .,&()/-]+$")
CODE_PATTERN = re.compile(r"^[A-Za-z0-9._/-]+$")
VENDOR_PATTERN = re.compile(r"^[A-Za-z ]+$")
TEXTAREA_PATTERN = re.compile(r"^[A-Za-z -]*$")
WARRANTY_PATTERN = re.compile(r"^[A-Za-z0-9 -]*$")


def is_valid_phone(phone):
    return bool(PHONE_PATTERN.fullmatch(phone))


def is_valid_email(email):
    return bool(EMAIL_PATTERN.fullmatch(email))


def is_valid_password(password):
    return (
        len(password) >= 8
        and any(c.isupper() for c in password)
        and any(c.islower() for c in password)
        and any(c.isdigit() for c in password)
    )


def is_valid_name(value):
    return bool(NAME_PATTERN.fullmatch(value))


def is_valid_label(value):
    return bool(LABEL_PATTERN.fullmatch(value))


def is_valid_code(value):
    return bool(CODE_PATTERN.fullmatch(value))


def is_valid_vendor(value):
    return bool(VENDOR_PATTERN.fullmatch(value))


def is_valid_textarea_value(value):
    return bool(TEXTAREA_PATTERN.fullmatch(value))


def is_valid_warranty(value):
    return bool(WARRANTY_PATTERN.fullmatch(value))


def is_valid_non_negative_number(value):
    try:
        return float(value) >= 0
    except (TypeError, ValueError):
        return False


def is_valid_iso_date(value):
    try:
        parsed = datetime.strptime(value, "%Y-%m-%d").date()
        return parsed <= date.today()
    except ValueError:
        return False


def is_valid_datetime_local(value):
    try:
        datetime.strptime(value, "%Y-%m-%dT%H:%M")
        return True
    except ValueError:
        return False


def validate_asset_form(form, require_department=False):
    asset_name = form.get("asset_name", "").strip()
    external_id = form.get("external_id", "").strip()
    asset_type = form.get("asset_type", "").strip()
    department = form.get("department", "").strip()
    location = form.get("location", "").strip()
    purchase_date = form.get("purchase_date", "").strip()
    cost = form.get("cost", "").strip()
    vendor = form.get("vendor", "").strip()
    warranty_period = form.get("warranty_period", "").strip()
    condition = form.get("condition", "").strip()
    asset_status = form.get("asset_status", "").strip()
    serial_number = form.get("serial_number", "").strip()
    incharge = form.get("incharge", "").strip()
    details = form.get("details", "").strip()
    remarks = form.get("remarks", "").strip()

    if not asset_name:
        return "Asset name is required"
    if len(asset_name) < 3 or len(asset_name) > 100:
        return "Asset name must be between 3 and 100 characters"
    if not is_valid_name(asset_name):
        return "Asset name must contain only letters and spaces"
    if external_id and (len(external_id) > 30 or not is_valid_code(external_id)):
        return "Asset ID must contain only letters, numbers, dots, underscores, slashes, or hyphens"
    if not asset_type:
        return "Asset type is required"
    if require_department and not department:
        return "Department is required"
    if location and (len(location) > 100 or not is_valid_textarea_value(location)):
        return "Location can contain only letters, spaces, and hyphens"
    if purchase_date and not is_valid_iso_date(purchase_date):
        return "Purchase date must be a valid date and cannot be in the future"
    if cost and not is_valid_non_negative_number(cost):
        return "Cost must be a valid non-negative number"
    if vendor and (len(vendor) > 100 or not is_valid_vendor(vendor)):
        return "Vendor must contain only letters and spaces"
    if warranty_period and not is_valid_warranty(warranty_period):
        return "Warranty can contain only letters, numbers, spaces, and hyphens"
    if warranty_period and len(warranty_period) > 50:
        return "Warranty must be 50 characters or fewer"
    if not condition:
        return "Condition is required"
    if not asset_status:
        return "Asset status is required"
    if serial_number and (len(serial_number) > 50 or not is_valid_code(serial_number)):
        return "Serial number must contain only letters, numbers, dots, underscores, slashes, or hyphens"
    if incharge and (len(incharge) > 100 or not is_valid_name(incharge)):
        return "In-charge name must contain only letters, spaces, and dots"
    if details and not is_valid_textarea_value(details):
        return "Asset details can contain only letters, spaces, and hyphens"
    if len(details) > 1000:
        return "Asset details must be 1000 characters or fewer"
    if remarks and not is_valid_textarea_value(remarks):
        return "Remarks can contain only letters, spaces, and hyphens"
    if len(remarks) > 500:
        return "Remarks must be 500 characters or fewer"
    return None


def validate_maintenance_submission(details, cost):
    if not details:
        return "Repair details are required"
    if len(details) < 5:
        return "Repair details must be at least 5 characters long"
    if len(details) > 1000:
        return "Repair details must be 1000 characters or fewer"
    if not cost:
        return "Repair cost is required"
    if not is_valid_non_negative_number(cost):
        return "Repair cost must be a valid non-negative number"
    return None


# ================= DATABASE INIT =================
def init_db():
    conn = sqlite3.connect("port_asset.db")
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = ON")

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        email TEXT ,
        phone TEXT,
        department TEXT,
        role TEXT,
        password TEXT,
        status TEXT DEFAULT 'Active'
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS assets (
        asset_id INTEGER PRIMARY KEY AUTOINCREMENT,
        external_id TEXT,
        asset_name TEXT,
        asset_type TEXT,
        category TEXT,
        department TEXT,
        location TEXT,
        purchase_date TEXT,
        cost REAL,
        vendor TEXT,
        warranty_period TEXT,
        condition TEXT,
        asset_status TEXT DEFAULT 'Active',
        serial_number TEXT,
        photo TEXT,
        incharge TEXT,
        remarks TEXT,
        history TEXT,
        details TEXT,
        approval_status TEXT DEFAULT 'Pending'
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS maintenance (
        maintenance_id INTEGER PRIMARY KEY AUTOINCREMENT,
        asset_id INTEGER,
        problem_description TEXT,
        request_date TEXT DEFAULT CURRENT_DATE,
        assigned_staff INTEGER,
        repair_details TEXT,
        repair_cost REAL,
        completion_date TEXT,
        status TEXT DEFAULT 'Pending'
    )
    """)
   
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS inspection (
        inspection_id INTEGER PRIMARY KEY AUTOINCREMENT,
        asset_id INTEGER,
        inspection_date TEXT DEFAULT CURRENT_DATE,
        inspector_id INTEGER,
        inspector_name TEXT,
        inspector_designation TEXT,
        inspector_organisation TEXT,
        condition_status TEXT,
        remarks TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS approvals (
        approval_id INTEGER PRIMARY KEY AUTOINCREMENT,
        asset_id INTEGER,
        request_type TEXT,
        requested_by INTEGER,
        approval_status TEXT DEFAULT 'Pending',
        remarks TEXT,
        approval_date TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS lifecycle (
        lifecycle_id INTEGER PRIMARY KEY AUTOINCREMENT,
        asset_id INTEGER,
        stage TEXT,
        stage_date TEXT DEFAULT CURRENT_DATE,
        notes TEXT,
        actor_id INTEGER,
        actor_name TEXT,
        actor_role TEXT
    )
    """)

    conn.commit()
    conn.close()

    # Ensure existing DB has `department` column for users (safe migration)
    try:
        conn = sqlite3.connect("port_asset.db")
        cur = conn.cursor()
        cur.execute("PRAGMA table_info(users)")
        cols = [r[1] for r in cur.fetchall()]
        if 'department' not in cols:
            cur.execute("ALTER TABLE users ADD COLUMN department TEXT")
            conn.commit()
    except Exception:
        pass
    finally:
        try:
            conn.close()
        except Exception:
            pass

# Safe migration: ensure maintenance and inspection tables have new columns
try:
    conn = sqlite3.connect("port_asset.db")
    cur = conn.cursor()
    # maintenance: scheduled_time
    cur.execute("PRAGMA table_info(maintenance)")
    mcols = [r[1] for r in cur.fetchall()]
    if 'scheduled_time' not in mcols:
        try:
            cur.execute("ALTER TABLE maintenance ADD COLUMN scheduled_time TEXT")
            conn.commit()
        except Exception:
            pass

    # maintenance: department (which department the maintenance is assigned to)
    if 'department' not in mcols:
        try:
            cur.execute("ALTER TABLE maintenance ADD COLUMN department TEXT")
            conn.commit()
        except Exception:
            pass

    # inspection: inspector_name, inspector_designation, inspector_organisation
    cur.execute("PRAGMA table_info(inspection)")
    icols = [r[1] for r in cur.fetchall()]
    adds = {
        'inspector_name': 'TEXT',
        'inspector_designation': 'TEXT',
        'inspector_organisation': 'TEXT'
    }
    for name, definition in adds.items():
        if name not in icols:
            try:
                cur.execute(f"ALTER TABLE inspection ADD COLUMN {name} {definition}")
                conn.commit()
            except Exception:
                pass
except Exception:
    pass
finally:
    try:
        conn.close()
    except Exception:
        pass

# Safe migration: ensure assets table has new columns (for existing DBs)
try:
    conn = sqlite3.connect("port_asset.db")
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(assets)")
    cols = [r[1] for r in cur.fetchall()]
    add_cols = {
        'external_id': "TEXT",
        'serial_number': "TEXT",
        'photo': "TEXT",
        'incharge': "TEXT",
        'remarks': "TEXT",
        'history': "TEXT",
        'details': "TEXT",
        'approval_status': "TEXT DEFAULT 'Pending'"
    }
    for name, definition in add_cols.items():
        if name not in cols:
            try:
                cur.execute(f"ALTER TABLE assets ADD COLUMN {name} {definition}")
                conn.commit()
            except Exception:
                pass
except Exception:
    pass
finally:
    try:
        conn.close()
    except Exception:
        pass

# Safe migration: ensure lifecycle has actor columns
try:
    conn = sqlite3.connect("port_asset.db")
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(lifecycle)")
    lcols = [r[1] for r in cur.fetchall()]
    lifecycle_adds = {
        'actor_id': 'INTEGER',
        'actor_name': 'TEXT',
        'actor_role': 'TEXT'
    }
    for name, definition in lifecycle_adds.items():
        if name not in lcols:
            try:
                cur.execute(f"ALTER TABLE lifecycle ADD COLUMN {name} {definition}")
                conn.commit()
            except Exception:
                pass
except Exception:
    pass
finally:
    try:
        conn.close()
    except Exception:
        pass

init_db()

# Safe migration for maintenance.department column
try:
    conn = sqlite3.connect("port_asset.db")
    cur = conn.cursor()

    cur.execute("PRAGMA table_info(maintenance)")
    columns = [col[1] for col in cur.fetchall()]

    if "department" not in columns:
        cur.execute("ALTER TABLE maintenance ADD COLUMN department TEXT")
        conn.commit()

except Exception:
    pass
finally:
    conn.close()
# ================= DB HELPER =================
def get_db():
    if 'db' not in g:
        # increase timeout to wait for locks, enable WAL for better concurrency
        g.db = sqlite3.connect("port_asset.db", timeout=10, check_same_thread=False)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
        try:
            g.db.execute("PRAGMA journal_mode=WAL")
        except Exception:
            pass
    return g.db


@app.teardown_appcontext
def close_db(exception=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()


# ================= PREDICTIVE MAINTENANCE =================
def calculate_next_maintenance(cursor, asset_id):
    """
    Calculate predicted next maintenance date based on:
    1. Average interval between completed maintenance records
    2. Last completion date
    Returns: (next_date_str, days_until, message_type)
    """
    try:
        # Get all completed maintenance records ordered by completion date
        cursor.execute("""
            SELECT completion_date FROM maintenance
            WHERE asset_id=? AND status='Completed' AND completion_date IS NOT NULL
            ORDER BY completion_date ASC
        """, (asset_id,))
        completed = cursor.fetchall()
        
        if len(completed) < 2:
            # Not enough data; return None
            return None, None, None
        
        # Calculate intervals between consecutive completions
        intervals = []
        for i in range(1, len(completed)):
            try:
                prev_date = datetime.strptime(completed[i-1][0], "%Y-%m-%d").date()
                curr_date = datetime.strptime(completed[i][0], "%Y-%m-%d").date()
                delta = (curr_date - prev_date).days
                if delta > 0:
                    intervals.append(delta)
            except Exception:
                pass
        
        if not intervals:
            return None, None, None
        
        # Calculate average interval
        avg_interval = sum(intervals) // len(intervals)
        
        # Get last completion date
        try:
            last_date = datetime.strptime(completed[-1][0], "%Y-%m-%d").date()
        except Exception:
            return None, None, None
        
        # Calculate next predicted maintenance
        from datetime import timedelta
        next_date = last_date + timedelta(days=avg_interval)
        today = date.today()
        days_until = (next_date - today).days
        
        next_date_str = next_date.strftime("%Y-%m-%d")
        
        # Determine message type
        if days_until < 0:
            msg_type = "overdue"
        elif days_until <= 7:
            msg_type = "urgent"
        elif days_until <= 30:
            msg_type = "upcoming"
        else:
            msg_type = "scheduled"
        
        return next_date_str, days_until, msg_type
    except Exception:
        return None, None, None


# ================= LIFECYCLE HELPER =================
def add_lifecycle(asset_id, stage, notes="", conn=None):
    # Use provided connection if given (caller may manage commit/close),
    # otherwise use the request-scoped connection from get_db().
    if conn is None:
        conn = get_db()

    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO lifecycle (asset_id, stage, notes, actor_id, actor_name, actor_role)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (asset_id, stage, notes, getattr(g, 'actor_id', None), getattr(g, 'actor_name', None), getattr(g, 'actor_role', None)))
    # commit so lifecycle entry is persisted promptly
    try:
        conn.commit()
    except Exception:
        pass


# ================= LOGIN =================
@app.route("/", methods=["GET", "POST"])
@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    selected_role = ""
    phone_value = ""
    
    if request.method == "POST":
        conn = get_db()
        cursor = conn.cursor()

        # Only accept phone + password for login
        phone = request.form.get("phone", "").strip()
        password = request.form.get("password", "")
        selected_role = request.form.get("role", "").strip().lower()
        phone_value = phone

        # Validate inputs
        if not phone:
            error = "Phone number is required"
        elif not is_valid_phone(phone):
            error = "Phone number must be exactly 10 digits"
        elif selected_role not in ("admin", "staff"):
            error = "Please choose a valid role"
        elif not password:
            error = "Password is required"
        else:
            cursor.execute(
                "SELECT user_id, name, role, department, status FROM users WHERE phone=? AND password=?",
                (phone, password)
            )

            user = cursor.fetchone()

            if user:
                # Check if user account is active
                if user[4] == "Active":
                    account_role = (user[2] or "").lower()

                    # Access rule:
                    # - Admin account: can choose admin or staff mode
                    # - Staff account: can choose only staff mode
                    if selected_role == "admin" and account_role != "admin":
                        error = "Only admin accounts can log in as Admin"
                    elif selected_role == "staff" and account_role not in ("staff", "admin"):
                        error = "This account cannot log in as Staff"
                    else:
                        session["user_id"] = user[0]
                        session["user"] = user[1]
                        session["role"] = selected_role
                        session["account_role"] = account_role
                        session["department"] = user[3]

                        if selected_role == "admin":
                            return redirect("/admin")
                        return redirect("/staff")
                else:
                    error = "Your account is inactive. Please contact administrator."
            else:
                error = "Invalid phone number or password. Please try again."

        return render_template("login.html", error=error, selected_role=selected_role, phone_value=phone_value)

    return render_template("login.html", selected_role=selected_role, phone_value=phone_value)


# ================= REGISTER =================
@app.route("/register", methods=["GET", "POST"])
def register():
    error = None
    
    if request.method == "POST":
        conn = get_db()
        cursor = conn.cursor()
        
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        phone = request.form.get("phone", "").strip()
        department = request.form.get("department", "")
        role = request.form.get("role", "")
        password = request.form.get("password", "")
        
        # Validate required fields
        if not name:
            error = "Full name is required"
        elif len(name) < 3:
            error = "Full name must be at least 3 characters long"
        elif not email:
            error = "Email is required"
        elif not is_valid_email(email):
            error = "Enter a valid email address"
        elif not phone:
            error = "Phone number is required"
        elif not is_valid_phone(phone):
            error = "Phone number must be exactly 10 digits"
        elif not department:
            error = "Department is required"
        elif not role:
            error = "Role is required"
        elif not password:
            error = "Password is required"
        # Validate password strength: min 8 chars, at least 1 uppercase, 1 lowercase, 1 digit
        elif len(password) < 8:
            error = "Password must be at least 8 characters long"
        elif not any(c.isupper() for c in password):
            error = "Password must contain at least one uppercase letter"
        elif not any(c.islower() for c in password):
            error = "Password must contain at least one lowercase letter"
        elif not any(c.isdigit() for c in password):
            error = "Password must contain at least one digit"
        elif not is_valid_password(password):
            error = "Password does not meet the required format"
        else:
            # Check if name already exists
            cursor.execute("SELECT user_id FROM users WHERE name=?", (name,))
            if cursor.fetchone():
                error = "Name already registered. Please use a different name."
            else:
                # Check if phone already exists
                cursor.execute("SELECT user_id FROM users WHERE phone=?", (phone,))
                if cursor.fetchone():
                    error = "Phone number already registered. Please use a different phone number."
                else:
                    # Check if email already exists
                    cursor.execute("SELECT user_id FROM users WHERE email=?", (email,))
                    if cursor.fetchone():
                        error = "Email already registered. Please use a different email."
        
        if not error:
            cursor.execute("""
            INSERT INTO users(name,email,phone,department,role,password,status)
            VALUES(?,?,?,?,?,?,?)
            """,(name, email, phone, department, role, password, "Active"))
            conn.commit()
            return redirect("/login")
    
    return render_template("register.html", error=error)


# ================= ADMIN DASHBOARD =================
@app.route("/admin")
def admin_dashboard():
    if session.get("role") != "admin":
        return redirect("/login")

    conn = get_db()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    department = session.get("department", "")

    if department == "Administration":
        cursor.execute("SELECT COUNT(*) FROM assets")
        total_assets = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM assets WHERE asset_status='Active'")
        active_assets = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM maintenance")
        total_maintenance = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM maintenance WHERE status='repair_submitted'")
        pending_approvals = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM users")
        total_users = cursor.fetchone()[0]
    else:
        cursor.execute("SELECT COUNT(*) FROM assets WHERE department=?", (department,))
        total_assets = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM assets WHERE asset_status='Active' AND department=?", (department,))
        active_assets = cursor.fetchone()[0]

        cursor.execute("""
        SELECT COUNT(*) FROM maintenance m
        WHERE m.department=?
        """, (department,))
        total_maintenance = cursor.fetchone()[0]

        cursor.execute("""
        SELECT COUNT(*) FROM maintenance m
        WHERE m.status='repair_submitted' AND m.department=?
        """, (department,))
        pending_approvals = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM users WHERE department=?", (department,))
        total_users = cursor.fetchone()[0]
    
    # Find assets with no inspection in the last 30 days (including never inspected)
    if department == "Administration":
        cursor.execute("""
        SELECT asset_id, asset_name
        FROM assets
        WHERE asset_id NOT IN (
            SELECT asset_id FROM inspection
            WHERE inspection_date > date('now','-30 day')
        )
        """)
    else:
        cursor.execute("""
        SELECT asset_id, asset_name
        FROM assets
        WHERE department=? AND asset_id NOT IN (
            SELECT asset_id FROM inspection
            WHERE inspection_date > date('now','-30 day')
        )
        """, (department,))
    
    overdue_assets = cursor.fetchall()
    overdue_count = len(overdue_assets)

    # Map departments to templates
    department_templates = {
        "Administration": "admin_dashboard.html",
        "Finance": "admin_dashboard_finance.html",
        "Marine": "admin_dashboard_marine.html",
        "Civil": "admin_dashboard_civil.html",
        "Mechanical": "admin_dashboard_mechanical.html",
        "Medical": "admin_dashboard_medical.html",
        "Traffic": "admin_dashboard_traffic.html"
    }
    
    template = department_templates.get(department, "admin_dashboard.html")

    return render_template(template,
                           department=department,
                           total_assets=total_assets,
                           active_assets=active_assets,
                           total_maintenance=total_maintenance,
                           pending_approvals=pending_approvals,
                           total_users=total_users,
                           overdue_count=overdue_count,
                           overdue_assets=overdue_assets)


# ================= ADMIN USERS =================
@app.route("/admin/users", methods=["GET","POST"])
def admin_users():
    if session.get("role") != "admin":
        return redirect("/login")

    conn = get_db()
    cursor = conn.cursor()

    user_department = session.get("department", "")

    if request.method == "POST":
           # If not Administration, force the department to be the user's department
           department = request.form.get("department", "")
           if user_department != "Administration":
               department = user_department
           
           cursor.execute("""
           INSERT INTO users(name,email,phone,department,role,password,status)
           VALUES(?,?,?,?,?,?,?)
           """,(request.form["name"],
               request.form["email"],
               request.form["phone"],
               department,
               request.form["role"],
               request.form["password"],
               request.form["status"]))
    conn.commit()

    # If user is from Administration, show all users; otherwise show only their department's users
    if user_department == "Administration":
        cursor.execute("SELECT user_id,name,email,department,role,status FROM users")
    else:
        cursor.execute("SELECT user_id,name,email,department,role,status FROM users WHERE department=?", (user_department,))
    
    users = cursor.fetchall()

    return render_template("admin_users.html", users=users, user_department=user_department)


# ================= ADMIN ASSETS =================
@app.route("/admin/assets", methods=["GET", "POST"])
def admin_assets():
    # Allow both admin and staff to access department-scoped assets
    if session.get("role") not in ("admin", "staff"):
        return redirect("/login")

    conn = get_db()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    user_department = session.get("department", "")
    error = None
    success = request.args.get("success")

    if request.method == "POST":
        print("FORM SUBMITTED")
        print(request.form)
        error = validate_asset_form(
            request.form,
            require_department=(user_department == "Administration")
        )

        if not error:

            # Handle photo upload
            photo_path = None
            photo_file = request.files.get("photo")

            if photo_file and photo_file.filename:
                filename = secure_filename(photo_file.filename)
                save_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
                photo_file.save(save_path)
                photo_path = os.path.join("uploads", filename).replace("\\", "/")

            # Force department if not Administration
            asset_department = request.form.get("department", "")
            if user_department != "Administration":
                asset_department = user_department

            cursor.execute("""
                INSERT INTO assets(
                    external_id, asset_name, asset_type, department,
                    location, purchase_date, cost, vendor,
                    warranty_period, condition, asset_status,
                    serial_number, photo, incharge,
                    remarks, details, approval_status
                )
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                request.form.get("external_id"),
                request.form.get("asset_name"),
                request.form.get("asset_type"),
                asset_department,
                request.form.get("location"),
                request.form.get("purchase_date"),
                request.form.get("cost"),
                request.form.get("vendor"),
                request.form.get("warranty_period"),
                request.form.get("condition"),
                request.form.get("asset_status"),
                request.form.get("serial_number"),
                photo_path,
                request.form.get("incharge"),
                request.form.get("remarks"),
                request.form.get("details"),
                request.form.get("approval_status")
            ))

            conn.commit()

            # Add lifecycle entry
            asset_id = cursor.lastrowid
            g.actor_id = session.get("user_id")
            g.actor_name = session.get("user")
            g.actor_role = session.get("role")

            add_lifecycle(asset_id, "Asset Created", "Asset added to system")

            return redirect("/admin/assets?success=1")

    # GET assets with optional filters
    filter_category  = request.args.get("filter_category", "").strip()
    filter_text      = request.args.get("filter_text", "").strip()
    filter_dept      = request.args.get("filter_dept", "").strip()
    filter_condition = request.args.get("filter_condition", "").strip()

    # Backward compatibility for older filter URLs that didn't send category.
    if not filter_category:
        if filter_dept:
            filter_category = "department"
        elif filter_condition:
            filter_category = "condition"

    where_clauses = []
    params = []

    # Department scope: non-admin users are always restricted to their dept
    if user_department != "Administration":
        where_clauses.append("department = ?")
        params.append(user_department)

    # Apply the selected filter category
    if filter_category == "department" and filter_dept:
        # Admin can filter any department; department users are already scoped.
        if user_department == "Administration":
            where_clauses.append("department = ?")
            params.append(filter_dept)
    elif filter_category == "condition" and filter_condition:
        where_clauses.append("condition = ?")
        params.append(filter_condition)
    elif filter_category == "name" and filter_text:
        where_clauses.append("asset_name LIKE ?")
        params.append(f"%{filter_text}%")
    elif filter_category == "external_id" and filter_text:
        where_clauses.append("external_id LIKE ?")
        params.append(f"%{filter_text}%")
    elif filter_category == "serial" and filter_text:
        where_clauses.append("serial_number LIKE ?")
        params.append(f"%{filter_text}%")
    elif filter_category == "incharge" and filter_text:
        where_clauses.append("incharge LIKE ?")
        params.append(f"%{filter_text}%")

    query = "SELECT * FROM assets"
    if where_clauses:
        query += " WHERE " + " AND ".join(where_clauses)
    query += " ORDER BY department, asset_id DESC"

    cursor.execute(query, params)
    assets = cursor.fetchall()

    # Group by department for display (preserves order)
    from collections import OrderedDict
    assets_by_dept = OrderedDict()
    for a in assets:
        dept = a["department"] or "Unassigned"
        assets_by_dept.setdefault(dept, []).append(a)

    return render_template("admin_assets.html",
                           assets=assets,
                           assets_by_dept=assets_by_dept,
                           filter_category=filter_category,
                           filter_text=filter_text,
                           filter_dept=filter_dept,
                           filter_condition=filter_condition,
                           error=error,
                           success=success,
                           user_department=user_department)


# ================= ADMIN USERS (Department Page) =================
@app.route("/admin/users-dept", methods=["GET","POST"])
def admin_users_dept():
    if session.get("role") != "admin":
        return redirect("/login")

    conn = get_db()
    cursor = conn.cursor()

    user_department = session.get("department", "")

    if request.method == "POST":
        # Force department to current user's department
        department = user_department
        cursor.execute("""
        INSERT INTO users(name,email,phone,department,role,password,status)
        VALUES(?,?,?,?,?,?,?)
        """, (
            request.form["name"],
            request.form["email"],
            request.form.get("phone", ""),
            department,
            request.form.get("role", "user"),
            request.form.get("password", ""),
            request.form.get("status", "Active")
        ))
        conn.commit()

    # Show only users from this department
    cursor.execute("SELECT user_id,name,email,department,role,status FROM users WHERE department=?", (user_department,))
    users = cursor.fetchall()

    return render_template("admin_users_dept.html", users=users, user_department=user_department)



from datetime import date

@app.route("/admin/assign", methods=["GET", "POST"])
def admin_assign():

    if session.get("role") != "admin":
        return redirect("/login")

    conn = get_db()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    user_dept = session.get("department", "")

    # Fetch staff - filter by department if not Administration
    if user_dept == "Administration":
        cursor.execute("""
            SELECT user_id, name, department, status
            FROM users
            WHERE role='staff'
            ORDER BY department, name
        """)
    else:
        cursor.execute("""
            SELECT user_id, name, department, status
            FROM users
            WHERE role='staff' AND department=?
            ORDER BY name
        """, (user_dept,))

    staff = cursor.fetchall()

    # Fetch assets - filter by department if not Administration
    if user_dept == "Administration":
        cursor.execute("SELECT asset_id, asset_name FROM assets ORDER BY asset_name")
    else:
        cursor.execute("SELECT asset_id, asset_name FROM assets WHERE department=? ORDER BY asset_name", (user_dept,))

    assets = cursor.fetchall()

    error = None
    if request.method == "POST":
        asset_id = request.form.get("asset_id")
        problem = request.form.get("problem", "").strip()
        staff_id = request.form.get("staff_id", "").strip()
        status = request.form.get("status", "Assigned").strip() or "Assigned"
        scheduled_time = request.form.get("scheduled_time", "").strip() or None

        # Convert to int
        try:
            asset_id = int(asset_id) if asset_id else None
            staff_id = int(staff_id) if staff_id else None
        except ValueError:
            asset_id = None
            staff_id = None

        if not asset_id:
            error = "Select an asset"
        elif not staff_id:
            error = "Select a staff member"
        elif not problem:
            error = "Enter a problem description"
        elif len(problem) < 5:
            error = "Problem description must be at least 5 characters long"
        elif len(problem) > 1000:
            error = "Problem description must be 1000 characters or fewer"
        elif scheduled_time and not is_valid_datetime_local(scheduled_time):
            error = "Scheduled time is invalid"
        else:
            cursor.execute("SELECT department FROM assets WHERE asset_id=?", (asset_id,))
            asset_dept = cursor.fetchone()[0]
            cursor.execute("SELECT name FROM users WHERE user_id=? AND role='staff'", (staff_id,))
            staff_row = cursor.fetchone()
            if not staff_row:
                error = "Invalid staff member"
            else:
                cursor.execute(
                    "INSERT INTO maintenance(asset_id, problem_description, assigned_staff, status, scheduled_time, department) VALUES (?,?,?,?,?,?)",
                    (asset_id, problem, staff_id, status, scheduled_time, asset_dept),
                )
                conn.commit()

                g.actor_id = session.get("user_id")
                g.actor_name = session.get("user")
                g.actor_role = session.get("role")
                add_lifecycle(
                    asset_id,
                    "Maintenance Assigned",
                    f"Assigned to staff {staff_row['name']} (staff_id={staff_id}, department={asset_dept}) by admin",
                )
                return redirect("/admin/assign?success=1")

    success = request.args.get("success")
    return render_template(
        "admin_assign.html",
        staff=staff,
        assets=assets,
        error=error,
        success=success,
    )

@app.route('/admin/asset/assign-dept/<int:asset_id>', methods=['GET','POST'])
def admin_asset_assign_dept(asset_id):
    if session.get('role') != 'admin':
        return redirect('/login')

    conn = get_db()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM assets WHERE asset_id=?', (asset_id,))
    asset = cursor.fetchone()
    if not asset:
        return redirect('/admin/assigns')

    error = None
    if request.method == 'POST':
        dept = request.form.get('department', '').strip()
        problem = request.form.get('problem_description', '').strip()
        if not dept:
            error = 'Select a department'
        elif not problem:
            error = 'Enter a problem description'
        else:
            cursor.execute(
                "INSERT INTO maintenance(asset_id, problem_description, assigned_staff, status, scheduled_time, department) VALUES (?,?,?,?,?,?)",
                (asset_id, problem, None, 'Pending Department', None, dept),
            )
            conn.commit()
            # add lifecycle entry
            g.actor_id = session.get('user_id')
            g.actor_name = session.get('user')
            g.actor_role = session.get('role')
            add_lifecycle(asset_id, 'Maintenance Assigned To Department', f'Assigned to department {dept} by admin')
            return redirect('/admin/assigns')

    return render_template('admin_asset_assign_dept.html', asset=asset, error=error)


@app.route('/admin/asset/remove_all', methods=['GET','POST'])
def admin_remove_all_assets():
    # Only allow Administration admin to remove all assets
    if session.get('role') != 'admin' or session.get('department') != 'Administration':
        return redirect('/login')

    conn = get_db()
    cursor = conn.cursor()

    if request.method == 'POST':
        # delete all asset-related records
        cursor.execute('DELETE FROM maintenance')
        cursor.execute('DELETE FROM inspection')
        cursor.execute('DELETE FROM lifecycle')
        cursor.execute('DELETE FROM approvals')
        cursor.execute('DELETE FROM assets')
        conn.commit()
        return redirect('/admin/assigns')

    # GET: show simple confirmation
    return "<h3>Confirm delete all assets?</h3><form method='post'><button type='submit'>CONFIRM DELETE ALL ASSETS</button></form><p><a href='/admin/assigns'>Cancel</a></p>"


@app.route('/admin/assign-maintenance-dept/<int:maintenance_id>', methods=['GET','POST'])
def admin_assign_maintenance_dept(maintenance_id):
    if session.get('role') != 'admin':
        return redirect('/login')

    conn = get_db()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute('''
        SELECT m.*, a.asset_name
        FROM maintenance m
        LEFT JOIN assets a ON m.asset_id = a.asset_id
        WHERE m.maintenance_id = ?
    ''', (maintenance_id,))
    m = cursor.fetchone()
    if not m:
        return redirect('/admin/assigns')

    error = None
    if request.method == 'POST':
        dept = request.form.get('department','').strip()
        if not dept:
            error = 'Select a department'
        else:
            cursor.execute('UPDATE maintenance SET department=?, status=? WHERE maintenance_id=?', (dept, 'Pending Department', maintenance_id))
            conn.commit()

            g.actor_id = session.get('user_id')
            g.actor_name = session.get('user')
            g.actor_role = session.get('role')
            add_lifecycle(m['asset_id'], 'Maintenance Assigned To Department', f'Assigned maintenance_id={maintenance_id} to department {dept} by admin')

            return redirect('/admin/assigns')

    return render_template('admin_maintenance_assign_dept.html', maintenance=m, error=error)

# ================= ADMIN ASSET HISTORY =================
@app.route("/admin/asset-history", methods=["GET", "POST"])
def admin_asset_history():
    # Allow both admin and staff to view asset history for their department
    if session.get("role") not in ("admin", "staff"):
        return redirect("/login")
    
    conn = get_db()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    user_department = session.get("department", "")
    
    # Get assets for dropdown search - filter by department for non-Administration admins
    if user_department == "Administration":
        cursor.execute("SELECT asset_id, asset_name FROM assets ORDER BY asset_name")
    else:
        cursor.execute("SELECT asset_id, asset_name FROM assets WHERE department=? ORDER BY asset_name", (user_department,))
    
    assets = cursor.fetchall()
    
    selected_asset = None
    maintenance_history = []
    inspection_history = []
    lifecycle_history = []
    next_maint_date = None
    days_until = None
    msg_type = None
    
    # Handle search
    if request.method == "POST" or request.args.get('asset_id'):
        asset_id = request.form.get('asset_id') or request.args.get('asset_id')
        
        if asset_id:
            # Get asset details
            cursor.execute("SELECT * FROM assets WHERE asset_id=?", (asset_id,))
            selected_asset = cursor.fetchone()
            
            # For non-Administration admins, only allow access to their own department's assets
            if selected_asset and user_department != "Administration" and selected_asset['department'] != user_department:
                selected_asset = None
            
            if selected_asset:
                # Get maintenance history with staff names
                cursor.execute("""
                SELECT m.*, u.name as staff_name
                FROM maintenance m
                LEFT JOIN users u ON m.assigned_staff = u.user_id
                WHERE m.asset_id = ?
                ORDER BY m.request_date DESC
                """, (asset_id,))
                maintenance_history = cursor.fetchall()
                
                # Get inspection history
                cursor.execute("""
                SELECT * FROM inspection
                WHERE asset_id = ?
                ORDER BY inspection_date DESC
                """, (asset_id,))
                inspection_history = cursor.fetchall()
                
                # Get lifecycle history
                cursor.execute("""
                SELECT * FROM lifecycle
                WHERE asset_id = ?
                ORDER BY stage_date DESC
                """, (asset_id,))
                lifecycle_history = cursor.fetchall()
                
                # Get predictive maintenance
                next_maint_date, days_until, msg_type = calculate_next_maintenance(cursor, asset_id)
                if next_maint_date:
                    lifecycle_history.insert(0, {
                        'stage': 'Next Maintenance Due',
                        'stage_date': next_maint_date,
                        'notes': 'Predicted next maintenance date based on completed maintenance records',
                        'actor_name': 'System',
                        'actor_role': 'Predictive'
                    })

    return render_template("asset_history.html", 
                         assets=assets, 
                         selected_asset=selected_asset,
                         maintenance_history=maintenance_history,
                         inspection_history=inspection_history,
                         lifecycle_history=lifecycle_history,
                         next_maint_date=next_maint_date,
                         days_until=days_until,
                         msg_type=msg_type)

# ================= ADMIN INSPECTION =================
@app.route("/admin/inspection")
def admin_inspection():
    if session.get("role") != "admin":
        return redirect("/login")

    conn = get_db()
    cursor = conn.cursor()
    user_department = session.get("department", "")
    
    # Filter inspections by department for non-Administration admins
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    if user_department == "Administration":
        cursor.execute("""
        SELECT i.*, a.asset_name
        FROM inspection i
        JOIN assets a ON i.asset_id = a.asset_id
        ORDER BY i.inspection_date DESC
        """)
    else:
        cursor.execute("""
        SELECT i.*, a.asset_name FROM inspection i
        JOIN assets a ON i.asset_id = a.asset_id
        WHERE a.department = ?
        ORDER BY i.inspection_date DESC
        """, (user_department,))
    
    inspections = cursor.fetchall()

    return render_template("admin_inspection.html", inspections=inspections)


# ================= ADMIN MAINTENANCE REQUEST (Assign to Department) =================
@app.route('/admin/request_maintenance', methods=['POST'])
def admin_request_maintenance():
    if session.get('role') != 'admin':
        return redirect('/login')

    asset_id = request.form.get('asset_id')
    problem = request.form.get('problem','').strip()
    scheduled_time = request.form.get('scheduled_time','').strip()

    if not asset_id or not problem:
        return redirect('/admin/assets')

    conn = get_db()
    cursor = conn.cursor()

    # Create maintenance request assigned to department (no staff yet)
    # determine asset's department and store it on the maintenance row
    cursor.execute('SELECT department FROM assets WHERE asset_id=?', (asset_id,))
    row = cursor.fetchone()
    asset_dept = row[0] if row else None

    cursor.execute("INSERT INTO maintenance(asset_id, problem_description, assigned_staff, status, scheduled_time, department) VALUES (?,?,?,?,?,?)",
                   (asset_id, problem, None, 'Pending Department', scheduled_time if scheduled_time else None, asset_dept))
    conn.commit()

    # lifecycle
    maintenance_id = cursor.lastrowid
    g.actor_id = session.get('user_id')
    g.actor_name = session.get('user')
    g.actor_role = session.get('role')
    add_lifecycle(asset_id, 'Maintenance Requested', f'Requested by admin (to department), maintenance_id={maintenance_id}')

    return redirect('/admin/assets')


# ================= DEPARTMENT MAINTENANCE LIST =================
@app.route('/admin/dept-maintenance')
def admin_dept_maintenance():
    if session.get('role') != 'admin':
        return redirect('/login')

    user_department = session.get('department','')
    if user_department == 'Administration':
        return redirect('/admin/inspection')

    conn = get_db()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
    SELECT m.*, a.asset_name, u.name AS staff_name
    FROM maintenance m
    JOIN assets a ON m.asset_id = a.asset_id
    LEFT JOIN users u ON m.assigned_staff = u.user_id
    WHERE m.department = ?
    ORDER BY m.request_date DESC
    """, (user_department,))

    maintenance = cursor.fetchall()

    return render_template('admin_dept_maintenance.html', maintenance=maintenance, user_department=user_department)


# ================= DEPARTMENT ASSIGN TO STAFF (Disabled: admin allocates staff) =================
@app.route('/admin/dept-assign/<int:maintenance_id>', methods=['GET','POST'])
def admin_dept_assign(maintenance_id):
    return redirect('/admin/assign')


# ================= STAFF SUBMIT REPAIR ESTIMATE =================
@app.route('/staff/submit_estimate/<int:maintenance_id>', methods=['GET','POST'])
def staff_submit_estimate(maintenance_id):
    return redirect(f"/staff/update/{maintenance_id}")


# ================= DEPARTMENT INSPECTION REPORTS =================
@app.route("/admin/dept-inspection")
def admin_dept_inspection():
    if session.get("role") != "admin":
        return redirect("/login")

    user_department = session.get("department", "")

    # If central Administration wants the global view, redirect to main inspection page
    if user_department == "Administration":
        return redirect("/admin/inspection")

    conn = get_db()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
    SELECT i.*, a.asset_name
    FROM inspection i
    JOIN assets a ON i.asset_id = a.asset_id
    WHERE a.department = ?
    ORDER BY i.inspection_date DESC
    """, (user_department,))

    inspections = cursor.fetchall()

    return render_template("admin_dept_inspection.html", inspections=inspections, user_department=user_department)


# ================= DEPARTMENT REPORTS =================
@app.route("/admin/dept-reports")
def admin_dept_reports():
    if session.get("role") != "admin":
        return redirect("/login")

    user_department = session.get("department", "")

    # Redirect central Administration to the global reports page
    if user_department == "Administration":
        return redirect("/admin/reports")

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM assets WHERE department=?", (user_department,))
    total_assets = cursor.fetchone()[0]

    cursor.execute("""
    SELECT COUNT(*) FROM maintenance m
    JOIN assets a ON m.asset_id = a.asset_id
    WHERE a.department=?
    """, (user_department,))
    total_maintenance = cursor.fetchone()[0]

    cursor.execute("""
    SELECT COUNT(*) FROM approvals ap
    JOIN assets a ON ap.asset_id = a.asset_id
    WHERE ap.approval_status='Approved' AND a.department=?
    """, (user_department,))
    approved = cursor.fetchone()[0]

    return render_template("admin_dept_reports.html",
                           total_assets=total_assets,
                           total_maintenance=total_maintenance,
                           approved=approved,
                           user_department=user_department)


@app.route('/admin/asset/<int:asset_id>')
def admin_asset_detail(asset_id):
    # Allow admin and staff to view asset details, but scope by department
    if session.get('role') not in ('admin', 'staff'):
        return redirect('/login')

    conn = get_db()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    user_department = session.get("department", "")

    cursor.execute('SELECT * FROM assets WHERE asset_id=?', (asset_id,))
    asset = cursor.fetchone()
    
    # For non-Administration admins, only allow access to their own department's assets
    if asset and user_department != "Administration" and asset['department'] != user_department:
        return redirect('/admin/assets')

    # inspections for this asset
    cursor.execute('SELECT * FROM inspection WHERE asset_id=? ORDER BY inspection_date DESC', (asset_id,))
    inspections = cursor.fetchall()

    # maintenance with staff names joined
    cursor.execute('''
        SELECT m.*, u.name as assigned_staff_name
        FROM maintenance m
        LEFT JOIN users u ON m.assigned_staff = u.user_id
        WHERE m.asset_id=?
        ORDER BY m.request_date DESC
    ''', (asset_id,))
    maintenance = cursor.fetchall()

    # lifecycle entries for asset (history)
    cursor.execute('SELECT stage, stage_date, notes FROM lifecycle WHERE asset_id=? ORDER BY stage_date DESC', (asset_id,))
    lifecycle = cursor.fetchall()

    return render_template('asset_detail.html', asset=asset, inspections=inspections, maintenance=maintenance, lifecycle=lifecycle)


@app.route('/admin/asset/edit/<int:asset_id>', methods=['GET','POST'])
def admin_asset_edit(asset_id):
    if session.get('role') != 'admin':
        return redirect('/login')

    conn = get_db()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    user_department = session.get("department", "")

    cursor.execute('SELECT * FROM assets WHERE asset_id=?', (asset_id,))
    asset = cursor.fetchone()
    if not asset:
        return redirect('/admin/assets')
    
    # For non-Administration admins, only allow access to their own department's assets
    if user_department != "Administration" and asset['department'] != user_department:
        return redirect('/admin/assets')

    if request.method == 'POST':
        error = validate_asset_form(request.form, require_department=True)
        if error:
            return render_template('admin_dept_asset_edit.html', asset=asset, user_department=user_department, error=error)

        # Collect new values
        fields = ['asset_name','external_id','asset_type','department','location','purchase_date','cost','vendor','warranty_period','condition','asset_status','serial_number','incharge','details','remarks']
        updates = {}
        changes = []
        for f in fields:
            new = request.form.get(f,'').strip()
            old = asset[f] if asset[f] is not None else ''
            if str(old) != new:
                updates[f] = new
                changes.append((f, old, new))

        if updates:
            set_clause = ','.join([f"{k}=?" for k in updates.keys()])
            params = list(updates.values()) + [asset_id]
            cursor.execute(f"UPDATE assets SET {set_clause} WHERE asset_id=?", params)
            conn.commit()

            # Record lifecycle entries for each changed field
            g.actor_id = session.get('user_id')
            g.actor_name = session.get('user')
            g.actor_role = session.get('role')
            for f, old, new in changes:
                add_lifecycle(asset_id, f"Field Updated: {f}", f"{f} changed from '{old}' to '{new}'")

        return redirect(f"/admin/asset/{asset_id}")

    return render_template('admin_dept_asset_edit.html', asset=asset, user_department=user_department)


# ================= ADMIN REPORTS =================
@app.route("/admin/reports")
def admin_reports():
    if session.get("role") != "admin":
        return redirect("/login")

    conn = get_db()
    cursor = conn.cursor()
    
    user_department = session.get("department", "")

    if user_department == "Administration":
        cursor.execute("SELECT COUNT(*) FROM assets")
        total_assets = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM maintenance")
        total_maintenance = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM approvals WHERE approval_status='Approved'")
        approved = cursor.fetchone()[0]
    else:
        cursor.execute("SELECT COUNT(*) FROM assets WHERE department=?", (user_department,))
        total_assets = cursor.fetchone()[0]

        cursor.execute("""
        SELECT COUNT(*) FROM maintenance m
        JOIN assets a ON m.asset_id = a.asset_id
        WHERE a.department=?
        """, (user_department,))
        total_maintenance = cursor.fetchone()[0]

        cursor.execute("""
        SELECT COUNT(*) FROM approvals ap
        JOIN assets a ON ap.asset_id = a.asset_id
        WHERE ap.approval_status='Approved' AND a.department=?
        """, (user_department,))
        approved = cursor.fetchone()[0]

    return render_template("admin_reports.html",
                           total_assets=total_assets,
                           total_maintenance=total_maintenance,
                           approved=approved)

@app.route("/staff")
def staff_dashboard():
    if session.get("role") != "staff":
        return redirect("/login")

    conn = get_db()
    cursor = conn.cursor()

    # Count ALL maintenance tasks by status
    cursor.execute("""
        SELECT COUNT(*) FROM maintenance m
        WHERE m.status='Assigned'
    """)
    total = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COUNT(*) FROM maintenance m
        WHERE m.status='repair_submitted'
    """)
    pending = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COUNT(*) FROM maintenance m
        WHERE m.status='Completed'
    """)
    completed = cursor.fetchone()[0]

    return render_template("staff_dashboard.html",
                           total=total,
                           pending=pending,
                           completed=completed)
# ================= STAFF ASSIGNED =================
@app.route("/staff/assigned")
def staff_assigned():
    if session.get("role") != "staff":
        return redirect("/login")
    allowed_depts = ['Administration', 'Finance', 'Marine', 'Civil', 'Mechanical', 'Medical', 'Traffic']
    response = make_response(render_template("staff_assigned.html", departments=allowed_depts))
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


@app.route("/staff/assigned/<dept>")
def staff_assigned_dept(dept):
    if session.get("role") != "staff":
        return redirect("/login")

    allowed_depts = ['Administration', 'Finance', 'Marine', 'Civil', 'Mechanical', 'Medical', 'Traffic']
    if dept not in allowed_depts:
        return redirect("/staff/assigned")

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT 
            m.maintenance_id,
            m.asset_id,
            a.asset_name,
            a.external_id,
            a.asset_type,
            COALESCE(m.department, a.department) AS department,
            a.location,
            a.condition,
            a.asset_status,
            a.serial_number,
            a.photo,
            m.problem_description,
            m.assigned_staff,
            m.status,
            m.scheduled_time,
            u.name AS assigned_staff_name,
            (
                SELECT ap.approval_status
                FROM approvals ap
                WHERE ap.asset_id = m.asset_id
                  AND ap.request_type = 'Maintenance Completion'
                  AND ap.requested_by = m.assigned_staff
                ORDER BY ap.approval_id DESC
                LIMIT 1
            ) AS completion_approval_status
        FROM maintenance m
        JOIN assets a ON m.asset_id = a.asset_id
        LEFT JOIN users u ON m.assigned_staff = u.user_id
        WHERE COALESCE(m.department, a.department) = ?
    """, (dept,))

    maintenance = cursor.fetchall()

    response = make_response(render_template("staff_assigned_dept.html", maintenance=maintenance, department=dept))
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


@app.route("/staff/department/<dept>")
def staff_department(dept):
    if session.get("role") != "staff":
        return redirect("/login")

    allowed_depts = ['Administration', 'Finance', 'Marine', 'Civil', 'Mechanical', 'Medical', 'Traffic']
    if dept not in allowed_depts:
        return redirect("/staff")

    conn = get_db()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Only show MAINTENANCE-ASSIGNED assets, not all assets
    cursor.execute("""
        SELECT DISTINCT
            a.asset_id,
            a.asset_name,
            a.department,
            a.location,
            a.asset_type,
            a.asset_status,
            a.condition,
            a.external_id,
            m.maintenance_id
        FROM maintenance m
        JOIN assets a ON m.asset_id = a.asset_id
        WHERE a.department = ?
        ORDER BY a.asset_name
    """, (dept,))
    assets = cursor.fetchall()

    return render_template("staff_department.html", department=dept, assets=assets)


@app.route("/staff/mark-completed/<int:maintenance_id>", methods=["POST"])
def staff_mark_completed(maintenance_id):
    if session.get("role") != "staff":
        return redirect("/login")

    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    conn = get_db()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT
            m.asset_id,
            m.status,
            m.department,
            a.department as asset_dept,
            (
                SELECT ap.approval_status
                FROM approvals ap
                WHERE ap.asset_id = m.asset_id
                  AND ap.request_type = 'Maintenance Completion'
                  AND ap.requested_by = m.assigned_staff
                ORDER BY ap.approval_id DESC
                LIMIT 1
            ) AS completion_approval_status
        FROM maintenance m
        LEFT JOIN assets a ON m.asset_id = a.asset_id
        WHERE m.maintenance_id=? AND m.assigned_staff=?
        """,
        (maintenance_id, session.get("user_id")),
    )
    row = cursor.fetchone()
    if not row:
        if is_ajax:
            return jsonify({"status": "error", "message": "Maintenance task not found for this staff member."}), 404
        return redirect("/staff/assigned")

    if row["status"] == "Completed":
        if is_ajax:
            return jsonify({"status": "success", "message": "Maintenance task is already completed."}), 200
        return redirect("/staff/assigned")

    # Only approved maintenance can be marked completed by staff
    if row["status"] != "Approved" and row["completion_approval_status"] != "Approved":
        if is_ajax:
            return jsonify({"status": "error", "message": "Only approved maintenance can be completed."}), 403
        return redirect("/staff/assigned")

    cursor.execute(
        "UPDATE maintenance SET status='Completed', completion_date=? WHERE maintenance_id=?",
        (date.today(), maintenance_id),
    )

    conn.commit()
    if is_ajax:
        return jsonify({"status": "success"}), 200
    return redirect("/staff/assigned")
# ================= STAFF INSPECTION =================
@app.route("/staff/inspection", methods=["GET","POST"])
def staff_inspection():
    if session.get("role") != "staff":
        return redirect("/login")

    conn = get_db()
    cursor = conn.cursor()

    error = None
    if request.method == "POST":
        asset_id = request.form.get('asset_id','').strip()
        condition = request.form.get("condition_status", "").strip()
        inspector_name = request.form.get('inspector_name', session.get('user')).strip()
        inspector_designation = request.form.get('inspector_designation', '').strip()
        inspector_organisation = request.form.get('inspector_organisation', '').strip()
        inspection_date = request.form.get('inspection_date', '').strip()

        # validation
        if not asset_id:
            error = 'Select an asset'
        elif not condition:
            error = 'Condition status is required'
        elif not inspector_name:
            error = 'Inspector name is required'
        elif len(inspector_name) < 3 or not is_valid_name(inspector_name):
            error = 'Inspector name must contain only letters and be at least 3 characters long'
        elif inspector_designation and (len(inspector_designation) > 100 or not is_valid_label(inspector_designation)):
            error = 'Inspector designation contains invalid characters'
        elif inspector_organisation and (len(inspector_organisation) > 100 or not is_valid_label(inspector_organisation)):
            error = 'Inspector organisation contains invalid characters'
        elif inspection_date and not is_valid_iso_date(inspection_date):
            error = 'Inspection date must be valid and cannot be in the future'
        elif len(request.form.get("remarks", "").strip()) > 500:
            error = 'Remarks must be 500 characters or fewer'

        if error:
            cursor.execute("""
            SELECT DISTINCT a.asset_id, a.asset_name
            FROM assets a
            WHERE a.asset_status = 'Active'
            ORDER BY a.asset_name
            """)
            assets = cursor.fetchall()
            return render_template('staff_inspection.html', assets=assets, error=error)

        # Classify asset health from condition
        if condition == "Good":
            health = "Healthy"
        elif condition == "Needs Repair":
            health = "Critical"
        else:
            health = "Risk"

        cursor.execute("""
        INSERT INTO inspection(asset_id,inspector_id,inspector_name,inspector_designation,inspector_organisation,inspection_date,condition_status,remarks)
        VALUES(?,?,?,?,?,?,?,?)
        """,(
            asset_id,
            session["user_id"],
            inspector_name,
            inspector_designation,
            inspector_organisation,
            inspection_date if inspection_date else date.today().isoformat(),
            condition,
            request.form.get("remarks", "")
        ))

        # Store condition + derived health and inspector identity in lifecycle notes
        notes = f"Condition: {condition}; Health: {health}; Inspected by {inspector_name}"
        # set actor info
        g.actor_id = session.get('user_id')
        g.actor_name = inspector_name
        g.actor_role = session.get('role')
        add_lifecycle(asset_id, "Inspection Done", notes)
        conn.commit()

    cursor.execute("""
    SELECT DISTINCT a.asset_id, a.asset_name
    FROM assets a
    WHERE a.asset_status = 'Active'
    ORDER BY a.asset_name
    """)
    assets = cursor.fetchall()

    return render_template("staff_inspection.html", assets=assets)

@app.route("/staff/update/<int:id>", methods=["GET", "POST"])
def staff_update(id):
    if session.get('role') != 'staff':
        return redirect('/login')

    conn = get_db()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute('''
        SELECT
            m.*, 
            COALESCE(m.department, a.department) AS task_department
        FROM maintenance m
        JOIN assets a ON m.asset_id = a.asset_id
        WHERE m.maintenance_id=?
    ''', (id,))
    m = cursor.fetchone()
    if not m:
        return redirect('/staff')

    # Staff can submit repair updates for any visible department task.

    if request.method == 'POST':
        repair_details = request.form.get('details', request.form.get('repair_details', '')).strip()
        repair_cost = request.form.get('cost', request.form.get('repair_cost', '')).strip()
        error = validate_maintenance_submission(repair_details, repair_cost)

        if error:
            return render_template('staff_update.html', maintenance=m, error=error)

        cursor.execute(
            "UPDATE maintenance SET repair_details=?, repair_cost=?, status='repair_submitted' WHERE maintenance_id=?",
            (repair_details, repair_cost, id)
        )
        conn.commit()

        cursor.execute(
            'INSERT INTO approvals(asset_id, request_type, requested_by, approval_status) VALUES (?,?,?,?)',
            (m['asset_id'], 'Repair Estimate', session.get('user_id'), 'Pending')
        )
        conn.commit()

        g.actor_id = session.get('user_id')
        g.actor_name = session.get('user')
        g.actor_role = session.get('role')
        add_lifecycle(m['asset_id'], 'Repair Estimate Submitted', f'Submitted by staff {g.actor_name} (maintenance_id={id})')

        return redirect('/staff')

    return render_template('staff_update.html', maintenance=m)

# ================= ADMIN ASSETS APPROVAL =================
@app.route("/admin/assets-approval")
def admin_assets_approval():
    if session.get("role") != "admin" or session.get("department") != "Administration":
        return redirect("/login")

    conn = get_db()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
    SELECT a.approval_id,
           s.asset_name,
           a.request_type,
           u.name AS requested_by,
           a.approval_status
    FROM approvals a
    JOIN assets s ON a.asset_id = s.asset_id
    LEFT JOIN users u ON a.requested_by = u.user_id
    WHERE a.approval_status='Pending'
    """)

    approvals = cursor.fetchall()

    return render_template("admin_assets_approval.html", approvals=approvals)


# ================= ADMIN APPROVAL DECISION =================
@app.route("/admin/approval/<int:id>", methods=["GET", "POST"])
def admin_approval_decision(id):
    if session.get("role") != "admin" or session.get("department") != "Administration":
        return redirect("/login")

    conn = get_db()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    if request.method == "POST":
        status = request.form.get("approval_status")
        remarks = request.form.get("remarks", "")

        if not status:
            return render_template("admin_approval.html", error="Please select an approval status")

        try:
            cursor.execute("""
            UPDATE approvals
            SET approval_status=?, remarks=?, approval_date=?
            WHERE approval_id=?
            """, (status, remarks, date.today(), id))

            conn.commit()

            # Track lifecycle and update related maintenance when approved
            if status == "Approved":
                cursor.execute("SELECT asset_id, request_type, requested_by FROM approvals WHERE approval_id=?", (id,))
                row = cursor.fetchone()
                if row:
                    asset_id = row[0]
                    request_type = row[1]
                    requested_by = row[2]
                    admin_name = session.get('user')
                    g.actor_id = session.get('user_id')
                    g.actor_name = admin_name
                    g.actor_role = session.get('role')
                    add_lifecycle(asset_id, "Maintenance Approved", f"Approved by {admin_name} (admin)")

                    # If this approval was for a repair estimate, mark the most recent maintenance awaiting approval as Approved
                    if request_type == 'Repair Estimate':
                        cursor.execute("SELECT maintenance_id FROM maintenance WHERE asset_id=? AND status IN ('repair_submitted','Approved') ORDER BY request_date DESC LIMIT 1", (asset_id,))
                        m = cursor.fetchone()
                        if m:
                            cursor.execute("UPDATE maintenance SET status='Approved' WHERE maintenance_id=?", (m[0],))

                    # If this approval was for maintenance completion, mark the most recent maintenance as Closed/Approved
                    if request_type == 'Maintenance Completion':
                        cursor.execute("""
                            SELECT maintenance_id
                            FROM maintenance
                            WHERE asset_id=?
                              AND assigned_staff=?
                            ORDER BY maintenance_id DESC
                            LIMIT 1
                        """, (asset_id, requested_by))
                        m = cursor.fetchone()
                        if not m:
                            cursor.execute("SELECT maintenance_id FROM maintenance WHERE asset_id=? ORDER BY maintenance_id DESC LIMIT 1", (asset_id,))
                            m = cursor.fetchone()
                        if m:
                            cursor.execute("UPDATE maintenance SET status='Approved' WHERE maintenance_id=?", (m[0],))

                    # Ensure asset is Active after approval
                    cursor.execute("UPDATE assets SET asset_status='Active' WHERE asset_id=?", (asset_id,))
                    conn.commit()

            return redirect("/admin/assets-approval")
        except Exception as e:
            return render_template("admin_approval.html", error=f"Error processing approval: {str(e)}")

    # FETCH APPROVAL DETAILS FOR DISPLAY
    cursor.execute("""
    SELECT a.approval_id,
           s.asset_name,
           a.request_type,
           a.approval_status,
           m.problem_description,
           u.name AS requested_by
    FROM approvals a
    JOIN assets s ON a.asset_id = s.asset_id
    LEFT JOIN maintenance m ON a.asset_id = m.asset_id
    LEFT JOIN users u ON a.requested_by = u.user_id
    WHERE a.approval_id=?
    """, (id,))

    approval = cursor.fetchone()

    if not approval:
        return render_template("admin_approval.html", approval=None, error="Approval not found")

    return render_template("admin_approval.html", approval=approval)

# ================= ADMIN ASSET LIFECYCLE =================
@app.route("/admin/asset-lifecycle")
def admin_asset_lifecycle():
    if session.get("role") != "admin":
        return redirect("/login")

    conn = get_db()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
    SELECT s.asset_name,
           l.stage,
           l.stage_date,
           l.notes
    FROM lifecycle l
    JOIN assets s ON l.asset_id = s.asset_id
    ORDER BY l.stage_date DESC
    """)

    lifecycle = cursor.fetchall()

    return render_template("admin_asset_lifecycle.html",
                           lifecycle=lifecycle)


# ================= ADMIN DISPOSE ASSET =================
@app.route("/admin/dispose/<int:asset_id>")
def admin_dispose(asset_id):
    if session.get("role") != "admin":
        return redirect("/login")

    conn = get_db()
    cursor = conn.cursor()

    # Update asset status
    cursor.execute("UPDATE assets SET asset_status='Disposed' WHERE asset_id=?", (asset_id,))

    # Add lifecycle entry with admin identity
    admin_name = session.get("user")
    g.actor_id = session.get('user_id')
    g.actor_name = admin_name
    g.actor_role = session.get('role')
    add_lifecycle(asset_id, "Disposed", f"Asset disposed by {admin_name} (admin)", conn)

    conn.commit()

    return redirect("/admin/assets")

# ================= ADMIN DELETE USER =================
@app.route("/admin/delete_user/<int:user_id>")
def delete_user(user_id):
    if session.get("role") != "admin":
        return redirect("/login")

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM users WHERE user_id=?", (user_id,))

    conn.commit()

    return redirect("/admin/users")

# ================= ADMIN DELETE ASSET =================
@app.route("/admin/delete_asset/<int:asset_id>")
def delete_asset(asset_id):
    if session.get("role") != "admin":
        return redirect("/login")

    conn = get_db()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    user_department = session.get("department", "")
    
    # Get the asset to check department
    cursor.execute("SELECT * FROM assets WHERE asset_id=?", (asset_id,))
    asset = cursor.fetchone()
    
    # For non-Administration admins, only allow deletion of their own department's assets
    if asset and user_department != "Administration" and asset['department'] != user_department:
        return redirect("/admin/assets")

    # Delete related records first
    cursor.execute("DELETE FROM maintenance WHERE asset_id= ?", (asset_id,))
    cursor.execute("DELETE FROM approvals WHERE asset_id= ?", (asset_id,))
    cursor.execute("DELETE FROM inspection WHERE asset_id= ?", (asset_id,))
    cursor.execute("DELETE FROM lifecycle WHERE asset_id= ?", (asset_id,))

    # Delete asset
    cursor.execute("DELETE FROM assets WHERE asset_id= ?", (asset_id,))

    conn.commit()

    return redirect("/admin/assets")
# ================= DEPARTMENT DASHBOARD =================
@app.route("/department")
def department_dashboard():
    if session.get("role") != "admin":
        return redirect("/login")

    department = session.get("department")

    # Prevent Administration from using this page
    if department == "Administration":
        return redirect("/admin")

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM assets WHERE department=?", (department,))
    total_assets = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COUNT(*) FROM maintenance m
        JOIN assets a ON m.asset_id = a.asset_id
        WHERE a.department=?
    """, (department,))
    total_maintenance = cursor.fetchone()[0]

    return render_template("dept_dashboard.html",
                           total_assets=total_assets,
                           total_maintenance=total_maintenance)
 # ================= DEPARTMENT ADMIN ASSETS =================
@app.route("/admin/dept-assets", methods=["GET", "POST"])
def admin_dept_assets():

    if session.get("role") != "admin":
        return redirect("/login")

    user_department = session.get("department")

    # 🚫 Block Administration from using this page
    if user_department == "Administration":
        return redirect("/admin/assets")

    conn = get_db()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    error = None
    success = request.args.get("success")

    if request.method == "POST":
        error = validate_asset_form(request.form)

        if not error:

            photo_path = None
            photo = request.files.get("photo")

            if photo and photo.filename:
                filename = secure_filename(photo.filename)
                save_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
                photo.save(save_path)
                photo_path = os.path.join("uploads", filename).replace("\\", "/")

            # 🔐 Force department automatically
            asset_department = user_department

            cursor.execute("""
                INSERT INTO assets(
                    external_id, asset_name, asset_type, department,
                    location, purchase_date, cost, vendor,
                    warranty_period, condition, asset_status,
                    serial_number, photo, incharge,
                    remarks, details, approval_status
                )
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                request.form.get("external_id"),
                request.form.get("asset_name"),
                request.form.get("asset_type"),
                asset_department,
                request.form.get("location"),
                request.form.get("purchase_date"),
                request.form.get("cost"),
                request.form.get("vendor"),
                request.form.get("warranty_period"),
                request.form.get("condition"),
                request.form.get("asset_status"),
                request.form.get("serial_number"),
                photo_path,
                request.form.get("incharge"),
                request.form.get("remarks"),
                request.form.get("details"),
                "Pending"  # 🔐 Always Pending
            ))

            conn.commit()
            return redirect("/admin/dept-assets?success=1")

    # 🔐 Fetch only department assets
    cursor.execute("""
        SELECT * FROM assets
        WHERE department=?
        ORDER BY asset_id DESC
    """, (user_department,))

    assets = cursor.fetchall()

    return render_template(
        "admin_dept_assets.html",
        assets=assets,
        user_department=user_department,
        error=error,
        success=success
    )


# ================= DEPARTMENT ASSET EDIT =================
@app.route('/admin/dept-asset/edit/<int:asset_id>', methods=['GET','POST'])
def admin_dept_asset_edit(asset_id):
    if session.get('role') != 'admin':
        return redirect('/login')

    user_department = session.get('department', '')
    # Department admins only (not central Administration)
    if user_department == 'Administration':
        return redirect('/admin/assets')

    conn = get_db()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM assets WHERE asset_id=?', (asset_id,))
    asset = cursor.fetchone()
    if not asset:
        return redirect('/admin/dept-assets')

    # ensure asset belongs to this department
    if asset['department'] != user_department:
        return redirect('/admin/dept-assets')

    if request.method == 'POST':
        error = validate_asset_form(request.form, require_department=True)
        if error:
            return render_template('admin_asset_edit.html', asset=asset, user_department=user_department, error=error)

        fields = ['asset_name','external_id','asset_type','department','location','purchase_date','cost','vendor','warranty_period','condition','asset_status','serial_number','incharge','details','remarks']
        updates = {}
        changes = []
        for f in fields:
            new = request.form.get(f,'').strip()
            old = asset[f] if asset[f] is not None else ''
            if str(old) != new:
                updates[f] = new
                changes.append((f, old, new))

        if updates:
            # force department to user's department to prevent privilege escalation
            if 'department' in updates:
                updates['department'] = user_department

            set_clause = ','.join([f"{k}=?" for k in updates.keys()])
            params = list(updates.values()) + [asset_id]
            cursor.execute(f"UPDATE assets SET {set_clause} WHERE asset_id=?", params)
            conn.commit()

            # lifecycle entries
            g.actor_id = session.get('user_id')
            g.actor_name = session.get('user')
            g.actor_role = session.get('role')
            for f, old, new in changes:
                add_lifecycle(asset_id, f"Field Updated: {f}", f"{f} changed from '{old}' to '{new}'")

        return redirect('/admin/dept-assets')

    return render_template('admin_asset_edit.html', asset=asset, user_department=user_department)


# ================= DEPARTMENT DELETE ASSET =================
@app.route('/admin/dept-asset/delete/<int:asset_id>')
def admin_dept_delete_asset(asset_id):
    if session.get('role') != 'admin':
        return redirect('/login')

    user_department = session.get('department', '')
    if user_department == 'Administration':
        return redirect('/admin/assets')

    conn = get_db()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM assets WHERE asset_id=?', (asset_id,))
    asset = cursor.fetchone()
    if not asset or asset['department'] != user_department:
        return redirect('/admin/dept-assets')

    # delete related records
    cursor.execute('DELETE FROM maintenance WHERE asset_id=?', (asset_id,))
    cursor.execute('DELETE FROM approvals WHERE asset_id=?', (asset_id,))
    cursor.execute('DELETE FROM inspection WHERE asset_id=?', (asset_id,))
    cursor.execute('DELETE FROM lifecycle WHERE asset_id=?', (asset_id,))
    cursor.execute('DELETE FROM assets WHERE asset_id=?', (asset_id,))
    conn.commit()

    return redirect('/admin/dept-assets')


# ================= DEPARTMENT DISPOSE ASSET =================
@app.route('/admin/dept-asset/dispose/<int:asset_id>')
def admin_dept_dispose(asset_id):
    if session.get('role') != 'admin':
        return redirect('/login')

    user_department = session.get('department', '')
    if user_department == 'Administration':
        return redirect('/admin/assets')

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM assets WHERE asset_id=?', (asset_id,))
    asset = cursor.fetchone()
    if not asset or asset['department'] != user_department:
        return redirect('/admin/dept-assets')

    cursor.execute("UPDATE assets SET asset_status='Disposed' WHERE asset_id=?", (asset_id,))

    # lifecycle entry with actor info
    admin_name = session.get('user')
    g.actor_id = session.get('user_id')
    g.actor_name = admin_name
    g.actor_role = session.get('role')
    add_lifecycle(asset_id, 'Disposed', f"Asset disposed by {admin_name} (dept admin)", conn)

    conn.commit()

    return redirect('/admin/dept-assets')
# ================= DEPARTMENT ASSET HISTORY =================
@app.route("/admin/dept-asset-history", methods=["GET", "POST"])
def admin_dept_asset_history():

    if session.get("role") != "admin":
        return redirect("/login")

    user_department = session.get("department")

    # 🚫 Block Administration from this page
    if user_department == "Administration":
        return redirect("/admin/asset-history")

    conn = get_db()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Dropdown assets (only department assets)
    cursor.execute("""
        SELECT asset_id, asset_name
        FROM assets
        WHERE department=?
        ORDER BY asset_name
    """, (user_department,))
    assets = cursor.fetchall()

    selected_asset = None
    maintenance_history = []
    inspection_history = []
    lifecycle_history = []
    next_maint_date = None
    days_until = None
    msg_type = None

    if request.method == "POST" or request.args.get("asset_id"):

        asset_id = request.form.get("asset_id") or request.args.get("asset_id")

        if asset_id:

            # Fetch only if belongs to department
            cursor.execute("""
                SELECT * FROM assets
                WHERE asset_id=? AND department=?
            """, (asset_id, user_department))

            selected_asset = cursor.fetchone()

            if selected_asset:

                # Maintenance
                cursor.execute("""
                    SELECT m.*, u.name AS staff_name
                    FROM maintenance m
                    LEFT JOIN users u ON m.assigned_staff = u.user_id
                    WHERE m.asset_id=?
                    ORDER BY m.request_date DESC
                """, (asset_id,))
                maintenance_history = cursor.fetchall()

                # Inspection
                cursor.execute("""
                    SELECT *
                    FROM inspection
                    WHERE asset_id=?
                    ORDER BY inspection_date DESC
                """, (asset_id,))
                inspection_history = cursor.fetchall()

                # Lifecycle
                cursor.execute("""
                    SELECT *
                    FROM lifecycle
                    WHERE asset_id=?
                    ORDER BY stage_date DESC
                """, (asset_id,))
                lifecycle_history = cursor.fetchall()
                
                # Get predictive maintenance
                next_maint_date, days_until, msg_type = calculate_next_maintenance(cursor, asset_id)
                if next_maint_date:
                    lifecycle_history.insert(0, {
                        'stage': 'Next Maintenance Due',
                        'stage_date': next_maint_date,
                        'notes': 'Predicted next maintenance date based on completed maintenance records',
                        'actor_name': 'System',
                        'actor_role': 'Predictive'
                    })

    return render_template(
        "admin_dept_asset_history.html",
        assets=assets,
        selected_asset=selected_asset,
        maintenance_history=maintenance_history,
        inspection_history=inspection_history,
        lifecycle_history=lifecycle_history,
        next_maint_date=next_maint_date,
        days_until=days_until,
        msg_type=msg_type,
        user_department=user_department
    )

# ================= LOGOUT =================
@app.route("/switch-role")
def switch_role():
    if not session.get("user_id"):
        return redirect("/login")

    account_role = (session.get("account_role") or "").lower()

    # Backward compatibility: populate account_role for older sessions.
    if not account_role:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT role FROM users WHERE user_id=?", (session.get("user_id"),))
        row = cursor.fetchone()
        account_role = (row[0] if row and row[0] else "").lower()
        if account_role:
            session["account_role"] = account_role

    if account_role != "admin":
        return redirect("/staff" if session.get("role") == "staff" else "/login")

    requested = request.args.get("to", "").strip().lower()
    if requested in ("admin", "staff"):
        target_role = requested
    else:
        target_role = "staff" if session.get("role") == "admin" else "admin"

    session["role"] = target_role
    return redirect("/admin" if target_role == "admin" else "/staff")


@app.route("/help/admin")
def help_admin():
    if session.get("role") != "admin":
        return redirect("/login")
    return render_template("help_admin.html")


@app.route("/help/staff")
def help_staff():
    if session.get("role") != "staff":
        return redirect("/login")
    return render_template("help_staff.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


if __name__ == "__main__":
    app.run(debug=True)
