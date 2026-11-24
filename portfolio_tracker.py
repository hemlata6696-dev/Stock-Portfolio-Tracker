"""
Stock Portfolio Tracker (Flask)

Run:   pip install flask
       python portfolio_tracker.py
Open:  http://127.0.0.1:5000

Prices are typed in by hand (starting from DEFAULT_PRICES below).
Data is saved in portfolio_data.json next to this file.
For local, single-user use only (no login).
"""
import csv
import io
import json
import math
import os
import re
import tempfile
import threading
from datetime import datetime

from flask import (Flask, Response, flash, redirect, render_template_string,
                   request, url_for)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", os.urandom(16).hex())

# Starting prices. You can add or change stocks from the website too.
DEFAULT_PRICES = {"AAPL": 180, "TSLA": 250, "MSFT": 420, "GOOGL": 150, "AMZN": 185}

DATA_FILE = os.environ.get(
    "PORTFOLIO_DATA_FILE",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "portfolio_data.json"),
)
NAME_RE = re.compile(r"^[A-Z0-9][A-Z0-9.\-]{0,9}$")
MAX_SNAPSHOTS = 200
lock = threading.Lock()


# ---------- saving and loading ----------
def fresh_data():
    return {"prices": dict(DEFAULT_PRICES), "holdings": [], "snapshots": [], "next_id": 1}


