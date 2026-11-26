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
            (HEAD_OFFICIAL_EMAIL.lower(), 'ÙÙØ±Ø± Ø§ÙÙØ³Ù', generate_password_hash(HEAD_PASSWORD), 'head'))
    else:
        print('WARNING: HEAD_PASSWORD is not set; the department head cannot log in.')
    conn.commit()
    conn.close()

init_db()

COLLEGE_DEPARTMENTS = [
    {"name": "ÙØ³Ù Ø§ÙØªØ±Ø¨ÙØ© Ø§ÙÙÙÙØ©", "icon": "ð¨", "desc": "ÙÙØ§Ø±Ø© Ø§ÙÙÙ Ø§ÙØªØ¹Ø¨ÙØ±Ù ÙØ¬ÙØ§ÙÙØ§Øª Ø§ÙØªØ±Ø¨ÙØ© Ø§ÙØ­ÙØ©"},
    {"name": "ÙØ³Ù Ø§ÙÙÙÙÙ Ø§ÙÙÙØ³ÙÙÙØ©", "icon": "ðµ", "desc": "Ø£ØµØ§ÙØ© Ø§ÙÙØºÙØ Ø§ÙØ¥ÙÙØ§Ø¹Ø ÙØ§ÙØªØ°ÙÙ Ø§ÙØµÙØªÙ Ø§ÙØ±ÙÙØ¹"},
    {"name": "ÙØ³Ù Ø§ÙØ®Ø· Ø§ÙØ¹Ø±Ø¨Ù ÙØ§ÙØ²Ø®Ø±ÙØ©", "icon": "âï¸", "desc": "ÙÙØ¯Ø³Ø© Ø§ÙØ­Ø±Ù Ø§ÙØ¹Ø±Ø¨Ù ÙØ¥Ø´Ø±Ø§ÙØ§Øª Ø§ÙØ²Ø®Ø±ÙØ© Ø§ÙØ¥Ø³ÙØ§ÙÙØ©"},
    {"name": "ÙØ³Ù Ø§ÙÙÙÙÙ Ø§ÙØªØ´ÙÙÙÙØ©", "icon": "ð¼ï¸", "desc": "Ø¹Ø±Ø§ÙØ© Ø§ÙØ±Ø³ÙØ Ø§ÙÙØ­ØªØ ÙØ§ÙØªØ´ÙÙÙ Ø§ÙØ¬Ø¯Ø§Ø±Ù Ø§ÙÙØ¹Ø§ØµØ±"},
    {"name": "ÙØ³Ù Ø§ÙÙÙÙÙ Ø§ÙÙØ³Ø±Ø­ÙØ©", "icon": "ð­", "desc": "Ø®Ø´Ø¨Ø© Ø§ÙØ¥Ø¨Ø¯Ø§Ø¹Ø Ø§ÙØªÙØ«ÙÙØ ÙØ§ÙØ¥Ø®Ø±Ø§Ø¬ Ø§ÙÙØ³Ø±Ø­Ù Ø§ÙØ±ÙÙÙ"},
    {"name": "ÙØ³Ù Ø§ÙÙÙÙÙ Ø§ÙØ³ÙÙÙØ§Ø¦ÙØ© ÙØ§ÙØªÙÙØ²ÙÙÙÙØ©", "icon": "ð¬", "desc": "Ø§ÙØ³ÙÙÙØ§ Ø§ÙØªÙØ§Ø¹ÙÙØ©Ø Ø§ÙØ¥Ø®Ø±Ø§Ø¬ Ø§ÙØªÙÙØ²ÙÙÙÙ ÙØ§ÙÙØ³Ø§Ø¦Ø·"},
    {"name": "ÙØ³Ù Ø§ÙØªØµÙÙÙ", "icon": "âï¸", "desc": "ÙÙØ¯Ø³Ø© Ø§ÙÙØ¶Ø§Ø¡ Ø§ÙØ¨ØµØ±ÙØ Ø§ÙØªØµÙÙÙ Ø§ÙØ¯Ø§Ø®ÙÙ ÙØ§ÙØµÙØ§Ø¹Ù"}
]

STAGE_ORDER = ['Ø§ÙÙØ±Ø­ÙØ© Ø§ÙØ£ÙÙÙ', 'Ø§ÙÙØ±Ø­ÙØ© Ø§ÙØ«Ø§ÙÙØ©', 'Ø§ÙÙØ±Ø­ÙØ© Ø§ÙØ«Ø§ÙØ«Ø©', 'Ø§ÙÙØ±Ø­ÙØ© Ø§ÙØ±Ø§Ø¨Ø¹Ø©']
SHIFTS = ('ØµØ¨Ø§Ø­Ù', 'ÙØ³Ø§Ø¦Ù')
FULL_COLLEGE_DATA = {}

