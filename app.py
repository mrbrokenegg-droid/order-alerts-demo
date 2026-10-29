import os
import csv
from datetime import datetime
import requests
from flask import Flask, request, render_template_string

app = Flask(__name__)
WEBHOOK_URL = os.environ["WEBHOOK_URL"]
FILE = "web_orders.csv"

PAGE = """
<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Place an order</title>
  <style>
    body { font-family: sans-serif; max-width: 420px; margin: 30px auto; padding: 0 16px; }
    input, textarea, button { width: 100%; padding: 10px; margin: 6px 0 14px; box-sizing: border-box; font-size: 16px; }
    button { background: #222; color: #fff; border: 0; border-radius: 6px; }
    .ok { background: #e6f6e6; padding: 12px; border-radius: 6px; }
  </style>
</head>
<body>
  <h2>Place your order</h2>
  {% if done %}<p class="ok">Thanks! Your order was received. We'll contact you soon.</p>{% endif %}
  {% if error %}<p>{{ error }}</p>{% endif %}
  <form method="post">
    <label>Your name</label>
    <input name="name" required maxlength="100">
    <label>Instagram handle or phone</label>
    <input name="contact" required maxlength="100">
    <label>What would you like?</label>
    <input name="item" required maxlength="200">
    <label>Notes (size, color, address...)</label>
    <textarea name="note" rows="3" maxlength="500"></textarea>
    <button type="submit">Send order</button>
  </form>
</body>
</html>
"""

def clean(value, limit):
    value = (value or "").strip()[:limit]
    # stop spreadsheet formula injection
    if value and value[0] in "=+-@":
        value = "'" + value
    return value

def save_order(row):
    new_file = not os.path.exists(FILE)
    with open(FILE, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new_file:
            w.writerow(["time", "name", "contact", "item", "note", "status"])
        w.writerow(row)

def send_alert(name, contact, item, note):
    msg = (
        "🛒 New order\n"
        f"Name: {name}\n"
        f"Contact: {contact}\n"
        f"Item: {item}\n"
        f"Note: {note or '-'}"
    )
    requests.post(
        WEBHOOK_URL,
        json={"content": msg, "allowed_mentions": {"parse": []}},
        timeout=10,
    ).raise_for_status()

@app.route("/", methods=["GET", "POST"])
def order():
    if request.method == "POST":
        name = clean(request.form.get("name"), 100)
        contact = clean(request.form.get("contact"), 100)
        item = clean(request.form.get("item"), 200)
        note = clean(request.form.get("note"), 500)
        if not (name and contact and item):
            return render_template_string(PAGE, error="Please fill in name, contact and item.")
        save_order([datetime.now().strftime("%Y-%m-%d %H:%M"), name, contact, item, note, "New"])
        try:
            send_alert(name, contact, item, note)
        except requests.RequestException:
            print("Alert failed, but the order was saved.")
        return render_template_string(PAGE, done=True)
    return render_template_string(PAGE)

if __name__ == "__main__":
    app.run(port=5000)
