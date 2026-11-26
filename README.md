from flask import Flask, render_template_string, request, redirect, url_for, session, send_file, jsonify, Response
from urllib.parse import urlencode
from datetime import datetime, timedelta, timezone
import os
import base64
import sqlite3
import io
import csv
import re
import time
import secrets
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024
app.secret_key = os.environ.get('SECRET_KEY') or secrets.token_hex(32)
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    SESSION_COOKIE_SECURE=os.environ.get('COOKIE_SECURE') == '1',
)

HEAD_OFFICIAL_EMAIL = "head.dept@cofarts.uobaghdad.edu.iq"
DB_NAME = os.environ.get('DB_PATH', 'cofarts_system.db')
HEAD_PASSWORD = os.environ.get('HEAD_PASSWORD')
REGISTER_CODE = os.environ.get('REGISTER_CODE')

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            doctor TEXT,
            dept TEXT,
            shift TEXT,
            stage TEXT,
            section TEXT,
            subject TEXT,
            timestamp TEXT,
            present_count INTEGER,
            absent_count INTEGER,
            details TEXT
        )
    ''')
    cols = [r[1] for r in cursor.execute('PRAGMA table_info(reports)')]
    if 'lecture_date' not in cols:
        cursor.execute('ALTER TABLE reports ADD COLUMN lecture_date TEXT')
    cursor.execute('CREATE UNIQUE INDEX IF NOT EXISTS ux_report ON reports (dept, shift, stage, section, subject, lecture_date)')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dept TEXT NOT NULL, shift TEXT NOT NULL, stage TEXT NOT NULL, section TEXT NOT NULL, name TEXT NOT NULL,
            UNIQUE (dept, shift, stage, section, name)
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            email TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL
        )
    ''')
    if HEAD_PASSWORD:
        cursor.execute(
            'INSERT OR REPLACE INTO users (email, name, password_hash, role) VALUES (?, ?, ?, ?)',
            (HEAD_OFFICIAL_EMAIL.lower(), '\u0645\u0642\u0631\u0631 \u0627\u0644\u0642\u0633\u0645', generate_password_hash(HEAD_PASSWORD), 'head'))
    else:
        print('WARNING: HEAD_PASSWORD is not set; the department head cannot log in.')
    conn.commit()
    conn.close()

init_db()

COLLEGE_DEPARTMENTS = [
    {"name": "\u0642\u0633\u0645 \u0627\u0644\u062a\u0631\u0628\u064a\u0629 \u0627\u0644\u0641\u0646\u064a\u0629", "icon": "\U0001f3a8", "desc": "\u0645\u0646\u0627\u0631\u0629 \u0627\u0644\u0641\u0646 \u0627\u0644\u062a\u0639\u0628\u064a\u0631\u064a \u0648\u062c\u0645\u0627\u0644\u064a\u0627\u062a \u0627\u0644\u062a\u0631\u0628\u064a\u0629 \u0627\u0644\u062d\u064a\u0629"},
    {"name": "\u0642\u0633\u0645 \u0627\u0644\u0641\u0646\u0648\u0646 \u0627\u0644\u0645\u0648\u0633\u064a\u0642\u064a\u0629", "icon": "\U0001f3b5", "desc": "\u0623\u0635\u0627\u0644\u0629 \u0627\u0644\u0646\u063a\u0645\u060c \u0627\u0644\u0625\u064a\u0642\u0627\u0639\u060c \u0648\u0627\u0644\u062a\u0630\u0648\u0642 \u0627\u0644\u0635\u0648\u062a\u064a \u0627\u0644\u0631\u0641\u064a\u0639"},
    {"name": "\u0642\u0633\u0645 \u0627\u0644\u062e\u0637 \u0627\u0644\u0639\u0631\u0628\u064a \u0648\u0627\u0644\u0632\u062e\u0631\u0641\u0629", "icon": "\u2712\ufe0f", "desc": "\u0647\u0646\u062f\u0633\u0629 \u0627\u0644\u062d\u0631\u0641 \u0627\u0644\u0639\u0631\u0628\u064a \u0648\u0625\u0634\u0631\u0627\u0642\u0627\u062a \u0627\u0644\u0632\u062e\u0631\u0641\u0629 \u0627\u0644\u0625\u0633\u0644\u0627\u0645\u064a\u0629"},
    {"name": "\u0642\u0633\u0645 \u0627\u0644\u0641\u0646\u0648\u0646 \u0627\u0644\u062a\u0634\u0643\u064a\u0644\u064a\u0629", "icon": "\U0001f5bc\ufe0f", "desc": "\u0639\u0631\u0627\u0642\u0629 \u0627\u0644\u0631\u0633\u0645\u060c \u0627\u0644\u0646\u062d\u062a\u060c \u0648\u0627\u0644\u062a\u0634\u0643\u064a\u0644 \u0627\u0644\u062c\u062f\u0627\u0631\u064a \u0627\u0644\u0645\u0639\u0627\u0635\u0631"},
    {"name": "\u0642\u0633\u0645 \u0627\u0644\u0641\u0646\u0648\u0646 \u0627\u0644\u0645\u0633\u0631\u062d\u064a\u0629", "icon": "\U0001f3ad", "desc": "\u062e\u0634\u0628\u0629 \u0627\u0644\u0625\u0628\u062f\u0627\u0639\u060c \u0627\u0644\u062a\u0645\u062b\u064a\u0644\u060c \u0648\u0627\u0644\u0625\u062e\u0631\u0627\u062c \u0627\u0644\u0645\u0633\u0631\u062d\u064a \u0627\u0644\u0631\u0642\u0645\u064a"},
    {"name": "\u0642\u0633\u0645 \u0627\u0644\u0641\u0646\u0648\u0646 \u0627\u0644\u0633\u064a\u0646\u0645\u0627\u0626\u064a\u0629 \u0648\u0627\u0644\u062a\u0644\u0641\u0632\u064a\u0648\u0646\u064a\u0629", "icon": "\U0001f3ac", "desc": "\u0627\u0644\u0633\u064a\u0646\u0645\u0627 \u0627\u0644\u062a\u0641\u0627\u0639\u0644\u064a\u0629\u060c \u0627\u0644\u0625\u062e\u0631\u0627\u062c \u0627\u0644\u062a\u0644\u0641\u0632\u064a\u0648\u0646\u064a \u0648\u0627\u0644\u0648\u0633\u0627\u0626\u0637"},
    {"name": "\u0642\u0633\u0645 \u0627\u0644\u062a\u0635\u0645\u064a\u0645", "icon": "\u270f\ufe0f", "desc": "\u0647\u0646\u062f\u0633\u0629 \u0627\u0644\u0641\u0636\u0627\u0621 \u0627\u0644\u0628\u0635\u0631\u064a\u060c \u0627\u0644\u062a\u0635\u0645\u064a\u0645 \u0627\u0644\u062f\u0627\u062e\u0644\u064a \u0648\u0627\u0644\u0635\u0646\u0627\u0639\u064a"}
]

STAGE_ORDER = ['\u0627\u0644\u0645\u0631\u062d\u0644\u0629 \u0627\u0644\u0623\u0648\u0644\u0649', '\u0627\u0644\u0645\u0631\u062d\u0644\u0629 \u0627\u0644\u062b\u0627\u0646\u064a\u0629', '\u0627\u0644\u0645\u0631\u062d\u0644\u0629 \u0627\u0644\u062b\u0627\u0644\u062b\u0629', '\u0627\u0644\u0645\u0631\u062d\u0644\u0629 \u0627\u0644\u0631\u0627\u0628\u0639\u0629']
SHIFTS = ('\u0635\u0628\u0627\u062d\u064a', '\u0645\u0633\u0627\u0626\u064a')
FULL_COLLEGE_DATA = {}

def _ar_key(s):
    return s.translate(str.maketrans('\u0623\u0625\u0622\u0649\u0629', '\u0627\u0627\u0627\u064a\u0647'))

def _sort_tree(tree):
    out = {}
    for dept, shifts in tree.items():
        out[dept] = {}
        for shift in sorted(shifts, key=lambda x: (SHIFTS.index(x) if x in SHIFTS else 9, x)):
            stages = shifts[shift]
            out[dept][shift] = {}
            for stage in sorted(stages, key=lambda x: STAGE_ORDER.index(x) if x in STAGE_ORDER else 99):
                out[dept][shift][stage] = {sec: sorted(stages[stage][sec], key=_ar_key)
                                           for sec in sorted(stages[stage], key=_ar_key)}
    return out

def load_students():
    conn = sqlite3.connect(DB_NAME)
    rows = conn.execute('SELECT dept, shift, stage, section, name FROM students').fetchall()
    conn.close()
    tree = {}
    for dept, shift, stage, section, name in rows:
        tree.setdefault(dept, {}).setdefault(shift, {}).setdefault(stage, {}).setdefault(section, []).append(name)
    FULL_COLLEGE_DATA.clear()
    FULL_COLLEGE_DATA.update(_sort_tree(tree))

def students_rows(tree=None):
    tree = FULL_COLLEGE_DATA if tree is None else tree
    order = [d['name'] for d in COLLEGE_DEPARTMENTS]
    for dept in sorted(tree, key=lambda x: order.index(x) if x in order else 99):
        for shift, stages in tree[dept].items():
            for stage, sections in stages.items():
                for sec, names in sections.items():
                    for n in names:
                        yield (dept, shift, stage, sec, n)

