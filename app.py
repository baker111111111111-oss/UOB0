from flask import Flask, render_template_string, request, redirect, url_for

app = Flask(__name__)

SUBJECTS = [
    "التربية الفنية",
    "التصميم",
    "الفنون التشكيلية",
    "الفنون المسرحية",
]

attendance_records = []

HTML_PAGE = """
<!doctype html>
<html lang="ar" dir="rtl">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>نظام الحضور - كلية الفنون الجميلة</title>
  <style>
    body { font-family: Tahoma, Arial, sans-serif; margin: 24px; background: #f5f5f5; }
    .card { max-width: 600px; margin: auto; background: #fff; padding: 20px; border-radius: 8px; }
    label { display: block; margin-top: 12px; font-weight: bold; }
    input, select, button { width: 100%; padding: 10px; margin-top: 6px; box-sizing: border-box; }
    button { background: #1a73e8; color: #fff; border: none; border-radius: 6px; cursor: pointer; margin-top: 16px; }
    table { width: 100%; border-collapse: collapse; margin-top: 24px; }
    th, td { border: 1px solid #ddd; padding: 8px; text-align: right; }
  </style>
</head>
<body>
  <div class="card">
    <h2>تسجيل الحضور</h2>
    <form method="post" action="/add">
      <label for="student_name">اسم الطالب:</label>
      <input id="student_name" name="student_name" type="text" required>

      <label for="subject">اختر المادة:</label>
      <select id="subject" name="subject" required>
        <option value="" disabled selected>-- اختر اسم المادة --</option>
        {% for subj in subjects %}
          <option value="{{ subj }}">{{ subj }}</option>
        {% endfor %}
      </select>

      <button type="submit">حفظ الحضور</button>
    </form>

    <table>
      <thead>
        <tr>
          <th>الاسم</th>
          <th>المادة</th>
        </tr>
      </thead>
      <tbody>
        {% for row in records %}
          <tr>
            <td>{{ row.name }}</td>
            <td>{{ row.subject }}</td>
          </tr>
        {% endfor %}
      </tbody>
    </table>
  </div>
</body>
</html>
"""

@app.route("/", methods=["GET"])
def index():
    return render_template_string(HTML_PAGE, subjects=SUBJECTS, records=attendance_records)

@app.route("/add", methods=["POST"])
def add_attendance():
    name = request.form.get("student_name", "").strip()
    subject = request.form.get("subject", "").strip()
    if name and subject:
        attendance_records.append({"name": name, "subject": subject})
    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