def _ar_key(s):
    return s.translate(str.maketrans('Ø£Ø¥Ø¢ÙØ©', 'Ø§Ø§Ø§ÙÙ'))

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
    ws.title = 'Ø§ÙØ·ÙØ¨Ø©'
    ws.sheet_view.rightToLeft = True
    ws.append(['Ø§ÙÙØ³Ù', 'Ø§ÙØ¯Ø±Ø§Ø³Ø©', 'Ø§ÙÙØ±Ø­ÙØ©', 'Ø§ÙØ´Ø¹Ø¨Ø©', 'Ø§ÙØ§Ø³Ù'])
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
    info = wb.create_sheet('ØªØ¹ÙÙÙØ§Øª')
    info.sheet_view.rightToLeft = True
    for line in ['ÙÙ ØµÙ ÙÙ ÙØ±ÙØ© "Ø§ÙØ·ÙØ¨Ø©" ÙÙØ«Ù Ø·Ø§ÙØ¨Ø§Ù ÙØ§Ø­Ø¯Ø§Ù.',
                 'Ø§ÙØ£Ø¹ÙØ¯Ø© Ø§ÙØ®ÙØ³Ø© ÙØ·ÙÙØ¨Ø© ÙØ¨ÙØ°Ø§ Ø§ÙØªØ±ØªÙØ¨: Ø§ÙÙØ³ÙØ Ø§ÙØ¯Ø±Ø§Ø³Ø©Ø Ø§ÙÙØ±Ø­ÙØ©Ø Ø§ÙØ´Ø¹Ø¨Ø©Ø Ø§ÙØ§Ø³Ù.',
                 'Ø§ÙÙØ³Ù ÙØ¬Ø¨ Ø£Ù ÙØ·Ø§Ø¨Ù Ø§Ø³ÙÙ ÙÙ Ø§ÙÙÙØ¸ÙÙØ© ØªÙØ§ÙØ§Ù. Ø§ÙØ¯Ø±Ø§Ø³Ø©: ØµØ¨Ø§Ø­Ù Ø£Ù ÙØ³Ø§Ø¦Ù.',
                 'Ø§ÙÙØ±Ø­ÙØ© ÙØ«Ù: Ø§ÙÙØ±Ø­ÙØ© Ø§ÙØ£ÙÙÙ. Ø§ÙØ´Ø¹Ø¨Ø© ÙØ«Ù: Ø§ÙØ´Ø¹Ø¨Ø© (Ø£).',
                 'Ø§Ø±ÙØ¹ Ø§ÙÙÙÙ ÙÙ ÙÙØ­Ø© Ø§ÙÙÙØ±Ø± > Ø¥Ø¯Ø§Ø±Ø© Ø§ÙØ·ÙØ¨Ø©. Ø§ÙØµÙ Ø§ÙØ£ÙÙ (Ø§ÙØ¹ÙØ§ÙÙÙ) ÙÙØªØ¬Ø§ÙÙ.']:
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
    ws = wb['Ø§ÙØ·ÙØ¨Ø©'] if 'Ø§ÙØ·ÙØ¨Ø©' in wb.sheetnames else wb.worksheets[0]
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
            return "Ø·ÙØ¨ ØºÙØ± ØµØ§ÙØ­Ø Ø£Ø¹Ø¯ ØªØ­ÙÙÙ Ø§ÙØµÙØ­Ø© ÙØ­Ø§ÙÙ ÙØ¬Ø¯Ø¯Ø§Ù", 400

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
    <title>Ø¬Ø§ÙØ¹Ø© Ø¨ØºØ¯Ø§Ø¯ - ÙÙÙØ© Ø§ÙÙÙÙÙ Ø§ÙØ¬ÙÙÙØ©</title>
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
        <h1>ð Ø¬Ø§ÙØ¹Ø© Ø¨ØºØ¯Ø§Ø¯</h1>
        <h2>ÙÙÙØ© Ø§ÙÙÙÙÙ Ø§ÙØ¬ÙÙÙØ©</h2>
    </div>
    <div class="status-bar">
        <div class="sb-item">ð <span id="sb-day">--</span> <span id="sb-date">--</span></div>
        <div class="sb-item">ð <span id="sb-time">--:--:--</span></div>
        <div class="sb-item"><span id="sb-dot" class="sb-dot"></span><span id="sb-conn">Ø¬Ø§Ø±Ù Ø§ÙÙØ­Øµâ¦</span></div>
    </div>