def build_students_xlsx(rows):
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment
    wb = Workbook()
    ws = wb.active
    ws.title = '\u0627\u0644\u0637\u0644\u0628\u0629'
    ws.sheet_view.rightToLeft = True
    ws.append(['\u0627\u0644\u0642\u0633\u0645', '\u0627\u0644\u062f\u0631\u0627\u0633\u0629', '\u0627\u0644\u0645\u0631\u062d\u0644\u0629', '\u0627\u0644\u0634\u0639\u0628\u0629', '\u0627\u0644\u0627\u0633\u0645'])
    for c in ws[1]:
        c.font = Font(name='Arial', bold=True, color='FFFFFF')
        c.fill = PatternFill('solid', fgColor='B45309')
        c.alignment = Alignment(horizontal='center')
    for r in rows:
        ws.append(list(r))
    for col, w in zip('ABCDE', (32, 12, 18, 14, 42)):
        ws.column_dimensions[col].width = w
    for row in ws.iter_rows(min_row=2):
        for c in row:
            c.font = Font(name='Arial')
    ws.freeze_panes = 'A2'
    ws.auto_filter.ref = ws.dimensions
    info = wb.create_sheet('\u062a\u0639\u0644\u064a\u0645\u0627\u062a')
    info.sheet_view.rightToLeft = True
    for line in ['\u0643\u0644 \u0635\u0641 \u0641\u064a \u0648\u0631\u0642\u0629 "\u0627\u0644\u0637\u0644\u0628\u0629" \u064a\u0645\u062b\u0644 \u0637\u0627\u0644\u0628\u0627\u064b \u0648\u0627\u062d\u062f\u0627\u064b.',
                 '\u0627\u0644\u0623\u0639\u0645\u062f\u0629 \u0627\u0644\u062e\u0645\u0633\u0629 \u0645\u0637\u0644\u0648\u0628\u0629 \u0648\u0628\u0647\u0630\u0627 \u0627\u0644\u062a\u0631\u062a\u064a\u0628: \u0627\u0644\u0642\u0633\u0645\u060c \u0627\u0644\u062f\u0631\u0627\u0633\u0629\u060c \u0627\u0644\u0645\u0631\u062d\u0644\u0629\u060c \u0627\u0644\u0634\u0639\u0628\u0629\u060c \u0627\u0644\u0627\u0633\u0645.',
                 '\u0627\u0644\u0642\u0633\u0645 \u064a\u062c\u0628 \u0623\u0646 \u064a\u0637\u0627\u0628\u0642 \u0627\u0633\u0645\u0647 \u0641\u064a \u0627\u0644\u0645\u0646\u0638\u0648\u0645\u0629 \u062a\u0645\u0627\u0645\u0627\u064b. \u0627\u0644\u062f\u0631\u0627\u0633\u0629: \u0635\u0628\u0627\u062d\u064a \u0623\u0648 \u0645\u0633\u0627\u0626\u064a.',
                 '\u0627\u0644\u0645\u0631\u062d\u0644\u0629 \u0645\u062b\u0644: \u0627\u0644\u0645\u0631\u062d\u0644\u0629 \u0627\u0644\u0623\u0648\u0644\u0649. \u0627\u0644\u0634\u0639\u0628\u0629 \u0645\u062b\u0644: \u0627\u0644\u0634\u0639\u0628\u0629 (\u0623).',
                 '\u0627\u0631\u0641\u0639 \u0627\u0644\u0645\u0644\u0641 \u0645\u0646 \u0644\u0648\u062d\u0629 \u0627\u0644\u0645\u0642\u0631\u0631 > \u0625\u062f\u0627\u0631\u0629 \u0627\u0644\u0637\u0644\u0628\u0629. \u0627\u0644\u0635\u0641 \u0627\u0644\u0623\u0648\u0644 (\u0627\u0644\u0639\u0646\u0627\u0648\u064a\u0646) \u064a\u064f\u062a\u062c\u0627\u0647\u0644.']:
        info.append([line])
    info.column_dimensions['A'].width = 90
    bio = io.BytesIO()
    wb.save(bio)
    bio.seek(0)
    return bio

def import_students_xlsx(fileobj, replace=False):
    from openpyxl import load_workbook
    valid = {d['name'] for d in COLLEGE_DEPARTMENTS}
    wb = load_workbook(fileobj, read_only=True, data_only=True)
    ws = wb['\u0627\u0644\u0637\u0644\u0628\u0629'] if '\u0627\u0644\u0637\u0644\u0628\u0629' in wb.sheetnames else wb.worksheets[0]
    data, skipped = [], 0
    for i, row in enumerate(ws.iter_rows(values_only=True)):
        if i == 0:
            continue
        vals = tuple(' '.join(str(v).split()) if v is not None else '' for v in (list(row) + [None] * 5)[:5])
        if not any(vals):
            continue
        if all(vals) and vals[0] in valid and vals[1] in SHIFTS:
            data.append(vals)
        else:
            skipped += 1
    conn = sqlite3.connect(DB_NAME)
    added = 0
    try:
        if replace and data:
            conn.execute('DELETE FROM students')
        for v in data:
            added += conn.execute('INSERT OR IGNORE INTO students (dept, shift, stage, section, name) VALUES (?, ?, ?, ?, ?)', v).rowcount
        conn.commit()
    finally:
        conn.close()
    load_students()
    return added, skipped

def seed_students():
    conn = sqlite3.connect(DB_NAME)
    n = conn.execute('SELECT COUNT(*) FROM students').fetchone()[0]
    conn.close()
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'students.xlsx')
    if n == 0 and os.path.exists(path):
        with open(path, 'rb') as f:
            import_students_xlsx(f)

seed_students()
load_students()

@app.before_request
def csrf_protect():
    if request.method == 'POST':
        token = session.get('_csrf')
        if not token or token != request.form.get('_csrf'):
            return "\u0637\u0644\u0628 \u063a\u064a\u0631 \u0635\u0627\u0644\u062d\u060c \u0623\u0639\u062f \u062a\u062d\u0645\u064a\u0644 \u0627\u0644\u0635\u0641\u062d\u0629 \u0648\u062d\u0627\u0648\u0644 \u0645\u062c\u062f\u062f\u0627\u064b", 400

@app.context_processor
def inject_csrf():
    if '_csrf' not in session:
        session['_csrf'] = secrets.token_hex(16)
    return {'csrf_token': session['_csrf']}

def baghdad_now():
    return datetime.now(timezone(timedelta(hours=3)))

def get_logo_base64():
    for path in [os.path.expanduser('~/logo.png'), 'logo.png', os.path.join(app.root_path, 'static', 'icon-192.png')]:
        if os.path.exists(path):
            with open(path, 'rb') as img_file:
                return "data:image/png;base64," + base64.b64encode(img_file.read()).decode('utf-8')
    return ""

