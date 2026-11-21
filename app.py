import os
import sqlite3
from functools import wraps
from flask import (
    Flask,
    render_template,
    render_template_string,
    request,
    redirect,
    url_for,
    session,
    flash,
)
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "uobo-baghdad-secret-key-2026")

DB_PATH = "uobo.db"

LOGIN_FALLBACK_HTML = """<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>تسجيل الدخول - UOBO</title>
  <style>
    body {
      font-family: Tahoma, Arial, sans-serif;
      background: #111318;
      color: #f3f4f6;
      display: flex;
      justify-content: center;
      align-items: center;
      min-height: 100vh;
      margin: 0;
      padding: 16px;
    }
    .card {
      background: #1b1f27;
      border: 1px solid #2d3340;
      border-radius: 12px;
      padding: 24px;
      width: 100%;
      max-width: 380px;
    }
    h2 { margin-top: 0; text-align: center; color: #f5b942; }
    label { display: block; margin: 12px 0 6px; font-size: 14px; }
    input {
      width: 100%;
      box-sizing: border-box;
      padding: 10px 12px;
      border-radius: 8px;
      border: 1px solid #3a4152;
      background: #111318;
      color: #fff;
      font-size: 15px;
    }
    button {
      width: 100%;
      margin-top: 18px;
      padding: 11px;
      border: none;
      border-radius: 8px;
      background: #d99b26;
      color: #111318;
      font-weight: bold;
      font-size: 15px;
      cursor: pointer;
    }
    .msg {
      background: #3b1d24;
      color: #ff9aa9;
      padding: 10px;
      border-radius: 8px;
      margin-bottom: 12px;
      font-size: 13px;
    }
  </style>
</head>
<body>
  <div class="card">
    <h2>تسجيل الدخول</h2>
    {% with messages = get_flashed_messages() %}
      {% if messages %}
        {% for msg in messages %}
          <div class="msg">{{ msg }}</div>
        {% endfor %}
      {% endif %}
    {% endwith %}
    <form method="POST">
      <label for="username">اسم الحساب</label>
      <input id="username" name="username" type="text" required placeholder="مثال: coordinator أو dr1">

      <label for="password">الرمز</label>
      <input id="password" name="password" type="password" required placeholder="أدخل الرمز">

      <button type="submit">دخول</button>
    </form>
  </div>
</body>
</html>"""

DASHBOARD_FALLBACK_HTML = """<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>لوحة النظام - UOBO</title>
  <style>
    body {
      font-family: Tahoma, Arial, sans-serif;
      background: #111318;
      color: #f3f4f6;
      margin: 0;
      padding: 20px;
    }
    .box {
      max-width: 600px;
      margin: 30px auto;
      background: #1b1f27;
      border: 1px solid #2d3340;
      border-radius: 12px;
      padding: 24px;
    }
    h2 { margin-top: 0; color: #f5b942; }
    .logout {
      display: inline-block;
      margin-top: 16px;
      padding: 9px 16px;
      border-radius: 8px;
      background: #d99b26;
      color: #111318;
      text-decoration: none;
      font-weight: bold;
    }
  </style>
</head>
<body>
  <div class="box">
    <h2>أهلاً بك، {{ full_name }}</h2>
    <p>اسم الحساب: <strong>{{ username }}</strong></p>
    <p>الصفة: <strong>{{ "مقرر القسم" if role == "coordinator" else "دكتور" }}</strong></p>
    <a class="logout" href="{{ url_for('logout') }}">تسجيل الخروج</a>
  </div>
</body>
</html>"""


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_users():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            full_name TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('coordinator', 'doctor')),
            is_active INTEGER NOT NULL DEFAULT 1
        )
    """)

    # الحسابات الأربعة فقط: مقرر القسم + 3 دكاترة
    accounts = [
        ("coordinator", "مقرر القسم", "Coord@1234", "coordinator"),
        ("dr1", "الدكتور الأول", "Dr1@1234", "doctor"),
        ("dr2", "الدكتور الثاني", "Dr2@1234", "doctor"),
        ("dr3", "الدكتور الثالث", "Dr3@1234", "doctor"),
    ]

    for username, full_name, raw_pass, role in accounts:
        exists = conn.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()
        if not exists:
            conn.execute(
                "INSERT INTO users (username, full_name, password_hash, role, is_active) VALUES (?, ?, ?, ?, 1)",
                (username, full_name, generate_password_hash(raw_pass), role),
            )

    conn.commit()
    conn.close()


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            flash("يرجى إدخال الاسم والرمز لتسجيل الدخول.", "warning")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


def safe_render(template_name, fallback_html, **context):
    template_path = os.path.join(app.root_path, app.template_folder or "templates", template_name)
    if os.path.exists(template_path):
        return render_template(template_name, **context)
    return render_template_string(fallback_html, **context)


@app.route("/")
@login_required
def index():
    return safe_render(
        "dashboard.html",
        DASHBOARD_FALLBACK_HTML,
        full_name=session.get("full_name"),
        username=session.get("username"),
        role=session.get("role"),
    )


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip().lower()
        password = request.form.get("password", "")

        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        conn.close()

        if user and user["is_active"] == 1 and check_password_hash(user["password_hash"], password):
            session.clear()
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session["full_name"] = user["full_name"]
            session["role"] = user["role"]
            return redirect(url_for("index"))

        flash("الاسم أو الرمز غير صحيح.", "danger")

    return safe_render("login.html", LOGIN_FALLBACK_HTML)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


init_users()

if __name__ == "__main__":
    app.run(debug=False)