"""

FOOTER_SCRIPTS = """
    <div class="support-footer">
        Ø§ÙØ¯Ø¹Ù Ø§ÙÙÙÙ ÙØ§ÙØªØ·ÙÙØ±: <a href="https://t.me/beko141" target="_blank">ØªÙØ§ØµÙ Ø¹Ø¨Ø± ØªÙÙÙØ¬Ø±Ø§Ù (@beko141)</a>
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
            connEl.textContent = online ? 'ÙØªØµÙ Ø¨Ø§ÙØ®Ø§Ø¯Ù' : 'ØºÙØ± ÙØªØµÙ';
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
                    alert('ÙØ§ ÙÙØ¬Ø¯ Ø§ØªØµØ§Ù Ø¨Ø§ÙØ®Ø§Ø¯ÙØ ÙÙ ÙÙØ±Ø³Ù Ø§ÙØªÙØ±ÙØ±. Ø­Ø§ÙÙ Ø¹ÙØ¯ Ø¹ÙØ¯Ø© Ø§ÙØ§ØªØµØ§Ù.');
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
        {% if error %}<div style="background:rgba(239,68,68,0.2); border-right:5px solid #ef4444; padding:12px; border-radius:10px; margin-bottom:15px; color:#fca5a5;">â ï¸ {{ error }}</div>{% endif %}
        {% if ok %}<div style="background:rgba(16,185,129,0.2); border-right:5px solid #10b981; padding:12px; border-radius:10px; margin-bottom:15px; color:#6ee7b7;">â {{ ok }}</div>{% endif %}
        
        <div style="background: rgba(245,158,11,0.15); border-right: 5px solid var(--accent-gold); padding: 15px; border-radius: 14px; margin-bottom: 20px; font-size: 0.95rem; line-height: 1.7;">
            â¨ <strong>Ø§ÙØ¨ÙØ§Ø¨Ø© Ø§ÙØ³ÙØ§Ø¯ÙØ© Ø§ÙÙÙØ­Ø¯Ø© ÙÙØªØ­ÙÙ Ø§ÙØ£ÙØ§Ø¯ÙÙÙ:</strong><br>
            Ø£ÙÙØ§Ù ÙÙØ±Ø­Ø¨Ø§Ù Ø¨Ø³ÙÙØ± Ø§ÙÙÙ ÙØ§ÙØ¹ÙÙ ÙÙ Ø±Ø­Ø§Ø¨ ÙÙÙØ© Ø§ÙÙÙÙÙ Ø§ÙØ¬ÙÙÙØ©. Ø³Ø¬ÙÙ Ø¯Ø®ÙÙÙ ÙÙÙØªØ§Ø¨Ø¹Ø©.
        </div>

        <form action="/login" method="POST">
            <input type="hidden" name="_csrf" value="{{ csrf_token }}">
            <label style="color:var(--accent-gold); font-weight:bold; display:block; margin-bottom:6px;">Ø§ÙØ¨Ø±ÙØ¯ Ø§ÙØ¥ÙÙØªØ±ÙÙÙ:</label>
            <input type="email" name="user_email" class="input-field" placeholder="name@cofarts.uobaghdad.edu.iq" required>

            <label style="color:var(--accent-gold); font-weight:bold; display:block; margin-bottom:6px;">ÙÙÙØ© Ø§ÙÙØ±ÙØ±:</label>
            <input type="password" name="password" class="input-field" required>

            <button type="submit" class="btn-action">Ø¯Ø®ÙÙ Ø§ÙÙÙØ¸ÙÙØ© Ø§ÙØ£ÙØ§Ø¯ÙÙÙØ©</button>
        </form>
        <p style="text-align:center; margin-top:18px;"><a href="/register" style="color:var(--accent-gold); font-weight:bold; text-decoration:none;">Ø£Ø³ØªØ§Ø° Ø¬Ø¯ÙØ¯Ø Ø¥ÙØ´Ø§Ø¡ Ø­Ø³Ø§Ø¨</a></p>
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
        return redirect(url_for('index', error='ÙØ­Ø§ÙÙØ§Øª ÙØ«ÙØ±Ø©Ø Ø­Ø§ÙÙ Ø¨Ø¹Ø¯ 5 Ø¯ÙØ§Ø¦Ù'))

    conn = sqlite3.connect(DB_NAME)
    row = conn.execute('SELECT name, password_hash, role FROM users WHERE email = ?', (email,)).fetchone()
    conn.close()

    if not row or not check_password_hash(row[1], password):
        LOGIN_FAILS[email] = (fails + 1, time.time())
        return redirect(url_for('index', error='Ø§ÙØ¨Ø±ÙØ¯ Ø§ÙØ¥ÙÙØªØ±ÙÙÙ Ø£Ù ÙÙÙØ© Ø§ÙÙØ±ÙØ± ØºÙØ± ØµØ­ÙØ­Ø©'))

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
            error = 'Ø±ÙØ² Ø§ÙØªØ³Ø¬ÙÙ ØºÙØ± ØµØ­ÙØ­'
        elif not name or '@' not in email or email == HEAD_OFFICIAL_EMAIL.lower():
            error = 'Ø£Ø¯Ø®Ù Ø§ÙØ§Ø³Ù ÙØ¨Ø±ÙØ¯Ø§Ù Ø¥ÙÙØªØ±ÙÙÙØ§Ù ØµØ­ÙØ­Ø§Ù'
        elif len(password) < 8:
            error = 'ÙÙÙØ© Ø§ÙÙØ±ÙØ± ÙØ¬Ø¨ Ø£ÙØ§ ØªÙÙ Ø¹Ù 8 Ø£Ø­Ø±Ù'
        else:
            conn = sqlite3.connect(DB_NAME)
            try:
                conn.execute('INSERT INTO users (email, name, password_hash, role) VALUES (?, ?, ?, ?)',
                             (email, name, generate_password_hash(password), 'doctor'))
                conn.commit()
                return redirect(url_for('index', ok='ØªÙ Ø¥ÙØ´Ø§Ø¡ Ø§ÙØ­Ø³Ø§Ø¨Ø Ø³Ø¬ÙÙ Ø¯Ø®ÙÙÙ Ø§ÙØ¢Ù'))
            except sqlite3.IntegrityError:
                error = 'ÙØ°Ø§ Ø§ÙØ¨Ø±ÙØ¯ ÙØ³Ø¬Ù ÙØ³Ø¨ÙØ§Ù'
            finally:
                conn.close()

    lbl = "color:var(--accent-gold); font-weight:bold; display:block; margin-bottom:6px;"
    html = BASE_CSS_AND_HEAD + """
    <div style="max-width: 550px; margin: 0 auto;">
        {% if error %}<div style="background:rgba(239,68,68,0.2); border-right:5px solid #ef4444; padding:12px; border-radius:10px; margin-bottom:15px; color:#fca5a5;">â ï¸ {{ error }}</div>{% endif %}
        <h3 style="color:var(--accent-gold); text-align:center;">Ø¥ÙØ´Ø§Ø¡ Ø­Ø³Ø§Ø¨ Ø£Ø³ØªØ§Ø°</h3>
        <form method="POST">
            <input type="hidden" name="_csrf" value="{{ csrf_token }}">
            <label style="{{ lbl }}">Ø§ÙØ§Ø³Ù Ø§ÙÙØ§ÙÙ / Ø§ÙÙÙØ¨ Ø§ÙØ¹ÙÙÙ:</label>
            <input type="text" name="user_name" class="input-field" required>
            <label style="{{ lbl }}">Ø§ÙØ¨Ø±ÙØ¯ Ø§ÙØ¥ÙÙØªØ±ÙÙÙ:</label>
            <input type="email" name="user_email" class="input-field" required>
            <label style="{{ lbl }}">ÙÙÙØ© Ø§ÙÙØ±ÙØ± (8 Ø£Ø­Ø±Ù Ø¹ÙÙ Ø§ÙØ£ÙÙ):</label>
            <input type="password" name="password" class="input-field" minlength="8" required>
            <label style="{{ lbl }}">Ø±ÙØ² Ø§ÙØªØ³Ø¬ÙÙ (ÙØ¹Ø·ÙÙ ÙÙ ÙÙØ±Ø± Ø§ÙÙØ³Ù):</label>
            <input type="text" name="code" class="input-field" required>
            <button type="submit" class="btn-action">Ø¥ÙØ´Ø§Ø¡ Ø§ÙØ­Ø³Ø§Ø¨</button>
        </form>
        <p style="text-align:center; margin-top:18px;"><a href="/" style="color:var(--accent-gold); font-weight:bold; text-decoration:none;">â Ø§ÙØ¹ÙØ¯Ø© ÙØªØ³Ø¬ÙÙ Ø§ÙØ¯Ø®ÙÙ</a></p>
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
        <div>ÙØ±Ø­Ø¨Ø§Ù Ø¨Ù: <strong style="color:var(--accent-gold);">{{ user_name }}</strong></div>
        <a href="/logout" class="logout-link">ØªØ³Ø¬ÙÙ Ø§ÙØ®Ø±ÙØ¬</a>
    </div>
    <h3 style="text-align:center; color:var(--accent-gold); margin-bottom:20px;">Ø§Ø®ØªØ± Ø§ÙÙØ³Ù Ø§ÙØ£ÙØ§Ø¯ÙÙÙ</h3>
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
    dept = request.args.get('dept', 'ÙØ³Ù Ø§ÙØªØ±Ø¨ÙØ© Ø§ÙÙÙÙØ©')
    shift = request.args.get('shift', 'ØµØ¨Ø§Ø­Ù')
    
    dept_data = FULL_COLLEGE_DATA.get(dept, {})
    shifts = list(dept_data.keys())
    stages = list(dept_data.get(shift, {}).keys())
    
    html = BASE_CSS_AND_HEAD + """
    <div class="nav-bar">
        <div>Ø§ÙÙØ³Ù: <strong style="color:var(--accent-gold);">{{ dept }}</strong></div>
        <div>
            <a href="/departments" style="color:var(--accent-green); text-decoration:none; margin-left:15px; font-weight:bold;">â Ø§ÙØ£ÙØ³Ø§Ù</a>
            <a href="/logout" class="logout-link">Ø®Ø±ÙØ¬</a>
        </div>
    </div>

    <div style="background:rgba(14,24,46,0.9); padding:25px; border-radius:20px; border:1px solid rgba(255,255,255,0.15);">
        <h3 style="color:var(--accent-gold); margin-top:0;">1. Ø§Ø®ØªØ± ÙÙØ¹ Ø§ÙØ¯Ø±Ø§Ø³Ø©:</h3>
        <div style="margin-bottom:25px;">
            {% for s in shifts %}
            <a href="/select_options?dept={{ dept }}&shift={{ s }}" class="pill-btn {% if s == shift %}active{% endif %}">Ø§ÙØ¯Ø±Ø§Ø³Ø© {{ s }}Ø©</a>
            {% endfor %}
        </div>

        <h3 style="color:var(--accent-gold);">2. Ø§Ø®ØªØ± Ø§ÙÙØ±Ø­ÙØ© ÙØ§ÙØ´Ø¹Ø¨Ø© ÙØ±ØµØ¯ Ø§ÙØ­Ø¶ÙØ±:</h3>
        {% if not stages %}<p style="color:var(--text-muted);">ÙØ§ ØªÙØ¬Ø¯ Ø£Ø³ÙØ§Ø¡ Ø·ÙØ¨Ø© ÙÙØ°Ø§ Ø§ÙÙØ³Ù Ø¨Ø¹Ø¯. ÙØ¶ÙÙÙØ§ ÙÙØ±Ø± Ø§ÙÙØ³Ù ÙÙ Â«Ø¥Ø¯Ø§Ø±Ø© Ø§ÙØ·ÙØ¨Ø©Â».</p>{% endif %}
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
        subject = ' '.join((request.form.get('subject') or 'ÙØ§Ø¯Ø© Ø¯Ø±Ø§Ø³ÙØ©').split())
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
            status = request.form.get(f'status_{idx}', 'Ø­Ø§Ø¶Ø±')
            if status == 'Ø­Ø§Ø¶Ø±':
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
                  present, absent, " | ".join(details_list) if details_list else "ÙØ§ ÙÙØ¬Ø¯ ØºÙØ§Ø¨", lecture_date.isoformat()))
            conn.commit()
        except sqlite3.IntegrityError:
            return redirect(url_for('attendance', dept=dept, shift=shift, stage=stage, section=section,
                                    error='Ø³Ø¨Ù ØªØ³Ø¬ÙÙ Ø­Ø¶ÙØ± ÙØ°Ù Ø§ÙÙØ§Ø¯Ø© ÙÙØ°Ù Ø§ÙØ´Ø¹Ø¨Ø© ÙÙ ÙØ°Ø§ Ø§ÙØªØ§Ø±ÙØ®'))
        finally:
            conn.close()
        
        return render_template_string(BASE_CSS_AND_HEAD + """
        <div style="text-align:center; padding:30px;">
            <div style="font-size:4rem;">â</div>
            <h2 style="color:var(--accent-green);">ØªÙ Ø¥Ø±Ø³Ø§Ù ÙØ­ÙØ¸ Ø³Ø¬Ù Ø§ÙØ­Ø¶ÙØ± Ø¨ÙØ¬Ø§Ø­!</h2>
            <p style="color:var(--text-muted);">Ø§ÙØ­Ø¶ÙØ±: {{ present }} | Ø§ÙØºÙØ§Ø¨/Ø§ÙØ¥Ø¬Ø§Ø²Ø§Øª: {{ absent }}</p>
            <br>
            <a href="/departments" class="btn-action" style="text-decoration:none; display:inline-block; width:auto;">Ø§ÙØ¹ÙØ¯Ø© ÙÙØ£ÙØ³Ø§Ù</a>
        </div>
        """ + FOOTER_SCRIPTS, logo_b64=get_logo_base64(), present=present, absent=absent)

    html = BASE_CSS_AND_HEAD + """
    <div class="nav-bar">
        <div><strong>{{ dept }}</strong> - {{ shift }} - {{ stage }} ({{ section }})</div>
        <a href="/select_options?dept={{ dept }}&shift={{ shift }}" style="color:var(--accent-gold); text-decoration:none; font-weight:bold;">â Ø±Ø¬ÙØ¹</a>
    </div>

    <form method="POST">
        <input type="hidden" name="_csrf" value="{{ csrf_token }}">
        {% if error %}<div style="background:rgba(239,68,68,0.2); border-right:5px solid #ef4444; padding:12px; border-radius:10px; margin-bottom:15px; color:#fca5a5;">â ï¸ {{ error }}</div>{% endif %}
        <label style="color:var(--accent-gold); font-weight:bold; display:block; margin-bottom:6px;">ØªØ§Ø±ÙØ® Ø§ÙÙØ­Ø§Ø¶Ø±Ø©:</label>
        <input type="date" name="lecture_date" class="input-field" value="{{ today }}" max="{{ today }}" required>
        <label style="color:var(--accent-gold); font-weight:bold; display:block; margin-bottom:6px;">Ø§Ø³Ù Ø§ÙÙØ§Ø¯Ø© Ø§ÙØ¯Ø±Ø§Ø³ÙØ©:</label>
        <input type="text" name="subject" class="input-field" placeholder="Ø§ÙØªØ¨ Ø§Ø³Ù Ø§ÙÙØ§Ø¯Ø© ÙÙØ§..." required>

        <table>
            <thead>
                <tr>
                    <th style="width:40px;">Øª</th>
                    <th>Ø§Ø³Ù Ø§ÙØ·Ø§ÙØ¨</th>
                    <th style="width:120px;">Ø§ÙØ­Ø§ÙØ©</th>
                </tr>
            </thead>
            <tbody>
                {% for st in students %}
                <tr>
                    <td>{{ loop.index }}</td>
                    <td style="font-weight:bold;">{{ st }}</td>
                    <td>
                        <select name="status_{{ loop.index0 }}" style="padding:8px; border-radius:8px; background:#050a18; color:#fff; border:1px solid #334155; font-family:'Cairo'; width:100%;">
                            <option value="Ø­Ø§Ø¶Ø±">Ø­Ø§Ø¶Ø± â</option>
                            <option value="ØºØ§Ø¦Ø¨">ØºØ§Ø¦Ø¨ â</option>
                            <option value="Ø¥Ø¬Ø§Ø²Ø©">Ø¥Ø¬Ø§Ø²Ø© ð</option>
                        </select>
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
        <br>
        <button type="submit" class="btn-action">Ø§Ø¹ØªÙØ§Ø¯ ÙØ¥Ø±Ø³Ø§Ù Ø§ÙØªÙØ±ÙØ± ÙÙÙØ±Ø± Ø§ÙÙØ³Ù</button>
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
        <div>ÙÙØ­Ø© ÙÙØ±Ø± Ø§ÙÙØ³Ù: <strong style="color:var(--accent-green);">{{ user_name }}</strong></div>
        <div>
            <a href="/admin/students" class="chip-btn" style="background:var(--accent-blue);">ð¥ Ø¥Ø¯Ø§Ø±Ø© Ø§ÙØ·ÙØ¨Ø©</a>
            <a href="/admin/accounts" class="chip-btn" style="background:#8b5cf6;">ð Ø­Ø³Ø§Ø¨Ø§Øª Ø§ÙØ£Ø³Ø§ØªØ°Ø©</a>
            <a href="/export_csv{{ '?' + qs if qs }}" class="chip-btn">ð¥ ØªØµØ¯ÙØ± CSV</a>
            <a href="/logout" class="logout-link">Ø®Ø±ÙØ¬</a>
        </div>
    </div>

    <div class="stat-grid">
        <div class="stat-card"><div class="num" style="color:var(--accent-gold);">{{ reports|length }}</div><div class="lbl">ØªÙØ±ÙØ± Ø­Ø¶ÙØ±</div></div>
        <div class="stat-card"><div class="num" style="color:#10b981;">{{ present }}</div><div class="lbl">Ø¥Ø¬ÙØ§ÙÙ Ø§ÙØ­Ø¶ÙØ±</div></div>
        <div class="stat-card"><div class="num" style="color:#ef4444;">{{ absent }}</div><div class="lbl">Ø§ÙØºÙØ§Ø¨ ÙØ§ÙØ¥Ø¬Ø§Ø²Ø§Øª</div></div>
        <div class="stat-card"><div class="ring" style="--p: {{ rate }};"><span>{{ rate }}%</span></div><div class="lbl">ÙØ³Ø¨Ø© Ø§ÙØ­Ø¶ÙØ±</div></div>
    </div>

    {% if bars %}
    <div style="background:rgba(14,24,46,0.9); padding:18px 22px; border-radius:20px; border:1px solid rgba(255,255,255,0.12); margin-bottom:20px;">
        <strong style="color:var(--accent-gold);">ÙØ³Ø¨Ø© Ø§ÙØ­Ø¶ÙØ± Ø­Ø³Ø¨ Ø§ÙÙØ³Ù</strong>
        {% for n, pct, a, b in bars %}
        <div class="bar-row"><div style="display:flex; justify-content:space-between;"><span>{{ n }}</span><span>{{ pct }}%</span></div>
        <div class="bar-track"><div class="bar-fill" style="width: {{ pct }}%;"></div></div></div>
        {% endfor %}
    </div>
    {% endif %}

    <form method="GET" class="filter-bar">
        <select name="dept" class="input-field">
            <option value="">ÙÙ Ø§ÙØ£ÙØ³Ø§Ù</option>
            {% for d in depts %}<option value="{{ d.name }}" {% if d.name == f.dept %}selected{% endif %}>{{ d.name }}</option>{% endfor %}
        </select>
        <input type="text" name="q" class="input-field" placeholder="Ø¨Ø­Ø« Ø¨Ø§ÙÙØ§Ø¯Ø© Ø£Ù Ø§ÙØ£Ø³ØªØ§Ø°" value="{{ f.q }}">
        <input type="date" name="d1" class="input-field" value="{{ f.d1 }}" title="ÙÙ ØªØ§Ø±ÙØ®">
        <input type="date" name="d2" class="input-field" value="{{ f.d2 }}" title="Ø¥ÙÙ ØªØ§Ø±ÙØ®">
        <button type="submit" class="btn-action" style="padding:12px;">ØªØµÙÙØ©</button>
    </form>

    <div style="overflow-x:auto;">
        <table>
            <thead><tr>
                <th>ØªØ§Ø±ÙØ® Ø§ÙÙØ­Ø§Ø¶Ø±Ø©</th><th>Ø§ÙØ£Ø³ØªØ§Ø°</th><th>Ø§ÙÙØ³Ù ÙØ§ÙÙØ±Ø­ÙØ©</th><th>Ø§ÙÙØ§Ø¯Ø©</th><th>Ø§ÙØ­Ø¶ÙØ± / Ø§ÙØºÙØ§Ø¨</th><th>Ø§ÙØ·ÙØ¨Ø© Ø§ÙØºØ§Ø¦Ø¨ÙÙ</th><th></th>
            </tr></thead>
            <tbody>
                {% for r in reports %}
                <tr>
                    <td>{{ r[11] or 'â' }}<br><span style="font-size:0.75rem; color:var(--text-muted);">Ø£ÙØ±Ø³Ù {{ r[7] }}</span></td>
                    <td>{{ r[1] }}</td>
                    <td>{{ r[2] }} ({{ r[3] }} - {{ r[4] }} {{ r[5] }})</td>
                    <td>{{ r[6] }}</td>
                    <td><span style="color:#10b981;">{{ r[8] }} Ø­Ø§Ø¶Ø±</span> / <span style="color:#ef4444;">{{ r[9] }} ØºØ§Ø¦Ø¨</span></td>
                    <td style="font-size:0.85rem; color:#fca5a5;">{{ r[10] }}</td>
                    <td><form method="POST" action="/report/{{ r[0] }}/delete" style="margin:0;" onsubmit="return confirm('Ø­Ø°Ù ÙØ°Ø§ Ø§ÙØ³Ø¬Ù ÙÙØ§Ø¦ÙØ§ÙØ');">
                        <input type="hidden" name="_csrf" value="{{ csrf_token }}"><button class="del-btn" title="Ø­Ø°Ù">ð</button></form></td>
                </tr>
                {% else %}
                <tr><td colspan="7" style="text-align:center; color:var(--text-muted);">ÙØ§ ØªÙØ¬Ø¯ Ø³Ø¬ÙØ§Øª ÙØ·Ø§Ø¨ÙØ©.</td></tr>
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
            err = 'Ø§Ø®ØªØ± ÙÙÙ Excel Ø¨ØµÙØºØ© xlsx'
        else:
            try:
                added, skipped = import_students_xlsx(fl.stream, replace=bool(request.form.get('replace')))
                msg = f'ØªÙ Ø§Ø³ØªÙØ±Ø§Ø¯ {added} Ø·Ø§ÙØ¨Ø§Ù' + (f' ÙØªØ¬Ø§ÙÙ {skipped} ØµÙØ§Ù ØºÙØ± ØµØ§ÙØ­' if skipped else '')
            except Exception:
                err = 'ØªØ¹Ø°ÙØ± ÙØ±Ø§Ø¡Ø© Ø§ÙÙÙÙ. ØªØ£ÙØ¯ ÙÙ Ø§ÙØ£Ø¹ÙØ¯Ø©: Ø§ÙÙØ³ÙØ Ø§ÙØ¯Ø±Ø§Ø³Ø©Ø Ø§ÙÙØ±Ø­ÙØ©Ø Ø§ÙØ´Ø¹Ø¨Ø©Ø Ø§ÙØ§Ø³Ù'
    counts = []
    for d in COLLEGE_DEPARTMENTS:
        n = sum(len(v) for sh in FULL_COLLEGE_DATA.get(d['name'], {}).values() for st in sh.values() for v in st.values())
        counts.append((d['icon'], d['name'], n))
    html = BASE_CSS_AND_HEAD + """
    <div class="nav-bar">
        <div>Ø¥Ø¯Ø§Ø±Ø© Ø§ÙØ·ÙØ¨Ø©</div>
        <div><a href="/head_dashboard" class="chip-btn" style="background:var(--accent-blue);">â Ø§ÙÙÙØ­Ø©</a><a href="/logout" class="logout-link">Ø®Ø±ÙØ¬</a></div>
    </div>
    {% if err %}<div style="background:rgba(239,68,68,0.2); border-right:5px solid #ef4444; padding:12px; border-radius:10px; margin-bottom:15px; color:#fca5a5;">â ï¸ {{ err }}</div>{% endif %}
    {% if msg %}<div style="background:rgba(16,185,129,0.2); border-right:5px solid #10b981; padding:12px; border-radius:10px; margin-bottom:15px; color:#6ee7b7;">â {{ msg }}</div>{% endif %}
    <div class="stat-grid">
        {% for icon, name, n in counts %}<div class="stat-card"><div style="font-size:1.8rem;">{{ icon }}</div><div class="num" style="color:var(--accent-gold);">{{ n }}</div><div class="lbl">{{ name }}</div></div>{% endfor %}
    </div>
    <div style="background:rgba(14,24,46,0.9); padding:22px; border-radius:20px; border:1px solid rgba(255,255,255,0.12);">
        <h3 style="color:var(--accent-gold); margin-top:0;">Ø§Ø³ØªÙØ±Ø§Ø¯ Ø§ÙØ£Ø³ÙØ§Ø¡ ÙÙ Excel</h3>
        <p style="color:var(--text-muted); line-height:1.8;">ÙØ²ÙÙ Ø§ÙÙÙÙ Ø§ÙØ­Ø§ÙÙØ Ø¹Ø¯ÙÙÙØ Ø«Ù Ø§Ø±ÙØ¹Ù. Ø§ÙØ£Ø¹ÙØ¯Ø©: Ø§ÙÙØ³ÙØ Ø§ÙØ¯Ø±Ø§Ø³Ø©Ø Ø§ÙÙØ±Ø­ÙØ©Ø Ø§ÙØ´Ø¹Ø¨Ø©Ø Ø§ÙØ§Ø³Ù. ØªÙØ±ØªÙÙØ¨ Ø§ÙØ£Ø³ÙØ§Ø¡ Ø£Ø¨Ø¬Ø¯ÙØ§Ù ØªÙÙØ§Ø¦ÙØ§Ù.</p>
        <a href="/admin/students/export" class="chip-btn">ð¥ ØªÙØ²ÙÙ Ø§ÙØ£Ø³ÙØ§Ø¡ Ø§ÙØ­Ø§ÙÙØ© (Excel)</a>
        <form method="POST" enctype="multipart/form-data" style="margin-top:18px;">
            <input type="hidden" name="_csrf" value="{{ csrf_token }}">
            <input type="file" name="file" accept=".xlsx" class="input-field" required>
            <label style="display:block; margin-bottom:16px;"><input type="checkbox" name="replace" value="1"> Ø§Ø³ØªØ¨Ø¯Ø§Ù ÙÙ Ø§ÙØ£Ø³ÙØ§Ø¡ Ø§ÙØ­Ø§ÙÙØ© Ø¨ÙØ­ØªÙÙ Ø§ÙÙÙÙ</label>
            <button type="submit" class="btn-action">Ø±ÙØ¹ ÙØ§Ø³ØªÙØ±Ø§Ø¯</button>
        </form>
    </div>
    """ + FOOTER_SCRIPTS
    return render_template_string(html, logo_b64=get_logo_base64(), msg=msg, err=err, counts=counts)

PW_CHARS = 'ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnpqrstuvwxyz23456789'
EMAIL_RE = re.compile(r'[^\s,Ø;]+@[^\s,Ø;]+')

def build_accounts_xlsx(rows):
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment
    wb = Workbook()
    ws = wb.active
    ws.title = 'Ø§ÙØ­Ø³Ø§Ø¨Ø§Øª'
    ws.sheet_view.rightToLeft = True
    ws.append(['Ø§ÙØ§Ø³Ù', 'Ø§ÙØ¨Ø±ÙØ¯ Ø§ÙØ¥ÙÙØªØ±ÙÙÙ', 'ÙÙÙØ© Ø§ÙÙØ±ÙØ±', 'Ø§ÙØ­Ø§ÙØ©'])
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
    ws.append(['ØªÙØ¨ÙÙ: ÙÙÙØ§Øª Ø§ÙÙØ±ÙØ± ÙØ§ ØªÙØ­ÙØ¸ ÙÙ Ø§ÙÙÙØ¸ÙÙØ© ÙÙØ§ ÙÙÙÙ Ø§Ø³ØªØ±Ø¬Ø§Ø¹ÙØ§. Ø³ÙÙÙ ÙÙ Ø£Ø³ØªØ§Ø° Ø¨ÙØ§ÙØ§ØªÙ Ø«Ù Ø§Ø­Ø°Ù ÙØ°Ø§ Ø§ÙÙÙÙ.'])
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
            name = re.sub(r'[,Ø;\t]+', ' ', line.replace(m.group(0), ' ') if m else line).strip()
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
            out.append((name, email, pw, 'ÙÙÙØ© ÙØ±ÙØ± Ø¬Ø¯ÙØ¯Ø©' if ex else 'Ø­Ø³Ø§Ø¨ Ø¬Ø¯ÙØ¯'))
        if out:
            return send_file(build_accounts_xlsx(out), as_attachment=True, download_name='accounts.xlsx',
                             mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        err = 'ÙÙ ÙÙÙØ´Ø£ Ø£Ù Ø­Ø³Ø§Ø¨. Ø§ÙØªØ¨ ÙÙ ÙÙ Ø³Ø·Ø±: Ø§Ø³Ù Ø§ÙØ£Ø³ØªØ§Ø° Ø«Ù Ø¨Ø±ÙØ¯Ù Ø§ÙØ¥ÙÙØªØ±ÙÙÙ.'
    conn = sqlite3.connect(DB_NAME)
    docs = conn.execute("SELECT name, email FROM users WHERE role = 'doctor' ORDER BY name").fetchall()
    conn.close()
    html = BASE_CSS_AND_HEAD + """
    <div class="nav-bar">
        <div>Ø­Ø³Ø§Ø¨Ø§Øª Ø§ÙØ£Ø³Ø§ØªØ°Ø©</div>
        <div><a href="/head_dashboard" class="chip-btn" style="background:var(--accent-blue);">â Ø§ÙÙÙØ­Ø©</a><a href="/logout" class="logout-link">Ø®Ø±ÙØ¬</a></div>
    </div>
    {% if err %}<div style="background:rgba(239,68,68,0.2); border-right:5px solid #ef4444; padding:12px; border-radius:10px; margin-bottom:15px; color:#fca5a5;">â ï¸ {{ err }}</div>{% endif %}
    <div style="background:rgba(14,24,46,0.9); padding:22px; border-radius:20px; border:1px solid rgba(255,255,255,0.12); margin-bottom:20px;">
        <h3 style="color:var(--accent-gold); margin-top:0;">Ø¥ÙØ´Ø§Ø¡ Ø­Ø³Ø§Ø¨Ø§Øª Ø¬Ø§ÙØ²Ø©</h3>
        <p style="color:var(--text-muted); line-height:1.8;">Ø§ÙØªØ¨ ÙÙ ÙÙ Ø³Ø·Ø± Ø§Ø³Ù Ø§ÙØ£Ø³ØªØ§Ø° ÙØ¨Ø±ÙØ¯Ù. ØªÙÙØ´Ø£ ÙÙÙ Ø£Ø³ØªØ§Ø° ÙÙÙØ© ÙØ±ÙØ± Ø¹Ø´ÙØ§Ø¦ÙØ©Ø ÙØªÙØ²Ù ÙÙ ÙÙ ÙÙÙ Excel ÙØ±Ø© ÙØ§Ø­Ø¯Ø© ÙÙØ·. Ø¥Ù ÙØªØ¨Øª Ø¨Ø±ÙØ¯Ø§Ù ÙÙØ¬ÙØ¯Ø§Ù ØªÙØ¹Ø§Ø¯ ÙÙÙØ© ÙØ±ÙØ±Ù.</p>
        <form method="POST">
            <input type="hidden" name="_csrf" value="{{ csrf_token }}">
            <textarea name="lines" class="input-field" rows="7" placeholder="Ø¯. Ø£Ø­ÙØ¯ Ø¹ÙÙØ ahmed@cofarts.uobaghdad.edu.iq" required></textarea>
            <button type="submit" class="btn-action">Ø¥ÙØ´Ø§Ø¡ ÙØªÙØ²ÙÙ ÙÙÙ Ø§ÙØ­Ø³Ø§Ø¨Ø§Øª</button>
        </form>
    </div>
    <h3 style="color:var(--accent-gold);">Ø§ÙØ­Ø³Ø§Ø¨Ø§Øª Ø§ÙØ­Ø§ÙÙØ© ({{ docs|length }})</h3>
    <div style="overflow-x:auto;"><table><thead><tr><th>Ø§ÙØ§Ø³Ù</th><th>Ø§ÙØ¨Ø±ÙØ¯</th></tr></thead><tbody>
        {% for n, e in docs %}<tr><td>{{ n }}</td><td style="direction:ltr; text-align:right;">{{ e }}</td></tr>{% else %}<tr><td colspan="2" style="text-align:center; color:var(--text-muted);">ÙØ§ ØªÙØ¬Ø¯ Ø­Ø³Ø§Ø¨Ø§Øª Ø¨Ø¹Ø¯.</td></tr>{% endfor %}
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
    cw.writerow(['ID', 'Ø§ÙØ£Ø³ØªØ§Ø°', 'Ø§ÙÙØ³Ù', 'Ø§ÙØ¯Ø±Ø§Ø³Ø©', 'Ø§ÙÙØ±Ø­ÙØ©', 'Ø§ÙØ´Ø¹Ø¨Ø©', 'Ø§ÙÙØ§Ø¯Ø©', 'Ø§ÙÙÙØª', 'Ø¹Ø¯Ø¯ Ø§ÙØ­Ø¶ÙØ±', 'Ø¹Ø¯Ø¯ Ø§ÙØºÙØ§Ø¨', 'ØªÙØ§ØµÙÙ Ø§ÙØºÙØ§Ø¨', 'ØªØ§Ø±ÙØ® Ø§ÙÙØ­Ø§Ø¶Ø±Ø©'])
    cw.writerows(rows)
    output = io.BytesIO(si.getvalue().encode('utf-8'))
    return send_file(output, mimetype="text/csv", as_attachment=True, download_name="cofarts_attendance_report.csv")

SW_JS = """self.addEventListener('install', function (e) { self.skipWaiting(); });
self.addEventListener('activate', function (e) { e.waitUntil(self.clients.claim()); });
self.addEventListener('fetch', function (e) {
    if (e.request.method !== 'GET' || e.request.mode !== 'navigate') return;
    e.respondWith(fetch(e.request).catch(function () {
        return new Response('<!DOCTYPE html><html lang="ar" dir="rtl"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><body style="font-family:sans-serif;background:#000207;color:#f8fafc;text-align:center;padding:60px 20px"><h2 style="color:#f59e0b">ÙØ§ ÙÙØ¬Ø¯ Ø§ØªØµØ§Ù Ø¨Ø§ÙØ¥ÙØªØ±ÙØª</h2><p>ØªØ­ØªØ§Ø¬ Ø§ÙÙÙØ¸ÙÙØ© Ø¥ÙÙ Ø§ØªØµØ§Ù ÙØ­ÙØ¸ Ø§ÙØ­Ø¶ÙØ±. Ø­Ø§ÙÙ ÙØ¬Ø¯Ø¯Ø§Ù Ø¹ÙØ¯ Ø¹ÙØ¯Ø© Ø§ÙØ§ØªØµØ§Ù.</p></body></html>',
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