BASE_CSS_AND_HEAD = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
    <meta name="theme-color" content="#050a18">
    <link rel="manifest" href="/manifest.json">
    <link rel="icon" type="image/png" sizes="32x32" href="/static/favicon-32.png">
    <link rel="apple-touch-icon" href="/static/apple-touch-icon.png">
    <meta name="apple-mobile-web-app-title" content="UOB">
    <title>\u062c\u0627\u0645\u0639\u0629 \u0628\u063a\u062f\u0627\u062f - \u0643\u0644\u064a\u0629 \u0627\u0644\u0641\u0646\u0648\u0646 \u0627\u0644\u062c\u0645\u064a\u0644\u0629</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;800;900&display=swap');
        
        :root {
            --bg-deep: #000207;
            --glass-bg: rgba(5, 10, 24, 0.96);
            --glass-border: rgba(245, 158, 11, 0.65);
            --accent-gold: #f59e0b;
            --accent-gold-glow: rgba(245, 158, 11, 0.85);
            --accent-green: #10b981;
            --accent-blue: #3b82f6;
            --text-light: #f8fafc;
            --text-muted: #94a3b8;
        }

        * { box-sizing: border-box; }

        body {
            font-family: 'Cairo', sans-serif;
            background-color: var(--bg-deep);
            color: var(--text-light);
            margin: 0;
            padding: 15px;
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            overflow-x: hidden;
        }

        #particles-canvas {
            position: fixed;
            top: 0; left: 0; width: 100%; height: 100%;
            z-index: 0; pointer-events: none;
        }

        .main-container {
            position: relative;
            z-index: 2;
            width: 100%;
            max-width: 1200px;
            background: var(--glass-bg);
            border-radius: 32px;
            padding: 30px;
            box-shadow: 0 40px 100px rgba(0,0,0,0.95), 0 0 60px rgba(245, 158, 11, 0.35);
            border: 2px solid var(--glass-border);
            backdrop-filter: blur(25px);
        }

        .brand-header {
            text-align: center;
            border-bottom: 2px solid rgba(245, 158, 11, 0.4);
            padding-bottom: 20px;
            margin-bottom: 25px;
        }

        .logo-img {
            width: 110px; height: 110px;
            object-fit: contain; margin-bottom: 10px;
            border-radius: 50%; border: 3px solid var(--accent-gold);
            background: #000207; padding: 6px;
            box-shadow: 0 0 45px var(--accent-gold-glow);
        }

        .brand-header h1 {
            margin: 0; font-size: 2.3rem; font-weight: 900;
            background: linear-gradient(135deg, #fbbf24 0%, #f59e0b 50%, #d97706 100%);
            -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        }

        .brand-header h2 {
            margin: 5px 0 0 0; font-size: 1.4rem; font-weight: 700;
            color: var(--accent-green);
        }

        .nav-bar {
            display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px;
            background: rgba(14, 24, 46, 0.94); padding: 15px 25px;
            border-radius: 20px; margin-bottom: 25px;
            border: 1px solid rgba(255, 255, 255, 0.15);
        }

        .logout-link {
            color: #ef4444; text-decoration: none; font-weight: 800;
            padding: 8px 18px; border: 1.5px solid #ef4444; border-radius: 12px;
        }

        .dept-grid {
            display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
            gap: 18px; margin-bottom: 25px;
        }

        .dept-card {
            background: rgba(14, 24, 46, 0.9); border: 1.5px solid rgba(255, 255, 255, 0.15);
            padding: 22px; border-radius: 22px; cursor: pointer; text-decoration: none; color: inherit;
            display: block; transition: all 0.3s;
        }

        .dept-card:hover {
            border-color: var(--accent-gold); transform: translateY(-5px);
            box-shadow: 0 15px 35px rgba(245, 158, 11, 0.4);
        }

        .btn-action {
            background: linear-gradient(135deg, var(--accent-gold), #b45309);
            color: #fff; font-weight: 900; padding: 16px 28px;
            border: none; border-radius: 16px; cursor: pointer;
            width: 100%; font-size: 1.2rem; font-family: 'Cairo', sans-serif;
            box-shadow: 0 10px 30px rgba(245, 158, 11, 0.5);
        }

        .input-field {
            width: 100%; padding: 14px 18px; border-radius: 14px;
            border: 1.5px solid rgba(255, 255, 255, 0.2);
            background: rgba(6, 11, 25, 0.95); color: #fff;
            font-size: 1.05rem; font-family: 'Cairo', sans-serif; margin-bottom: 18px;
        }

        .portal-switcher {
            display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin-bottom: 25px;
        }

        .role-card-select {
            background: rgba(10, 18, 38, 0.75); border: 2px solid rgba(255, 255, 255, 0.12);
            padding: 18px; border-radius: 18px; cursor: pointer; text-align: center;
        }

        .role-card-select.active-doctor { border-color: var(--accent-gold); background: rgba(245, 158, 11, 0.2); }
        .role-card-select.active-head { border-color: var(--accent-green); background: rgba(16, 185, 129, 0.2); }

        table { width: 100%; border-collapse: collapse; margin-top: 15px; background: rgba(6, 11, 25, 0.95); border-radius: 14px; overflow: hidden; }
        th, td { border-bottom: 1px solid rgba(255, 255, 255, 0.1); padding: 12px; text-align: right; font-size: 0.95rem; }
        th { background: rgba(14, 24, 46, 0.99); color: var(--accent-gold); }

        .pill-btn {
            display: inline-block; padding: 10px 22px; margin: 6px;
            border-radius: 30px; border: 1.5px solid var(--accent-blue);
            color: var(--accent-blue); text-decoration: none; font-weight: 700;
        }
        .pill-btn:hover, .pill-btn.active { background: var(--accent-blue); color: #fff; }
        
        .status-bar {
            display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px;
            background: rgba(14, 24, 46, 0.94); border: 1px solid rgba(255, 255, 255, 0.15);
            border-radius: 16px; padding: 10px 18px; margin-bottom: 20px;
            font-weight: 700; font-size: 0.95rem;
        }
        .sb-item { white-space: nowrap; }
        .sb-dot { display: inline-block; width: 11px; height: 11px; border-radius: 50%; background: #94a3b8; margin-left: 6px; }
        #sb-time { color: var(--accent-gold); direction: ltr; display: inline-block; font-variant-numeric: tabular-nums; }

        body {
            background: radial-gradient(1200px 600px at 85% -10%, rgba(245,158,11,0.18), transparent 60%),
                        radial-gradient(900px 500px at -10% 110%, rgba(16,185,129,0.14), transparent 60%), #000207;
        }
        .main-container {
            animation: rise .7s cubic-bezier(.2,.8,.2,1) both;
            background: linear-gradient(160deg, rgba(10,18,38,0.97), rgba(3,7,18,0.98));
            border: 1px solid rgba(245,158,11,0.55);
            box-shadow: 0 40px 100px rgba(0,0,0,.95), 0 0 80px rgba(245,158,11,.22), inset 0 1px 0 rgba(255,255,255,.08);
        }
        @keyframes rise { from { opacity: 0; transform: translateY(18px); } to { opacity: 1; transform: none; } }
        .brand-header h1 { background-size: 200% auto; animation: shine 6s linear infinite; }
        @keyframes shine { to { background-position: 200% center; } }
        .brand-header::after { content: ''; display: block; width: 140px; height: 3px; margin: 16px auto 0; border-radius: 3px; background: linear-gradient(90deg, transparent, #f59e0b, transparent); }
        .btn-action { transition: transform .2s, box-shadow .2s, filter .2s; }
        .btn-action:hover { transform: translateY(-2px); filter: brightness(1.12); box-shadow: 0 14px 38px rgba(245,158,11,.65); }
        .input-field:focus, select:focus { outline: none; border-color: var(--accent-gold); box-shadow: 0 0 0 3px rgba(245,158,11,.25); }
        .dept-card { position: relative; overflow: hidden; }
        .dept-card::before { content: ''; position: absolute; inset: 0 0 auto 0; height: 3px; background: linear-gradient(90deg, transparent, var(--accent-gold), transparent); opacity: 0; transition: .3s; }
        .dept-card:hover::before { opacity: 1; }
        tbody tr:nth-child(even) { background: rgba(255,255,255,0.025); }
        tbody tr:hover { background: rgba(245,158,11,0.09); }
        .stat-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 14px; margin-bottom: 22px; }
        .stat-card { background: linear-gradient(145deg, rgba(20,32,60,.9), rgba(8,14,30,.95)); border: 1px solid rgba(245,158,11,.35); border-radius: 20px; padding: 18px; text-align: center; }
        .stat-card .num { font-size: 2.1rem; font-weight: 900; }
        .stat-card .lbl { color: var(--text-muted); font-size: .9rem; }
        .ring { --p: 0; width: 92px; height: 92px; border-radius: 50%; margin: 0 auto 6px; display: grid; place-items: center; background: conic-gradient(var(--accent-green) calc(var(--p) * 1%), rgba(255,255,255,.1) 0); }
        .ring span { width: 70px; height: 70px; border-radius: 50%; background: #07101f; display: grid; place-items: center; font-weight: 900; }
        .bar-row { margin-bottom: 12px; font-size: .92rem; }
        .bar-track { height: 10px; border-radius: 10px; background: rgba(255,255,255,.1); overflow: hidden; margin-top: 4px; }
        .bar-fill { height: 100%; border-radius: 10px; background: linear-gradient(90deg, #10b981, #f59e0b); }
        .filter-bar { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 10px; align-items: end; margin-bottom: 18px; }
        .filter-bar .input-field { margin-bottom: 0; }
        .del-btn { background: rgba(239,68,68,.15); border: 1px solid #ef4444; color: #fca5a5; border-radius: 10px; padding: 6px 10px; cursor: pointer; }
        .chip-btn { background: var(--accent-green); color: #fff; padding: 8px 16px; border-radius: 10px; text-decoration: none; font-weight: bold; margin-left: 8px; display: inline-block; }
        @media (max-width: 600px) { body { padding: 8px; } .main-container { padding: 16px; border-radius: 24px; } .brand-header h1 { font-size: 1.6rem; } }

        .support-footer {
            text-align: center; margin-top: 25px; padding-top: 15px;
            border-top: 1px solid rgba(255,255,255,0.1); font-size: 0.9rem; color: var(--text-muted);
        }
        .support-footer a { color: var(--accent-gold); text-decoration: none; font-weight: bold; }
    </style>
</head>
<body>
<canvas id="particles-canvas"></canvas>
<div class="main-container">
    <div class="brand-header">
        {% if logo_b64 %}<img src="{{ logo_b64 }}" class="logo-img">{% endif %}
        <h1>\U0001f3db \u062c\u0627\u0645\u0639\u0629 \u0628\u063a\u062f\u0627\u062f</h1>
        <h2>\u0643\u0644\u064a\u0629 \u0627\u0644\u0641\u0646\u0648\u0646 \u0627\u0644\u062c\u0645\u064a\u0644\u0629</h2>
    </div>
    <div class="status-bar">
        <div class="sb-item">\U0001f4c5 <span id="sb-day">--</span> <span id="sb-date">--</span></div>
        <div class="sb-item">\U0001f552 <span id="sb-time">--:--:--</span></div>
        <div class="sb-item"><span id="sb-dot" class="sb-dot"></span><span id="sb-conn">\u062c\u0627\u0631\u064d \u0627\u0644\u0641\u062d\u0635\u2026</span></div>
    </div>
"""

FOOTER_SCRIPTS = """
    <div class="support-footer">
        \u0627\u0644\u062f\u0639\u0645 \u0627\u0644\u0641\u0646\u064a \u0648\u0627\u0644\u062a\u0637\u0648\u064a\u0631: <a href="https://t.me/beko141" target="_blank">\u062a\u0648\u0627\u0635\u0644 \u0639\u0628\u0631 \u062a\u064a\u0644\u064a\u062c\u0631\u0627\u0645 (@beko141)</a>
    </div>
</div>
<script>
    const canvas = document.getElementById('particles-canvas');
    const ctx = canvas.getContext('2d');
    let particles = [];
    function resize() { canvas.width = window.innerWidth; canvas.height = window.innerHeight; }
    window.addEventListener('resize', resize); resize();
    for (let i = 0; i < 45; i++) {
        particles.push({
            x: Math.random() * canvas.width, y: Math.random() * canvas.height,
            r: Math.random() * 2.5 + 1, dx: (Math.random() - 0.5) * 1, dy: (Math.random() - 0.5) * 1
        });
    }
    function animate() {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        ctx.fillStyle = 'rgba(245, 158, 11, 0.5)';
        particles.forEach(p => {
            p.x += p.dx; p.y += p.dy;
            if (p.x < 0 || p.x > canvas.width) p.dx *= -1;
            if (p.y < 0 || p.y > canvas.height) p.dy *= -1;
            ctx.beginPath(); ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2); ctx.fill();
        });
        requestAnimationFrame(animate);
    }
    animate();

    (function () {
        const tz = 'Asia/Baghdad';
        const dayEl = document.getElementById('sb-day');
        const dateEl = document.getElementById('sb-date');
        const timeEl = document.getElementById('sb-time');
        const connEl = document.getElementById('sb-conn');
        const dotEl = document.getElementById('sb-dot');
        const fDay = new Intl.DateTimeFormat('ar-IQ-u-nu-latn', { weekday: 'long', timeZone: tz });
        const fDate = new Intl.DateTimeFormat('en-GB', { year: 'numeric', month: '2-digit', day: '2-digit', timeZone: tz });
        const fTime = new Intl.DateTimeFormat('ar-IQ-u-nu-latn', { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: true, timeZone: tz });

        function tick() {
            const now = new Date();
            dayEl.textContent = fDay.format(now);
            dateEl.textContent = fDate.format(now);
            timeEl.textContent = fTime.format(now);
        }
        tick();
        setInterval(tick, 1000);

        let online = navigator.onLine;
        function render() {
            connEl.textContent = online ? '\u0645\u062a\u0635\u0644 \u0628\u0627\u0644\u062e\u0627\u062f\u0645' : '\u063a\u064a\u0631 \u0645\u062a\u0635\u0644';
            dotEl.style.background = online ? '#10b981' : '#ef4444';
            dotEl.style.boxShadow = online ? '0 0 10px #10b981' : '0 0 10px #ef4444';
        }
        async function check() {
            if (!navigator.onLine) { online = false; render(); return; }
            const ctl = new AbortController();
            const to = setTimeout(function () { ctl.abort(); }, 5000);
            try {
                const r = await fetch('/ping', { cache: 'no-store', signal: ctl.signal });
                online = r.ok;
            } catch (e) {
                online = false;
            }
            clearTimeout(to);
            render();
        }
        window.addEventListener('online', check);
        window.addEventListener('offline', check);
        check();
        setInterval(check, 15000);
        if ('serviceWorker' in navigator) { navigator.serviceWorker.register('/sw.js').catch(function () {}); }

        document.querySelectorAll('form').forEach(function (f) {
            f.addEventListener('submit', function (e) {
                if (!online) {
                    e.preventDefault();
                    alert('\u0644\u0627 \u064a\u0648\u062c\u062f \u0627\u062a\u0635\u0627\u0644 \u0628\u0627\u0644\u062e\u0627\u062f\u0645\u060c \u0644\u0645 \u064a\u064f\u0631\u0633\u0644 \u0627\u0644\u062a\u0642\u0631\u064a\u0631. \u062d\u0627\u0648\u0644 \u0639\u0646\u062f \u0639\u0648\u062f\u0629 \u0627\u0644\u0627\u062a\u0635\u0627\u0644.');
                }
            });
        });
    })();
</script>
</body>
</html>
"""

@app.route('/')
def index():
    if 'user_role' in session:
        if session['user_role'] == 'head':
            return redirect(url_for('head_dashboard'))
        return redirect(url_for('departments'))
    
    error = request.args.get('error')
    ok = request.args.get('ok')
    html = BASE_CSS_AND_HEAD + """
    <div style="max-width: 550px; margin: 0 auto;">
        {% if error %}<div style="background:rgba(239,68,68,0.2); border-right:5px solid #ef4444; padding:12px; border-radius:10px; margin-bottom:15px; color:#fca5a5;">\u26a0\ufe0f {{ error }}</div>{% endif %}
        {% if ok %}<div style="background:rgba(16,185,129,0.2); border-right:5px solid #10b981; padding:12px; border-radius:10px; margin-bottom:15px; color:#6ee7b7;">\u2705 {{ ok }}</div>{% endif %}
        
        <div style="background: rgba(245,158,11,0.15); border-right: 5px solid var(--accent-gold); padding: 15px; border-radius: 14px; margin-bottom: 20px; font-size: 0.95rem; line-height: 1.7;">
            \u2728 <strong>\u0627\u0644\u0628\u0648\u0627\u0628\u0629 \u0627\u0644\u0633\u064a\u0627\u062f\u064a\u0629 \u0627\u0644\u0645\u0648\u062d\u062f\u0629 \u0644\u0644\u062a\u062d\u0642\u0642 \u0627\u0644\u0623\u0643\u0627\u062f\u064a\u0645\u064a:</strong><br>
            \u0623\u0647\u0644\u0627\u064b \u0648\u0645\u0631\u062d\u0628\u0627\u064b \u0628\u0633\u0641\u064a\u0631 \u0627\u0644\u0641\u0646 \u0648\u0627\u0644\u0639\u0644\u0645 \u0641\u064a \u0631\u062d\u0627\u0628 \u0643\u0644\u064a\u0629 \u0627\u0644\u0641\u0646\u0648\u0646 \u0627\u0644\u062c\u0645\u064a\u0644\u0629. \u0633\u062c\u0651\u0644 \u062f\u062e\u0648\u0644\u0643 \u0644\u0644\u0645\u062a\u0627\u0628\u0639\u0629.
        </div>

        <form action="/login" method="POST">
            <input type="hidden" name="_csrf" value="{{ csrf_token }}">
            <label style="color:var(--accent-gold); font-weight:bold; display:block; margin-bottom:6px;">\u0627\u0644\u0628\u0631\u064a\u062f \u0627\u0644\u0625\u0644\u0643\u062a\u0631\u0648\u0646\u064a:</label>
            <input type="email" name="user_email" class="input-field" placeholder="name@cofarts.uobaghdad.edu.iq" required>

            <label style="color:var(--accent-gold); font-weight:bold; display:block; margin-bottom:6px;">\u0643\u0644\u0645\u0629 \u0627\u0644\u0645\u0631\u0648\u0631:</label>
            <input type="password" name="password" class="input-field" required>

            <button type="submit" class="btn-action">\u062f\u062e\u0648\u0644 \u0627\u0644\u0645\u0646\u0638\u0648\u0645\u0629 \u0627\u0644\u0623\u0643\u0627\u062f\u064a\u0645\u064a\u0629</button>
        </form>
        <p style="text-align:center; margin-top:18px;"><a href="/register" style="color:var(--accent-gold); font-weight:bold; text-decoration:none;">\u0623\u0633\u062a\u0627\u0630 \u062c\u062f\u064a\u062f\u061f \u0625\u0646\u0634\u0627\u0621 \u062d\u0633\u0627\u0628</a></p>
    </div>
    """ + FOOTER_SCRIPTS
    return render_template_string(html, logo_b64=get_logo_base64(), error=error, ok=ok)

LOGIN_FAILS = {}

@app.route('/login', methods=['POST'])
def login():
    email = (request.form.get('user_email') or '').strip().lower()
    password = request.form.get('password') or ''

    fails, last = LOGIN_FAILS.get(email, (0, 0))
    if time.time() - last > 300:
        fails = 0
    if fails >= 5:
        return redirect(url_for('index', error='\u0645\u062d\u0627\u0648\u0644\u0627\u062a \u0643\u062b\u064a\u0631\u0629\u060c \u062d\u0627\u0648\u0644 \u0628\u0639\u062f 5 \u062f\u0642\u0627\u0626\u0642'))

    conn = sqlite3.connect(DB_NAME)
    row = conn.execute('SELECT name, password_hash, role FROM users WHERE email = ?', (email,)).fetchone()
    conn.close()

    if not row or not check_password_hash(row[1], password):
        LOGIN_FAILS[email] = (fails + 1, time.time())
        return redirect(url_for('index', error='\u0627\u0644\u0628\u0631\u064a\u062f \u0627\u0644\u0625\u0644\u0643\u062a\u0631\u0648\u0646\u064a \u0623\u0648 \u0643\u0644\u0645\u0629 \u0627\u0644\u0645\u0631\u0648\u0631 \u063a\u064a\u0631 \u0635\u062d\u064a\u062d\u0629'))

    LOGIN_FAILS.pop(email, None)
    session.clear()
    session['user_name'] = row[0]
    session['user_role'] = row[2]
    session['user_email'] = email
    if row[2] == 'head':
        return redirect(url_for('head_dashboard'))
    return redirect(url_for('departments'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    error = None
    if request.method == 'POST':
        name = (request.form.get('user_name') or '').strip()
        email = (request.form.get('user_email') or '').strip().lower()
        password = request.form.get('password') or ''
        code = request.form.get('code') or ''
        if not REGISTER_CODE or not secrets.compare_digest(code.encode(), REGISTER_CODE.encode()):
            error = '\u0631\u0645\u0632 \u0627\u0644\u062a\u0633\u062c\u064a\u0644 \u063a\u064a\u0631 \u0635\u062d\u064a\u062d'
        elif not name or '@' not in email or email == HEAD_OFFICIAL_EMAIL.lower():
            error = '\u0623\u062f\u062e\u0644 \u0627\u0644\u0627\u0633\u0645 \u0648\u0628\u0631\u064a\u062f\u0627\u064b \u0625\u0644\u0643\u062a\u0631\u0648\u0646\u064a\u0627\u064b \u0635\u062d\u064a\u062d\u0627\u064b'
        elif len(password) < 8:
            error = '\u0643\u0644\u0645\u0629 \u0627\u0644\u0645\u0631\u0648\u0631 \u064a\u062c\u0628 \u0623\u0644\u0627 \u062a\u0642\u0644 \u0639\u0646 8 \u0623\u062d\u0631\u0641'
        else:
            conn = sqlite3.connect(DB_NAME)
            try:
                conn.execute('INSERT INTO users (email, name, password_hash, role) VALUES (?, ?, ?, ?)',
                             (email, name, generate_password_hash(password), 'doctor'))
                conn.commit()
                return redirect(url_for('index', ok='\u062a\u0645 \u0625\u0646\u0634\u0627\u0621 \u0627\u0644\u062d\u0633\u0627\u0628\u060c \u0633\u062c\u0651\u0644 \u062f\u062e\u0648\u0644\u0643 \u0627\u0644\u0622\u0646'))
            except sqlite3.IntegrityError:
                error = '\u0647\u0630\u0627 \u0627\u0644\u0628\u0631\u064a\u062f \u0645\u0633\u062c\u0644 \u0645\u0633\u0628\u0642\u0627\u064b'
            finally:
                conn.close()

    lbl = "color:var(--accent-gold); font-weight:bold; display:block; margin-bottom:6px;"
    html = BASE_CSS_AND_HEAD + """
    <div style="max-width: 550px; margin: 0 auto;">
        {% if error %}<div style="background:rgba(239,68,68,0.2); border-right:5px solid #ef4444; padding:12px; border-radius:10px; margin-bottom:15px; color:#fca5a5;">\u26a0\ufe0f {{ error }}</div>{% endif %}
        <h3 style="color:var(--accent-gold); text-align:center;">\u0625\u0646\u0634\u0627\u0621 \u062d\u0633\u0627\u0628 \u0623\u0633\u062a\u0627\u0630</h3>
        <form method="POST">
            <input type="hidden" name="_csrf" value="{{ csrf_token }}">
            <label style="{{ lbl }}">\u0627\u0644\u0627\u0633\u0645 \u0627\u0644\u0643\u0627\u0645\u0644 / \u0627\u0644\u0644\u0642\u0628 \u0627\u0644\u0639\u0644\u0645\u064a:</label>
            <input type="text" name="user_name" class="input-field" required>
            <label style="{{ lbl }}">\u0627\u0644\u0628\u0631\u064a\u062f \u0627\u0644\u0625\u0644\u0643\u062a\u0631\u0648\u0646\u064a:</label>
            <input type="email" name="user_email" class="input-field" required>
            <label style="{{ lbl }}">\u0643\u0644\u0645\u0629 \u0627\u0644\u0645\u0631\u0648\u0631 (8 \u0623\u062d\u0631\u0641 \u0639\u0644\u0649 \u0627\u0644\u0623\u0642\u0644):</label>
            <input type="password" name="password" class="input-field" minlength="8" required>
            <label style="{{ lbl }}">\u0631\u0645\u0632 \u0627\u0644\u062a\u0633\u062c\u064a\u0644 (\u064a\u0639\u0637\u064a\u0647 \u0644\u0643 \u0645\u0642\u0631\u0631 \u0627\u0644\u0642\u0633\u0645):</label>
            <input type="text" name="code" class="input-field" required>
            <button type="submit" class="btn-action">\u0625\u0646\u0634\u0627\u0621 \u0627\u0644\u062d\u0633\u0627\u0628</button>
        </form>
        <p style="text-align:center; margin-top:18px;"><a href="/" style="color:var(--accent-gold); font-weight:bold; text-decoration:none;">\u2190 \u0627\u0644\u0639\u0648\u062f\u0629 \u0644\u062a\u0633\u062c\u064a\u0644 \u0627\u0644\u062f\u062e\u0648\u0644</a></p>
    </div>
    """ + FOOTER_SCRIPTS
    return render_template_string(html, logo_b64=get_logo_base64(), error=error, lbl=lbl)

@app.route('/ping')
def ping():
    return ('', 204, {'Cache-Control': 'no-store'})

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/departments')
def departments():
    if 'user_role' not in session:
        return redirect(url_for('index'))
    
    html = BASE_CSS_AND_HEAD + """
    <div class="nav-bar">
        <div>\u0645\u0631\u062d\u0628\u0627\u064b \u0628\u0643: <strong style="color:var(--accent-gold);">{{ user_name }}</strong></div>
        <a href="/logout" class="logout-link">\u062a\u0633\u062c\u064a\u0644 \u0627\u0644\u062e\u0631\u0648\u062c</a>
    </div>
    <h3 style="text-align:center; color:var(--accent-gold); margin-bottom:20px;">\u0627\u062e\u062a\u0631 \u0627\u0644\u0642\u0633\u0645 \u0627\u0644\u0623\u0643\u0627\u062f\u064a\u0645\u064a</h3>
    <div class="dept-grid">
        {% for d in depts %}
        <a href="/select_options?dept={{ d.name }}" class="dept-card">
            <div style="font-size:2.5rem; margin-bottom:10px;">{{ d.icon }}</div>
            <div style="font-size:1.25rem; font-weight:800; color:var(--accent-gold);">{{ d.name }}</div>
            <div style="font-size:0.9rem; color:var(--text-muted); margin-top:6px;">{{ d.desc }}</div>
        </a>
        {% endfor %}
    </div>
    """ + FOOTER_SCRIPTS
    return render_template_string(html, logo_b64=get_logo_base64(), user_name=session['user_name'], depts=COLLEGE_DEPARTMENTS)

@app.route('/select_options')
def select_options():
    if 'user_role' not in session:
        return redirect(url_for('index'))
    dept = request.args.get('dept', '\u0642\u0633\u0645 \u0627\u0644\u062a\u0631\u0628\u064a\u0629 \u0627\u0644\u0641\u0646\u064a\u0629')
    shift = request.args.get('shift', '\u0635\u0628\u0627\u062d\u064a')
    
    dept_data = FULL_COLLEGE_DATA.get(dept, {})
    shifts = list(dept_data.keys())
    stages = list(dept_data.get(shift, {}).keys())
    
    html = BASE_CSS_AND_HEAD + """
    <div class="nav-bar">
        <div>\u0627\u0644\u0642\u0633\u0645: <strong style="color:var(--accent-gold);">{{ dept }}</strong></div>
        <div>
            <a href="/departments" style="color:var(--accent-green); text-decoration:none; margin-left:15px; font-weight:bold;">\u2190 \u0627\u0644\u0623\u0642\u0633\u0627\u0645</a>
            <a href="/logout" class="logout-link">\u062e\u0631\u0648\u062c</a>
        </div>
    </div>

    <div style="background:rgba(14,24,46,0.9); padding:25px; border-radius:20px; border:1px solid rgba(255,255,255,0.15);">
        <h3 style="color:var(--accent-gold); margin-top:0;">1. \u0627\u062e\u062a\u0631 \u0646\u0648\u0639 \u0627\u0644\u062f\u0631\u0627\u0633\u0629:</h3>
        <div style="margin-bottom:25px;">
            {% for s in shifts %}
            <a href="/select_options?dept={{ dept }}&shift={{ s }}" class="pill-btn {% if s == shift %}active{% endif %}">\u0627\u0644\u062f\u0631\u0627\u0633\u0629 {{ s }}\u0629</a>
            {% endfor %}
        </div>

        <h3 style="color:var(--accent-gold);">2. \u0627\u062e\u062a\u0631 \u0627\u0644\u0645\u0631\u062d\u0644\u0629 \u0648\u0627\u0644\u0634\u0639\u0628\u0629 \u0644\u0631\u0635\u062f \u0627\u0644\u062d\u0636\u0648\u0631:</h3>
        {% if not stages %}<p style="color:var(--text-muted);">\u0644\u0627 \u062a\u0648\u062c\u062f \u0623\u0633\u0645\u0627\u0621 \u0637\u0644\u0628\u0629 \u0644\u0647\u0630\u0627 \u0627\u0644\u0642\u0633\u0645 \u0628\u0639\u062f. \u064a\u0636\u064a\u0641\u0647\u0627 \u0645\u0642\u0631\u0631 \u0627\u0644\u0642\u0633\u0645 \u0645\u0646 \u00ab\u0625\u062f\u0627\u0631\u0629 \u0627\u0644\u0637\u0644\u0628\u0629\u00bb.</p>{% endif %}
        {% for st in stages %}
            <div style="margin-bottom:15px; padding:15px; background:rgba(5,10,24,0.8); border-radius:14px;">
                <strong style="color:var(--accent-green); display:block; margin-bottom:10px;">{{ st }}:</strong>
                {% for sec in dept_data[shift][st].keys() %}
                    <a href="/attendance?dept={{ dept }}&shift={{ shift }}&stage={{ st }}&section={{ sec }}" class="pill-btn">{{ sec }}</a>
                {% endfor %}
            </div>
        {% endfor %}
    </div>
    """ + FOOTER_SCRIPTS
    return render_template_string(html, logo_b64=get_logo_base64(), dept=dept, shift=shift, shifts=shifts, stages=stages, dept_data=dept_data)

@app.route('/attendance', methods=['GET', 'POST'])
def attendance():
    if 'user_role' not in session:
        return redirect(url_for('index'))
        
    dept = request.args.get('dept')
    shift = request.args.get('shift')
    stage = request.args.get('stage')
    section = request.args.get('section')
    
    students = FULL_COLLEGE_DATA.get(dept, {}).get(shift, {}).get(stage, {}).get(section, [])
    if not students:
        return redirect(url_for('departments'))
    
    if request.method == 'POST':
        subject = ' '.join((request.form.get('subject') or '\u0645\u0627\u062f\u0629 \u062f\u0631\u0627\u0633\u064a\u0629').split())
        today = baghdad_now().date()
        try:
            lecture_date = datetime.strptime(request.form.get('lecture_date', ''), '%Y-%m-%d').date()
        except ValueError:
            lecture_date = today
        if lecture_date > today:
            lecture_date = today
        present = 0
        absent = 0
        details_list = []
        
        for idx, st_name in enumerate(students):
            status = request.form.get(f'status_{idx}', '\u062d\u0627\u0636\u0631')
            if status == '\u062d\u0627\u0636\u0631':
                present += 1
            else:
                absent += 1
                details_list.append(f"{st_name} ({status})")
                
        conn = sqlite3.connect(DB_NAME)
        try:
            conn.execute('''
                INSERT INTO reports (doctor, dept, shift, stage, section, subject, timestamp, present_count, absent_count, details, lecture_date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (session['user_name'], dept, shift, stage, section, subject, baghdad_now().strftime("%Y-%m-%d %H:%M"),
                  present, absent, " | ".join(details_list) if details_list else "\u0644\u0627 \u064a\u0648\u062c\u062f \u063a\u064a\u0627\u0628", lecture_date.isoformat()))
            conn.commit()
        except sqlite3.IntegrityError:
            return redirect(url_for('attendance', dept=dept, shift=shift, stage=stage, section=section,
                                    error='\u0633\u0628\u0642 \u062a\u0633\u062c\u064a\u0644 \u062d\u0636\u0648\u0631 \u0647\u0630\u0647 \u0627\u0644\u0645\u0627\u062f\u0629 \u0644\u0647\u0630\u0647 \u0627\u0644\u0634\u0639\u0628\u0629 \u0641\u064a \u0647\u0630\u0627 \u0627\u0644\u062a\u0627\u0631\u064a\u062e'))
        finally:
            conn.close()
        
        return render_template_string(BASE_CSS_AND_HEAD + """
        <div style="text-align:center; padding:30px;">
            <div style="font-size:4rem;">\u2705</div>
            <h2 style="color:var(--accent-green);">\u062a\u0645 \u0625\u0631\u0633\u0627\u0644 \u0648\u062d\u0641\u0638 \u0633\u062c\u0644 \u0627\u0644\u062d\u0636\u0648\u0631 \u0628\u0646\u062c\u0627\u062d!</h2>
            <p style="color:var(--text-muted);">\u0627\u0644\u062d\u0636\u0648\u0631: {{ present }} | \u0627\u0644\u063a\u064a\u0627\u0628/\u0627\u0644\u0625\u062c\u0627\u0632\u0627\u062a: {{ absent }}</p>
            <br>
            <a href="/departments" class="btn-action" style="text-decoration:none; display:inline-block; width:auto;">\u0627\u0644\u0639\u0648\u062f\u0629 \u0644\u0644\u0623\u0642\u0633\u0627\u0645</a>
        </div>
        """ + FOOTER_SCRIPTS, logo_b64=get_logo_base64(), present=present, absent=absent)

    html = BASE_CSS_AND_HEAD + """
    <div class="nav-bar">
        <div><strong>{{ dept }}</strong> - {{ shift }} - {{ stage }} ({{ section }})</div>
        <a href="/select_options?dept={{ dept }}&shift={{ shift }}" style="color:var(--accent-gold); text-decoration:none; font-weight:bold;">\u2190 \u0631\u062c\u0648\u0639</a>
    </div>

    <form method="POST">
        <input type="hidden" name="_csrf" value="{{ csrf_token }}">
        {% if error %}<div style="background:rgba(239,68,68,0.2); border-right:5px solid #ef4444; padding:12px; border-radius:10px; margin-bottom:15px; color:#fca5a5;">\u26a0\ufe0f {{ error }}</div>{% endif %}
        <label style="color:var(--accent-gold); font-weight:bold; display:block; margin-bottom:6px;">\u062a\u0627\u0631\u064a\u062e \u0627\u0644\u0645\u062d\u0627\u0636\u0631\u0629:</label>
        <input type="date" name="lecture_date" class="input-field" value="{{ today }}" max="{{ today }}" required>
        <label style="color:var(--accent-gold); font-weight:bold; display:block; margin-bottom:6px;">\u0627\u0633\u0645 \u0627\u0644\u0645\u0627\u062f\u0629 \u0627\u0644\u062f\u0631\u0627\u0633\u064a\u0629:</label>
        <input type="text" name="subject" class="input-field" placeholder="\u0627\u0643\u062a\u0628 \u0627\u0633\u0645 \u0627\u0644\u0645\u0627\u062f\u0629 \u0647\u0646\u0627..." required>

        <table>
            <thead>
                <tr>
                    <th style="width:40px;">\u062a</th>
                    <th>\u0627\u0633\u0645 \u0627\u0644\u0637\u0627\u0644\u0628</th>
                    <th style="width:120px;">\u0627\u0644\u062d\u0627\u0644\u0629</th>
                </tr>
            </thead>
            <tbody>
                {% for st in students %}
                <tr>
                    <td>{{ loop.index }}</td>
                    <td style="font-weight:bold;">{{ st }}</td>
                    <td>
                        <select name="status_{{ loop.index0 }}" style="padding:8px; border-radius:8px; background:#050a18; color:#fff; border:1px solid #334155; font-family:'Cairo'; width:100%;">
                            <option value="\u062d\u0627\u0636\u0631">\u062d\u0627\u0636\u0631 \u2705</option>
                            <option value="\u063a\u0627\u0626\u0628">\u063a\u0627\u0626\u0628 \u274c</option>
                            <option value="\u0625\u062c\u0627\u0632\u0629">\u0625\u062c\u0627\u0632\u0629 \U0001f4dd</option>
                        </select>
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
        <br>
        <button type="submit" class="btn-action">\u0627\u0639\u062a\u0645\u0627\u062f \u0648\u0625\u0631\u0633\u0627\u0644 \u0627\u0644\u062a\u0642\u0631\u064a\u0631 \u0644\u0645\u0642\u0631\u0631 \u0627\u0644\u0642\u0633\u0645</button>
    </form>
    """ + FOOTER_SCRIPTS
    return render_template_string(html, logo_b64=get_logo_base64(), dept=dept, shift=shift, stage=stage, section=section, students=students,
                                  today=baghdad_now().date().isoformat(), error=request.args.get('error'))

def head_only():
    return session.get('user_role') == 'head'

def _filtered_reports():
    f = {k: request.args.get(k, '').strip() for k in ('dept', 'q', 'd1', 'd2')}
    where, params = [], []
    if f['dept']:
        where.append('dept = ?'); params.append(f['dept'])
    if f['q']:
        where.append('(subject LIKE ? OR doctor LIKE ?)'); params += ['%' + f['q'] + '%'] * 2
    if f['d1']:
        where.append('COALESCE(lecture_date, substr(timestamp, 1, 10)) >= ?'); params.append(f['d1'])
    if f['d2']:
        where.append('COALESCE(lecture_date, substr(timestamp, 1, 10)) <= ?'); params.append(f['d2'])
    sql = 'SELECT * FROM reports' + (' WHERE ' + ' AND '.join(where) if where else '') + \
          ' ORDER BY COALESCE(lecture_date, substr(timestamp, 1, 10)) DESC, id DESC'
    conn = sqlite3.connect(DB_NAME)
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return rows, f

@app.route('/head_dashboard')
def head_dashboard():
    if not head_only():
        return redirect(url_for('index'))
    reports, f = _filtered_reports()
    present = sum(r[8] for r in reports)
    absent = sum(r[9] for r in reports)
    rate = round(present * 100 / (present + absent)) if present + absent else 0
    by_dept = {}
    for r in reports:
        d = by_dept.setdefault(r[2], [0, 0])
        d[0] += r[8]; d[1] += r[9]
    bars = [(n, round(a * 100 / (a + b)) if a + b else 0, a, b) for n, (a, b) in by_dept.items()]
    html = BASE_CSS_AND_HEAD + """
    <div class="nav-bar">
        <div>\u0644\u0648\u062d\u0629 \u0645\u0642\u0631\u0631 \u0627\u0644\u0642\u0633\u0645: <strong style="color:var(--accent-green);">{{ user_name }}</strong></div>
        <div>
            <a href="/admin/students" class="chip-btn" style="background:var(--accent-blue);">\U0001f465 \u0625\u062f\u0627\u0631\u0629 \u0627\u0644\u0637\u0644\u0628\u0629</a>
            <a href="/admin/accounts" class="chip-btn" style="background:#8b5cf6;">\U0001f511 \u062d\u0633\u0627\u0628\u0627\u062a \u0627\u0644\u0623\u0633\u0627\u062a\u0630\u0629</a>
            <a href="/export_csv{{ '?' + qs if qs }}" class="chip-btn">\U0001f4e5 \u062a\u0635\u062f\u064a\u0631 CSV</a>
            <a href="/logout" class="logout-link">\u062e\u0631\u0648\u062c</a>
        </div>
    </div>

    <div class="stat-grid">
        <div class="stat-card"><div class="num" style="color:var(--accent-gold);">{{ reports|length }}</div><div class="lbl">\u062a\u0642\u0631\u064a\u0631 \u062d\u0636\u0648\u0631</div></div>
        <div class="stat-card"><div class="num" style="color:#10b981;">{{ present }}</div><div class="lbl">\u0625\u062c\u0645\u0627\u0644\u064a \u0627\u0644\u062d\u0636\u0648\u0631</div></div>
        <div class="stat-card"><div class="num" style="color:#ef4444;">{{ absent }}</div><div class="lbl">\u0627\u0644\u063a\u064a\u0627\u0628 \u0648\u0627\u0644\u0625\u062c\u0627\u0632\u0627\u062a</div></div>
        <div class="stat-card"><div class="ring" style="--p: {{ rate }};"><span>{{ rate }}%</span></div><div class="lbl">\u0646\u0633\u0628\u0629 \u0627\u0644\u062d\u0636\u0648\u0631</div></div>
    </div>

    {% if bars %}
    <div style="background:rgba(14,24,46,0.9); padding:18px 22px; border-radius:20px; border:1px solid rgba(255,255,255,0.12); margin-bottom:20px;">
        <strong style="color:var(--accent-gold);">\u0646\u0633\u0628\u0629 \u0627\u0644\u062d\u0636\u0648\u0631 \u062d\u0633\u0628 \u0627\u0644\u0642\u0633\u0645</strong>
        {% for n, pct, a, b in bars %}
        <div class="bar-row"><div style="display:flex; justify-content:space-between;"><span>{{ n }}</span><span>{{ pct }}%</span></div>
        <div class="bar-track"><div class="bar-fill" style="width: {{ pct }}%;"></div></div></div>
        {% endfor %}
    </div>
    {% endif %}

    <form method="GET" class="filter-bar">
        <select name="dept" class="input-field">
            <option value="">\u0643\u0644 \u0627\u0644\u0623\u0642\u0633\u0627\u0645</option>
            {% for d in depts %}<option value="{{ d.name }}" {% if d.name == f.dept %}selected{% endif %}>{{ d.name }}</option>{% endfor %}
        </select>
        <input type="text" name="q" class="input-field" placeholder="\u0628\u062d\u062b \u0628\u0627\u0644\u0645\u0627\u062f\u0629 \u0623\u0648 \u0627\u0644\u0623\u0633\u062a\u0627\u0630" value="{{ f.q }}">
        <input type="date" name="d1" class="input-field" value="{{ f.d1 }}" title="\u0645\u0646 \u062a\u0627\u0631\u064a\u062e">
        <input type="date" name="d2" class="input-field" value="{{ f.d2 }}" title="\u0625\u0644\u0649 \u062a\u0627\u0631\u064a\u062e">
        <button type="submit" class="btn-action" style="padding:12px;">\u062a\u0635\u0641\u064a\u0629</button>
    </form>

    <div style="overflow-x:auto;">
        <table>
            <thead><tr>
                <th>\u062a\u0627\u0631\u064a\u062e \u0627\u0644\u0645\u062d\u0627\u0636\u0631\u0629</th><th>\u0627\u0644\u0623\u0633\u062a\u0627\u0630</th><th>\u0627\u0644\u0642\u0633\u0645 \u0648\u0627\u0644\u0645\u0631\u062d\u0644\u0629</th><th>\u0627\u0644\u0645\u0627\u062f\u0629</th><th>\u0627\u0644\u062d\u0636\u0648\u0631 / \u0627\u0644\u063a\u064a\u0627\u0628</th><th>\u0627\u0644\u0637\u0644\u0628\u0629 \u0627\u0644\u063a\u0627\u0626\u0628\u0648\u0646</th><th></th>
            </tr></thead>
            <tbody>
                {% for r in reports %}
                <tr>
                    <td>{{ r[11] or '\u2014' }}<br><span style="font-size:0.75rem; color:var(--text-muted);">\u0623\u064f\u0631\u0633\u0644 {{ r[7] }}</span></td>
                    <td>{{ r[1] }}</td>
                    <td>{{ r[2] }} ({{ r[3] }} - {{ r[4] }} {{ r[5] }})</td>
                    <td>{{ r[6] }}</td>
                    <td><span style="color:#10b981;">{{ r[8] }} \u062d\u0627\u0636\u0631</span> / <span style="color:#ef4444;">{{ r[9] }} \u063a\u0627\u0626\u0628</span></td>
                    <td style="font-size:0.85rem; color:#fca5a5;">{{ r[10] }}</td>
                    <td><form method="POST" action="/report/{{ r[0] }}/delete" style="margin:0;" onsubmit="return confirm('\u062d\u0630\u0641 \u0647\u0630\u0627 \u0627\u0644\u0633\u062c\u0644 \u0646\u0647\u0627\u0626\u064a\u0627\u064b\u061f');">
                        <input type="hidden" name="_csrf" value="{{ csrf_token }}"><button class="del-btn" title="\u062d\u0630\u0641">\U0001f5d1</button></form></td>
                </tr>
                {% else %}
                <tr><td colspan="7" style="text-align:center; color:var(--text-muted);">\u0644\u0627 \u062a\u0648\u062c\u062f \u0633\u062c\u0644\u0627\u062a \u0645\u0637\u0627\u0628\u0642\u0629.</td></tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
    """ + FOOTER_SCRIPTS
    return render_template_string(html, logo_b64=get_logo_base64(), user_name=session['user_name'], reports=reports,
                                  present=present, absent=absent, rate=rate, bars=bars, f=f,
                                  depts=COLLEGE_DEPARTMENTS, qs=urlencode({k: v for k, v in f.items() if v}))

@app.route('/report/<int:rid>/delete', methods=['POST'])
def delete_report(rid):
    if not head_only():
        return redirect(url_for('index'))
    conn = sqlite3.connect(DB_NAME)
    conn.execute('DELETE FROM reports WHERE id = ?', (rid,))
    conn.commit()
    conn.close()
    return redirect(url_for('head_dashboard'))

@app.route('/admin/students', methods=['GET', 'POST'])
def admin_students():
    if not head_only():
        return redirect(url_for('index'))
    msg = err = None
    if request.method == 'POST':
        fl = request.files.get('file')
        if not fl or not fl.filename.lower().endswith('.xlsx'):
            err = '\u0627\u062e\u062a\u0631 \u0645\u0644\u0641 Excel \u0628\u0635\u064a\u063a\u0629 xlsx'
        else:
            try:
                added, skipped = import_students_xlsx(fl.stream, replace=bool(request.form.get('replace')))
                msg = f'\u062a\u0645 \u0627\u0633\u062a\u064a\u0631\u0627\u062f {added} \u0637\u0627\u0644\u0628\u0627\u064b' + (f' \u0648\u062a\u062c\u0627\u0647\u0644 {skipped} \u0635\u0641\u0627\u064b \u063a\u064a\u0631 \u0635\u0627\u0644\u062d' if skipped else '')
            except Exception:
                err = '\u062a\u0639\u0630\u0651\u0631 \u0642\u0631\u0627\u0621\u0629 \u0627\u0644\u0645\u0644\u0641. \u062a\u0623\u0643\u062f \u0645\u0646 \u0627\u0644\u0623\u0639\u0645\u062f\u0629: \u0627\u0644\u0642\u0633\u0645\u060c \u0627\u0644\u062f\u0631\u0627\u0633\u0629\u060c \u0627\u0644\u0645\u0631\u062d\u0644\u0629\u060c \u0627\u0644\u0634\u0639\u0628\u0629\u060c \u0627\u0644\u0627\u0633\u0645'
    counts = []
    for d in COLLEGE_DEPARTMENTS:
        n = sum(len(v) for sh in FULL_COLLEGE_DATA.get(d['name'], {}).values() for st in sh.values() for v in st.values())
        counts.append((d['icon'], d['name'], n))
    html = BASE_CSS_AND_HEAD + """
    <div class="nav-bar">
        <div>\u0625\u062f\u0627\u0631\u0629 \u0627\u0644\u0637\u0644\u0628\u0629</div>
        <div><a href="/head_dashboard" class="chip-btn" style="background:var(--accent-blue);">\u2190 \u0627\u0644\u0644\u0648\u062d\u0629</a><a href="/logout" class="logout-link">\u062e\u0631\u0648\u062c</a></div>
    </div>
    {% if err %}<div style="background:rgba(239,68,68,0.2); border-right:5px solid #ef4444; padding:12px; border-radius:10px; margin-bottom:15px; color:#fca5a5;">\u26a0\ufe0f {{ err }}</div>{% endif %}
    {% if msg %}<div style="background:rgba(16,185,129,0.2); border-right:5px solid #10b981; padding:12px; border-radius:10px; margin-bottom:15px; color:#6ee7b7;">\u2705 {{ msg }}</div>{% endif %}
    <div class="stat-grid">
        {% for icon, name, n in counts %}<div class="stat-card"><div style="font-size:1.8rem;">{{ icon }}</div><div class="num" style="color:var(--accent-gold);">{{ n }}</div><div class="lbl">{{ name }}</div></div>{% endfor %}
    </div>
    <div style="background:rgba(14,24,46,0.9); padding:22px; border-radius:20px; border:1px solid rgba(255,255,255,0.12);">
        <h3 style="color:var(--accent-gold); margin-top:0;">\u0627\u0633\u062a\u064a\u0631\u0627\u062f \u0627\u0644\u0623\u0633\u0645\u0627\u0621 \u0645\u0646 Excel</h3>
        <p style="color:var(--text-muted); line-height:1.8;">\u0646\u0632\u0651\u0644 \u0627\u0644\u0645\u0644\u0641 \u0627\u0644\u062d\u0627\u0644\u064a\u060c \u0639\u062f\u0651\u0644\u0647\u060c \u062b\u0645 \u0627\u0631\u0641\u0639\u0647. \u0627\u0644\u0623\u0639\u0645\u062f\u0629: \u0627\u0644\u0642\u0633\u0645\u060c \u0627\u0644\u062f\u0631\u0627\u0633\u0629\u060c \u0627\u0644\u0645\u0631\u062d\u0644\u0629\u060c \u0627\u0644\u0634\u0639\u0628\u0629\u060c \u0627\u0644\u0627\u0633\u0645. \u062a\u064f\u0631\u062a\u0651\u064e\u0628 \u0627\u0644\u0623\u0633\u0645\u0627\u0621 \u0623\u0628\u062c\u062f\u064a\u0627\u064b \u062a\u0644\u0642\u0627\u0626\u064a\u0627\u064b.</p>
        <a href="/admin/students/export" class="chip-btn">\U0001f4e5 \u062a\u0646\u0632\u064a\u0644 \u0627\u0644\u0623\u0633\u0645\u0627\u0621 \u0627\u0644\u062d\u0627\u0644\u064a\u0629 (Excel)</a>
        <form method="POST" enctype="multipart/form-data" style="margin-top:18px;">
            <input type="hidden" name="_csrf" value="{{ csrf_token }}">
            <input type="file" name="file" accept=".xlsx" class="input-field" required>
            <label style="display:block; margin-bottom:16px;"><input type="checkbox" name="replace" value="1"> \u0627\u0633\u062a\u0628\u062f\u0627\u0644 \u0643\u0644 \u0627\u0644\u0623\u0633\u0645\u0627\u0621 \u0627\u0644\u062d\u0627\u0644\u064a\u0629 \u0628\u0645\u062d\u062a\u0648\u0649 \u0627\u0644\u0645\u0644\u0641</label>
            <button type="submit" class="btn-action">\u0631\u0641\u0639 \u0648\u0627\u0633\u062a\u064a\u0631\u0627\u062f</button>
        </form>
    </div>
    """ + FOOTER_SCRIPTS
    return render_template_string(html, logo_b64=get_logo_base64(), msg=msg, err=err, counts=counts)

PW_CHARS = 'ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnpqrstuvwxyz23456789'
EMAIL_RE = re.compile(r'[^\s,\u060c;]+@[^\s,\u060c;]+')

def build_accounts_xlsx(rows):
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment
    wb = Workbook()
    ws = wb.active
    ws.title = '\u0627\u0644\u062d\u0633\u0627\u0628\u0627\u062a'
    ws.sheet_view.rightToLeft = True
    ws.append(['\u0627\u0644\u0627\u0633\u0645', '\u0627\u0644\u0628\u0631\u064a\u062f \u0627\u0644\u0625\u0644\u0643\u062a\u0631\u0648\u0646\u064a', '\u0643\u0644\u0645\u0629 \u0627\u0644\u0645\u0631\u0648\u0631', '\u0627\u0644\u062d\u0627\u0644\u0629'])
    for c in ws[1]:
        c.font = Font(name='Arial', bold=True, color='FFFFFF')
        c.fill = PatternFill('solid', fgColor='B45309')
        c.alignment = Alignment(horizontal='center')
    for r in rows:
        ws.append(list(r))
    for row in ws.iter_rows(min_row=2):
        for c in row:
            c.font = Font(name='Arial')
        row[1].alignment = Alignment(horizontal='left')
        row[2].alignment = Alignment(horizontal='left')
    ws.append([])
    ws.append(['\u062a\u0646\u0628\u064a\u0647: \u0643\u0644\u0645\u0627\u062a \u0627\u0644\u0645\u0631\u0648\u0631 \u0644\u0627 \u062a\u064f\u062d\u0641\u0638 \u0641\u064a \u0627\u0644\u0645\u0646\u0638\u0648\u0645\u0629 \u0648\u0644\u0627 \u064a\u0645\u0643\u0646 \u0627\u0633\u062a\u0631\u062c\u0627\u0639\u0647\u0627. \u0633\u0644\u0651\u0645 \u0643\u0644 \u0623\u0633\u062a\u0627\u0630 \u0628\u064a\u0627\u0646\u0627\u062a\u0647 \u062b\u0645 \u0627\u062d\u0630\u0641 \u0647\u0630\u0627 \u0627\u0644\u0645\u0644\u0641.'])
    for col, w in zip('ABCD', (30, 38, 18, 14)):
        ws.column_dimensions[col].width = w
    ws.freeze_panes = 'A2'
    bio = io.BytesIO()
    wb.save(bio)
    bio.seek(0)
    return bio

@app.route('/admin/accounts', methods=['GET', 'POST'])
def admin_accounts():
    if not head_only():
        return redirect(url_for('index'))
    err = None
    if request.method == 'POST':
        out, seen, bad = [], set(), 0
        for line in (request.form.get('lines') or '').splitlines()[:300]:
            line = line.strip()
            if not line:
                continue
            m = EMAIL_RE.search(line)
            email = m.group(0).lower() if m else ''
            name = re.sub(r'[,\u060c;\t]+', ' ', line.replace(m.group(0), ' ') if m else line).strip()
            if not m or not name or email == HEAD_OFFICIAL_EMAIL.lower() or email in seen:
                bad += 1
                continue
            seen.add(email)
            pw = ''.join(secrets.choice(PW_CHARS) for _ in range(10))
            conn = sqlite3.connect(DB_NAME)
            try:
                ex = conn.execute('SELECT role FROM users WHERE email = ?', (email,)).fetchone()
                if ex and ex[0] != 'doctor':
                    bad += 1
                    continue
                conn.execute('INSERT INTO users (email, name, password_hash, role) VALUES (?, ?, ?, ?) '
                             'ON CONFLICT(email) DO UPDATE SET name = excluded.name, password_hash = excluded.password_hash',
                             (email, name, generate_password_hash(pw), 'doctor'))
                conn.commit()
            finally:
                conn.close()
            out.append((name, email, pw, '\u0643\u0644\u0645\u0629 \u0645\u0631\u0648\u0631 \u062c\u062f\u064a\u062f\u0629' if ex else '\u062d\u0633\u0627\u0628 \u062c\u062f\u064a\u062f'))
        if out:
            return send_file(build_accounts_xlsx(out), as_attachment=True, download_name='accounts.xlsx',
                             mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        err = '\u0644\u0645 \u064a\u064f\u0646\u0634\u0623 \u0623\u064a \u062d\u0633\u0627\u0628. \u0627\u0643\u062a\u0628 \u0641\u064a \u0643\u0644 \u0633\u0637\u0631: \u0627\u0633\u0645 \u0627\u0644\u0623\u0633\u062a\u0627\u0630 \u062b\u0645 \u0628\u0631\u064a\u062f\u0647 \u0627\u0644\u0625\u0644\u0643\u062a\u0631\u0648\u0646\u064a.'
    conn = sqlite3.connect(DB_NAME)
    docs = conn.execute("SELECT name, email FROM users WHERE role = 'doctor' ORDER BY name").fetchall()
    conn.close()
    html = BASE_CSS_AND_HEAD + """
    <div class="nav-bar">
        <div>\u062d\u0633\u0627\u0628\u0627\u062a \u0627\u0644\u0623\u0633\u0627\u062a\u0630\u0629</div>
        <div><a href="/head_dashboard" class="chip-btn" style="background:var(--accent-blue);">\u2190 \u0627\u0644\u0644\u0648\u062d\u0629</a><a href="/logout" class="logout-link">\u062e\u0631\u0648\u062c</a></div>
    </div>
    {% if err %}<div style="background:rgba(239,68,68,0.2); border-right:5px solid #ef4444; padding:12px; border-radius:10px; margin-bottom:15px; color:#fca5a5;">\u26a0\ufe0f {{ err }}</div>{% endif %}
    <div style="background:rgba(14,24,46,0.9); padding:22px; border-radius:20px; border:1px solid rgba(255,255,255,0.12); margin-bottom:20px;">
        <h3 style="color:var(--accent-gold); margin-top:0;">\u0625\u0646\u0634\u0627\u0621 \u062d\u0633\u0627\u0628\u0627\u062a \u062c\u0627\u0647\u0632\u0629</h3>
        <p style="color:var(--text-muted); line-height:1.8;">\u0627\u0643\u062a\u0628 \u0641\u064a \u0643\u0644 \u0633\u0637\u0631 \u0627\u0633\u0645 \u0627\u0644\u0623\u0633\u062a\u0627\u0630 \u0648\u0628\u0631\u064a\u062f\u0647. \u062a\u064f\u0646\u0634\u0623 \u0644\u0643\u0644 \u0623\u0633\u062a\u0627\u0630 \u0643\u0644\u0645\u0629 \u0645\u0631\u0648\u0631 \u0639\u0634\u0648\u0627\u0626\u064a\u0629\u060c \u0648\u062a\u0646\u0632\u0644 \u0644\u0643 \u0641\u064a \u0645\u0644\u0641 Excel \u0645\u0631\u0629 \u0648\u0627\u062d\u062f\u0629 \u0641\u0642\u0637. \u0625\u0646 \u0643\u062a\u0628\u062a \u0628\u0631\u064a\u062f\u0627\u064b \u0645\u0648\u062c\u0648\u062f\u0627\u064b \u062a\u064f\u0639\u0627\u062f \u0643\u0644\u0645\u0629 \u0645\u0631\u0648\u0631\u0647.</p>
        <form method="POST">
            <input type="hidden" name="_csrf" value="{{ csrf_token }}">
            <textarea name="lines" class="input-field" rows="7" placeholder="\u062f. \u0623\u062d\u0645\u062f \u0639\u0644\u064a\u060c ahmed@cofarts.uobaghdad.edu.iq" required></textarea>
            <button type="submit" class="btn-action">\u0625\u0646\u0634\u0627\u0621 \u0648\u062a\u0646\u0632\u064a\u0644 \u0645\u0644\u0641 \u0627\u0644\u062d\u0633\u0627\u0628\u0627\u062a</button>
        </form>
    </div>
    <h3 style="color:var(--accent-gold);">\u0627\u0644\u062d\u0633\u0627\u0628\u0627\u062a \u0627\u0644\u062d\u0627\u0644\u064a\u0629 ({{ docs|length }})</h3>
    <div style="overflow-x:auto;"><table><thead><tr><th>\u0627\u0644\u0627\u0633\u0645</th><th>\u0627\u0644\u0628\u0631\u064a\u062f</th></tr></thead><tbody>
        {% for n, e in docs %}<tr><td>{{ n }}</td><td style="direction:ltr; text-align:right;">{{ e }}</td></tr>{% else %}<tr><td colspan="2" style="text-align:center; color:var(--text-muted);">\u0644\u0627 \u062a\u0648\u062c\u062f \u062d\u0633\u0627\u0628\u0627\u062a \u0628\u0639\u062f.</td></tr>{% endfor %}
    </tbody></table></div>
    """ + FOOTER_SCRIPTS
    return render_template_string(html, logo_b64=get_logo_base64(), err=err, docs=docs)

@app.route('/admin/students/export')
def admin_students_export():
    if not head_only():
        return redirect(url_for('index'))
    return send_file(build_students_xlsx(students_rows()), as_attachment=True, download_name='students.xlsx',
                     mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

@app.route('/export_csv')
def export_csv():
    if not head_only():
        return redirect(url_for('index'))
    rows, _ = _filtered_reports()
    si = io.StringIO()
    si.write('\ufeff')
    cw = csv.writer(si)
    cw.writerow(['ID', '\u0627\u0644\u0623\u0633\u062a\u0627\u0630', '\u0627\u0644\u0642\u0633\u0645', '\u0627\u0644\u062f\u0631\u0627\u0633\u0629', '\u0627\u0644\u0645\u0631\u062d\u0644\u0629', '\u0627\u0644\u0634\u0639\u0628\u0629', '\u0627\u0644\u0645\u0627\u062f\u0629', '\u0627\u0644\u0648\u0642\u062a', '\u0639\u062f\u062f \u0627\u0644\u062d\u0636\u0648\u0631', '\u0639\u062f\u062f \u0627\u0644\u063a\u064a\u0627\u0628', '\u062a\u0641\u0627\u0635\u064a\u0644 \u0627\u0644\u063a\u064a\u0627\u0628', '\u062a\u0627\u0631\u064a\u062e \u0627\u0644\u0645\u062d\u0627\u0636\u0631\u0629'])
    cw.writerows(rows)
    output = io.BytesIO(si.getvalue().encode('utf-8'))
    return send_file(output, mimetype="text/csv", as_attachment=True, download_name="cofarts_attendance_report.csv")

SW_JS = """self.addEventListener('install', function (e) { self.skipWaiting(); });
self.addEventListener('activate', function (e) { e.waitUntil(self.clients.claim()); });
self.addEventListener('fetch', function (e) {
    if (e.request.method !== 'GET' || e.request.mode !== 'navigate') return;
    e.respondWith(fetch(e.request).catch(function () {
        return new Response('<!DOCTYPE html><html lang="ar" dir="rtl"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><body style="font-family:sans-serif;background:#000207;color:#f8fafc;text-align:center;padding:60px 20px"><h2 style="color:#f59e0b">\u0644\u0627 \u064a\u0648\u062c\u062f \u0627\u062a\u0635\u0627\u0644 \u0628\u0627\u0644\u0625\u0646\u062a\u0631\u0646\u062a</h2><p>\u062a\u062d\u062a\u0627\u062c \u0627\u0644\u0645\u0646\u0638\u0648\u0645\u0629 \u0625\u0644\u0649 \u0627\u062a\u0635\u0627\u0644 \u0644\u062d\u0641\u0638 \u0627\u0644\u062d\u0636\u0648\u0631. \u062d\u0627\u0648\u0644 \u0645\u062c\u062f\u062f\u0627\u064b \u0639\u0646\u062f \u0639\u0648\u062f\u0629 \u0627\u0644\u0627\u062a\u0635\u0627\u0644.</p></body></html>',
            { headers: { 'Content-Type': 'text/html; charset=utf-8' } });
    }));
});
"""

@app.route('/manifest.json')
def manifest():
    return jsonify({
        'name': 'UOB', 'short_name': 'UOB', 'lang': 'ar', 'dir': 'rtl',
        'start_url': '/', 'scope': '/', 'display': 'standalone',
        'background_color': '#000207', 'theme_color': '#050a18',
        'icons': [{'src': '/static/icon-192.png', 'sizes': '192x192', 'type': 'image/png', 'purpose': 'any'},
                  {'src': '/static/icon-512.png', 'sizes': '512x512', 'type': 'image/png', 'purpose': 'any'}]})

@app.route('/sw.js')
def service_worker():
    return Response(SW_JS, mimetype='application/javascript', headers={'Service-Worker-Allowed': '/', 'Cache-Control': 'no-cache'})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
