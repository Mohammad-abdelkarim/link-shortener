from flask import Flask, request, redirect, render_template, jsonify
import sqlite3
import string
import secrets
from urllib.parse import urlparse
import os

app = Flask(__name__)

DB_PATH = os.environ.get("DB_PATH", "/var/data/links.db")

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with sqlite3.connect(DB_PATH) as con:
        cur = con.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS links (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT UNIQUE NOT NULL,
                long_url TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        con.commit()

def is_valid_url(url):
    p = urlparse(url.strip())
    return p.scheme in ("http", "https") and p.netloc

def generate_code(length=6):
    chars = string.ascii_letters + string.digits
    return "".join(secrets.choice(chars) for _ in range(length))

def save_link(long_url, length=6):
    init_db()
    with sqlite3.connect(DB_PATH) as con:
        cur = con.cursor()
        for _ in range(30):
            code = generate_code(length)
            try:
                cur.execute(
                    "INSERT INTO links (code, long_url) VALUES (?, ?)",
                    (code, long_url)
                )
                con.commit()
                return code
            except sqlite3.IntegrityError:
                continue
    raise RuntimeError("Failed to generate unique code")

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/api/shorten", methods=["POST"])
def shorten():
    data = request.get_json()
    long_url = data.get("url", "").strip()

    if not is_valid_url(long_url):
        return jsonify({"error": "Invalid URL"}), 400

    code = save_link(long_url)
    short_url = request.host_url.rstrip("/") + "/" + code
    return jsonify({"short_url": short_url})

@app.route("/<code>")
def redirect_link(code):
    init_db()
    with sqlite3.connect(DB_PATH) as con:
        cur = con.cursor()
        cur.execute("SELECT long_url FROM links WHERE code=?", (code,))
        row = cur.fetchone()

    if row:
        return redirect(row[0], code=302)
    return "Link not found", 404

if __name__ == "__main__":
    app.run(debug=True)
