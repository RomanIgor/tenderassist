"""
TenderAI Backend — Flask API
100% lokal, kein Internet, kein KI
"""

import os
import json
import sqlite3
import tempfile
from datetime import datetime
from pathlib import Path
from flask import Flask, request, jsonify, send_file, send_from_directory
from flask_cors import CORS

from parser import parse_pdf, result_to_dict
from offer_generator import generate_offer_pdf
from matcher import match_requirements
from product_db import VEHICLES

# ─── Setup ────────────────────────────────────────────────────────────────────

BASE_DIR = Path(__file__).parent.parent
DB_PATH  = BASE_DIR / "data" / "db" / "tenderai.db"
UPLOAD_DIR = BASE_DIR / "data" / "tenders"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

app = Flask(__name__, static_folder=str(BASE_DIR / "frontend"), static_url_path="")
CORS(app)

# ─── Datenbank ────────────────────────────────────────────────────────────────

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS tenders (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            filename    TEXT,
            client      TEXT,
            vehicle     TEXT,
            value       REAL,
            status      TEXT DEFAULT 'offen',
            pages       INTEGER,
            req_count   INTEGER,
            created_at  TEXT
        );
        CREATE TABLE IF NOT EXISTS requirements (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            tender_id   INTEGER REFERENCES tenders(id),
            category    TEXT,
            label       TEXT,
            value       TEXT,
            status      TEXT
        );
    """)
    conn.commit()
    conn.close()

# ─── Routes ───────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return send_from_directory(str(BASE_DIR / "frontend"), "tenderai-v2.html")

@app.route("/api/health")
def health():
    return jsonify({
        "status": "ok",
        "local": True,
        "internet": False,
        "ki": False,
        "version": "1.0.0-mvp",
        "timestamp": datetime.now().isoformat(),
    })

@app.route("/api/analyze", methods=["POST"])
def analyze():
    """PDF hochladen und analysieren."""
    if "file" not in request.files:
        return jsonify({"error": "Keine Datei übermittelt"}), 400

    f = request.files["file"]
    if not f.filename.lower().endswith((".pdf", ".docx")):
        return jsonify({"error": "Nur PDF oder DOCX erlaubt"}), 400

    # Datei speichern
    save_path = UPLOAD_DIR / f.filename
    f.save(save_path)

    # Parsen
    result = parse_pdf(str(save_path))
    data   = result_to_dict(result)

    # In DB speichern
    conn = get_db()
    cur = conn.execute(
        "INSERT INTO tenders (filename, status, pages, req_count, created_at) VALUES (?,?,?,?,?)",
        (f.filename, "analyse", result.pages, len(result.requirements), datetime.now().isoformat())
    )
    tender_id = cur.lastrowid
    for req in result.requirements:
        conn.execute(
            "INSERT INTO requirements (tender_id, category, label, value, status) VALUES (?,?,?,?,?)",
            (tender_id, req.category, req.label, req.value, req.status)
        )
    conn.commit()
    conn.close()

    data["tender_id"] = tender_id
    data["match_results"] = match_requirements(data["requirements"])
    return jsonify(data)

@app.route("/api/generate-offer", methods=["POST"])
def generate_offer():
    """Angebots-PDF generieren."""
    body = request.json or {}
    required = ["client", "vehicle", "price", "delivery"]
    for f in required:
        if not body.get(f):
            return jsonify({"error": f"Feld fehlt: {f}"}), 400

    pdf_path = generate_offer_pdf(body)
    return send_file(pdf_path, as_attachment=True,
                     download_name=f"Angebot_{body['vehicle'].replace(' ','_')}_{body['client'].split(',')[0].strip().replace(' ','_')}.pdf",
                     mimetype="application/pdf")

@app.route("/api/catalog")
def catalog():
    """Ziegler Fahrzeugkatalog."""
    return jsonify([
        {
            "id": v["id"],
            "name": v["name"],
            "type": v["type"],
            "description": v["description"],
            "specs": v["specs"],
        }
        for v in VEHICLES
    ])


@app.route("/api/tenders")
def list_tenders():
    """Alle Tender aus der DB."""
    conn = get_db()
    rows = conn.execute("SELECT * FROM tenders ORDER BY created_at DESC").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route("/api/tenders/<int:tid>")
def get_tender(tid):
    """Einzelnen Tender mit Anforderungen."""
    conn = get_db()
    tender = conn.execute("SELECT * FROM tenders WHERE id=?", (tid,)).fetchone()
    reqs   = conn.execute("SELECT * FROM requirements WHERE tender_id=?", (tid,)).fetchall()
    conn.close()
    if not tender:
        return jsonify({"error": "Nicht gefunden"}), 404
    return jsonify({**dict(tender), "requirements": [dict(r) for r in reqs]})

# ─── Start ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    init_db()
    print("\n" + "="*50)
    print("  TenderAI Backend — 100% lokal")
    print("  http://localhost:5000")
    print("  Kein Internet · Kein KI · DSGVO-konform")
    print("="*50 + "\n")
    app.run(host="0.0.0.0", port=5000, debug=True)
