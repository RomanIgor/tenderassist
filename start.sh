#!/bin/bash
echo ""
echo "╔══════════════════════════════════════════════╗"
echo "║         TenderAI — 100% lokal               ║"
echo "║  Kein Internet · Kein KI · DSGVO-konform    ║"
echo "╚══════════════════════════════════════════════╝"
echo ""
cd "$(dirname "$0")/backend"
python3 -c "import flask, pdfplumber, reportlab" 2>/dev/null || {
  echo "→ Installiere Pakete..."
  pip install flask flask-cors pdfplumber reportlab --break-system-packages -q
}
echo "→ http://localhost:5000"
echo ""
python3 app.py
