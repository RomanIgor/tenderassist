# TenderAssist

Lokales Ausschreibungs-Assistenztool fuer Feuerwehrfahrzeuge.

## Zweck

TenderAssist hilft dabei, Ausschreibungs-PDFs lokal zu verarbeiten, technische Anforderungen zu erkennen und gegen einen simulierten Ziegler-Fahrzeugkatalog abzugleichen.

Keine Cloud-KI, kein externer API-Upload. Die Analyse basiert auf lokalen Regeln und Pattern-Matching.

## Projektstruktur

```text
tenderai_v2/
├── backend/
│   ├── app.py              # Flask API und Webserver
│   ├── parser.py           # PDF-Parser und Regel-Extraktion
│   ├── matcher.py          # Vergleich Tender-Anforderungen vs. Fahrzeugkatalog
│   ├── product_db.py       # Simulierter Fahrzeugkatalog
│   └── offer_generator.py  # PDF-Angebotsgenerator
├── frontend/
│   └── tenderai-v2.html    # Benutzeroberflaeche
├── data/
│   ├── db/                 # Lokale SQLite-Datenbank, nicht in Git
│   └── tenders/            # Hochgeladene PDF-Dateien, nicht in Git
├── requirements.txt
├── Procfile                # Render Start Command
└── start.sh
```

## Lokal starten

```bash
cd C:\tenderai\tenderai_v2
pip install -r requirements.txt
python backend/app.py
```

Browser:

```text
http://localhost:5000
```

## Online testen

GitHub hostet nur den Code. Zum Ausfuehren wird ein Webhoster wie Render verwendet.

Render Einstellungen:

```text
Environment: Python
Build Command: pip install -r requirements.txt
Start Command: gunicorn app:app --chdir backend
```

## Datenschutz

Nicht in GitHub enthalten:

- `data/db/`
- `data/tenders/`
- `.env`
- hochgeladene Kunden-PDFs

Der Beispielkatalog in `backend/product_db.py` ist simuliert und enthaelt keine echten SAP- oder Kundendaten.