def load():
    if not os.path.exists(DATA_FILE):
        return fresh_data()
    try:
        with open(DATA_FILE, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        # Keep the broken file instead of overwriting it
        os.replace(DATA_FILE, DATA_FILE + ".broken")
        return fresh_data()


def save(data):
    folder = os.path.dirname(DATA_FILE)
    fd, tmp = tempfile.mkstemp(dir=folder, suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, DATA_FILE)  # safe write: never leaves a half-written file


# ---------- maths ----------
def summarize(data):
    rows, invested, value = [], 0.0, 0.0
    for h in data["holdings"]:
        price = data["prices"].get(h["stock"], h["buy_price"])
        cost = h["qty"] * h["buy_price"]
        now = h["qty"] * price
        rows.append({
            "id": h["id"], "stock": h["stock"], "qty": h["qty"],
            "buy": h["buy_price"], "price": price, "cost": cost, "value": now,
            "pl": now - cost, "pct": (now - cost) / cost * 100 if cost else 0.0,
        })
        invested += cost
        value += now
    pl = value - invested
    pct = pl / invested * 100 if invested else 0.0
    return rows, {"invested": invested, "value": value, "pl": pl, "pct": pct}


def take_snapshot(data):
    """Record total value so the page can show change over time."""
    _, t = summarize(data)
    if not data["holdings"]:
        return
    snaps = data["snapshots"]
    if snaps and snaps[-1]["invested"] == round(t["invested"], 2) \
            and snaps[-1]["value"] == round(t["value"], 2):
        return  # nothing changed
    snaps.append({
        "time": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "invested": round(t["invested"], 2),
        "value": round(t["value"], 2),
    })
    del snaps[:-MAX_SNAPSHOTS]


def positive_number(text):
    try:
        n = float(text)
    except (TypeError, ValueError):
        return None
    return n if math.isfinite(n) and n > 0 else None


# ---------- display helpers ----------
@app.template_filter("money")
def money(x):
    return "${:,.2f}".format(x)


@app.template_filter("signed")
def signed(x):
    return ("+" if x >= 0 else "-") + "${:,.2f}".format(abs(x))


@app.template_filter("pct")
def pct(x):
    return "{:+.2f}%".format(x)


@app.template_filter("num")
def num(x):
    return "{:,.4g}".format(x)


PAGE = """
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Stock Portfolio Tracker</title>
<style>
  :root { --bg:#fafafa; --card:#fff; --text:#1a1a1a; --muted:#666; --line:#e3e3e3;
          --good:#0a7d33; --bad:#b00020; --accent:#2457d6; }
  @media (prefers-color-scheme: dark) {
    :root { --bg:#141414; --card:#1e1e1e; --text:#eee; --muted:#9a9a9a; --line:#333;
            --good:#4cd47f; --bad:#ff6b7f; --accent:#7aa2ff; } }
  * { box-sizing: border-box; }
  body { font-family: system-ui, sans-serif; background: var(--bg); color: var(--text);
         max-width: 860px; margin: 0 auto; padding: 1rem; line-height: 1.4; }
  h1 { margin-bottom: .2rem; } h2 { margin: 0 0 .6rem; font-size: 1.1rem; }
  .sub { color: var(--muted); margin-top: 0; }
  .card { background: var(--card); border: 1px solid var(--line); border-radius: 10px;
          padding: 1rem; margin-bottom: 1rem; }
  .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: .8rem; }
  .stat small { color: var(--muted); display: block; }
  .stat b { font-size: 1.3rem; }
  .good { color: var(--good); } .bad { color: var(--bad); }
  .wrap { overflow-x: auto; }
  table { border-collapse: collapse; width: 100%; font-size: .95rem; }
  th, td { padding: 7px 8px; text-align: right; border-bottom: 1px solid var(--line); white-space: nowrap; }
  th:first-child, td:first-child { text-align: left; }
  input { padding: 8px; border: 1px solid var(--line); border-radius: 6px; background: var(--bg);
          color: var(--text); width: 140px; max-width: 100%; }
  button { padding: 8px 12px; border: 0; border-radius: 6px; background: var(--accent);
           color: #fff; cursor: pointer; }
  button.link { background: none; color: var(--bad); padding: 2px 6px; }
  .row { display: flex; gap: .5rem; flex-wrap: wrap; align-items: center; }
  .msg { padding: 8px 12px; border-radius: 6px; margin-bottom: .6rem; background: #fde7ea; color: #7a0014; }
  .msg.ok { background: #e3f6ea; color: #0a4d20; }
  a.btn { display: inline-block; padding: 8px 12px; border-radius: 6px; background: var(--accent);
          color: #fff; text-decoration: none; margin-right: .4rem; }
  .empty { color: var(--muted); }
</style>
</head>
<body>
<h1>Stock Portfolio Tracker</h1>
<p class="sub">Prices are entered by hand. Update them when you want a fresh profit/loss number.</p>

{% for cat, m in get_flashed_messages(with_categories=true) %}
  <div class="msg {{ 'ok' if cat == 'ok' else '' }}">{{ m }}</div>
{% endfor %}

<div class="card stats">
  <div class="stat"><small>Total invested</small><b>{{ t.invested|money }}</b></div>
  <div class="stat"><small>Current value</small><b>{{ t.value|money }}</b></div>
  <div class="stat"><small>Profit / Loss</small>
    <b class="{{ 'good' if t.pl >= 0 else 'bad' }}">{{ t.pl|signed }} ({{ t.pct|pct }})</b></div>
</div>

<div class="card">
  <h2>Your holdings</h2>
  {% if rows %}
  <div class="wrap"><table>
    <tr><th>Stock</th><th>Qty</th><th>Buy price</th><th>Price now</th><th>Cost</th><th>Value</th><th>P/L</th><th></th></tr>
    {% for r in rows %}
    <tr>
      <td>{{ r.stock }}</td><td>{{ r.qty|num }}</td><td>{{ r.buy|money }}</td><td>{{ r.price|money }}</td>
      <td>{{ r.cost|money }}</td><td>{{ r.value|money }}</td>
      <td class="{{ 'good' if r.pl >= 0 else 'bad' }}">{{ r.pl|signed }} ({{ r.pct|pct }})</td>
      <td><form method="post" action="{{ url_for('delete_holding', hid=r.id) }}">
          <button class="link" title="Remove">Remove</button></form></td>
    </tr>
    {% endfor %}
  </table></div>
  <p>
    <a class="btn" href="{{ url_for('download', fmt='csv') }}">Download CSV</a>
    <a class="btn" href="{{ url_for('download', fmt='txt') }}">Download TXT</a>
  </p>
  {% else %}
  <p class="empty">No holdings yet. Add your first one below.</p>
  {% endif %}
</div>

<div class="card">
  <h2>Add a holding</h2>
  <form method="post" action="{{ url_for('add_holding') }}" class="row">
    <input name="stock" list="stocks" placeholder="Stock (AAPL)" required>
    <input name="qty" type="number" step="any" min="0" placeholder="Quantity" required>
    <input name="buy_price" type="number" step="any" min="0" placeholder="Buy price" required>
    <button>Add</button>
  </form>
  <datalist id="stocks">{% for s in prices %}<option value="{{ s }}">{% endfor %}</datalist>
  <p class="sub">The stock must be in the price list below. Add it there first if it is new.</p>
</div>

<div class="card">
  <h2>Price list</h2>
  <form method="post" action="{{ url_for('set_price') }}" class="row">
    <input name="stock" placeholder="Stock (NVDA)" required>
    <input name="price" type="number" step="any" min="0" placeholder="Price now" required>
    <button>Add / update price</button>
  </form>
  <div class="wrap"><table>
    <tr><th>Stock</th><th>Price</th><th></th></tr>
    {% for s, p in prices.items() %}
    <tr><td>{{ s }}</td><td>{{ p|money }}</td>
      <td><form method="post" action="{{ url_for('delete_price', stock=s) }}">
          <button class="link">Delete</button></form></td></tr>
    {% endfor %}
  </table></div>
</div>

<div class="card">
  <h2>History</h2>
  {% if snaps|length > 1 %}
  <div class="wrap"><table>
    <tr><th>When</th><th>Invested</th><th>Value</th><th>P/L</th></tr>
    {% for s in snaps %}
    {% set d = s.value - s.invested %}
    <tr><td>{{ s.time }}</td><td>{{ s.invested|money }}</td><td>{{ s.value|money }}</td>
        <td class="{{ 'good' if d >= 0 else 'bad' }}">{{ d|signed }}</td></tr>
    {% endfor %}
  </table></div>
  {% else %}
  <p class="empty">A new line is saved each time your total changes. Update a price or add a holding to start the history.</p>
  {% endif %}
</div>
</body>
</html>
"""


# ---------- routes ----------
@app.route("/")
def home():
    with lock:
        data = load()
    rows, t = summarize(data)
    return render_template_string(
        PAGE, rows=rows, t=t, prices=dict(sorted(data["prices"].items())),
        snaps=list(reversed(data["snapshots"]))[:10],
    )


@app.post("/holding/add")
def add_holding():
    stock = request.form.get("stock", "").strip().upper()
    qty = positive_number(request.form.get("qty"))
    buy = positive_number(request.form.get("buy_price"))
    with lock:
        data = load()
        if stock not in data["prices"]:
            flash(f"'{stock}' is not in the price list. Add its price first.")
        elif qty is None:
            flash("Quantity must be a number above 0.")
        elif buy is None:
            flash("Buy price must be a number above 0.")
        else:
            data["holdings"].append({"id": data["next_id"], "stock": stock,
                                     "qty": qty, "buy_price": buy})
            data["next_id"] += 1
            take_snapshot(data)
            save(data)
            flash(f"Added {stock}.", "ok")
    return redirect(url_for("home"))


@app.post("/holding/<int:hid>/delete")
def delete_holding(hid):
    with lock:
        data = load()
        data["holdings"] = [h for h in data["holdings"] if h["id"] != hid]
        take_snapshot(data)
        save(data)
    return redirect(url_for("home"))


@app.post("/price/set")
def set_price():
    stock = request.form.get("stock", "").strip().upper()
    price = positive_number(request.form.get("price"))
    if not NAME_RE.match(stock):
        flash("Stock name: 1 to 10 characters, letters/numbers only (. and - allowed inside).")
    elif price is None:
        flash("Price must be a number above 0.")
    else:
        with lock:
            data = load()
            data["prices"][stock] = price
            take_snapshot(data)
            save(data)
        flash(f"{stock} price set to {money(price)}.", "ok")
    return redirect(url_for("home"))


@app.post("/price/<stock>/delete")
def delete_price(stock):
    with lock:
        data = load()
        if any(h["stock"] == stock for h in data["holdings"]):
            flash(f"Can't delete {stock}: you still hold it. Remove the holding first.")
        else:
            data["prices"].pop(stock, None)
            save(data)
    return redirect(url_for("home"))


@app.get("/download/<fmt>")
def download(fmt):
    with lock:
        data = load()
    rows, t = summarize(data)
    if not rows:
        flash("Nothing to download yet.")
        return redirect(url_for("home"))

    if fmt == "csv":
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(["Stock", "Quantity", "Buy Price", "Current Price",
                    "Cost", "Value", "Profit/Loss", "Return %"])
        for r in rows:
            w.writerow([r["stock"], r["qty"], r["buy"], r["price"], round(r["cost"], 2),
                        round(r["value"], 2), round(r["pl"], 2), round(r["pct"], 2)])
        w.writerow(["TOTAL", "", "", "", round(t["invested"], 2), round(t["value"], 2),
                    round(t["pl"], 2), round(t["pct"], 2)])
        body, mime, name = buf.getvalue(), "text/csv", "portfolio.csv"
    elif fmt == "txt":
        lines = ["STOCK PORTFOLIO REPORT",
                 "Generated: " + datetime.now().strftime("%Y-%m-%d %H:%M"), "-" * 60]
        for r in rows:
            lines.append(f"{r['stock']:<8} qty {num(r['qty']):>8}  buy {money(r['buy']):>10}  "
                         f"now {money(r['price']):>10}  P/L {signed(r['pl']):>11}")
        lines += ["-" * 60,
                  f"Total invested: {money(t['invested'])}",
                  f"Current value:  {money(t['value'])}",
                  f"Profit / Loss:  {signed(t['pl'])} ({pct(t['pct'])})"]
        body, mime, name = "\n".join(lines) + "\n", "text/plain", "portfolio.txt"
    else:
        return "Unknown format", 404

    return Response(body, mimetype=mime,
                    headers={"Content-Disposition": f"attachment; filename={name}"})


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
