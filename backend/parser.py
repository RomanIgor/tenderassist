"""
TenderAssist Parser — 100% lokal, kein KI, kein Internet.
Extrahiert technische Anforderungen aus Feuerwehr-Ausschreibungen.
"""

import re
from pathlib import Path
import pdfplumber
from dataclasses import dataclass, field
from typing import Optional

# ─── Datenstrukturen ───────────────────────────────────────────────────────────

@dataclass
class Requirement:
    category: str       # technik | frist | rechtlich | garantie
    label: str
    value: str
    unit: str = ""
    mandatory: bool = True
    status: str = "found"   # found | missing | check

@dataclass
class ParseResult:
    filename: str
    pages: int
    chars: int
    requirements: list[Requirement] = field(default_factory=list)
    raw_text: str = ""
    warnings: list[str] = field(default_factory=list)

# ─── Regex-Regeln für Feuerwehr-Ausschreibungen ───────────────────────────────

RULES = [

    # TECHNIK — Motor
    {
        "category": "technik",
        "label": "Motorleistung",
        "patterns": [
            r"[Mm]otorleistung\s*(?:mind(?:est)?\.?|min\.?|von)?\s*(\d[\d.,]+)\s*kW",
            r"(\d[\d.,]+)\s*kW\s*[Mm]otorleistung",
            r"[Mm]ind(?:est)?\.?\s*(\d[\d.,]+)\s*kW",
            r"Leistung\s*(?:mind\.?)?\s*(\d[\d.,]+)\s*kW",
        ],
        "unit": "kW",
        "prefix": "min. ",
    },
    {
        "category": "technik",
        "label": "Drehmoment",
        "patterns": [
            r"(\d[\d.,]+)\s*Nm\s*[Dd]rehmoment",
            r"[Dd]rehmoment\s*(?:mind\.?)?\s*(\d[\d.,]+)\s*Nm",
            r"mind\.\s*(\d[\d.,]+)\s*Nm",
        ],
        "unit": "Nm",
        "prefix": "min. ",
    },

    # TECHNIK — Pumpe
    {
        "category": "technik",
        "label": "Feuerlöschkreiselpumpe",
        "patterns": [
            r"(FPN?\s*\d+[-–]\d+)",
            r"(FP\s*\d+[-–]\d+)",
            r"[Ff]euerl.schkreiselpumpe\s+(\w+\s*\d+[-–]\d+)",
        ],
        "unit": "",
        "prefix": "",
    },
    {
        "category": "technik",
        "label": "Pumpenleistung",
        "patterns": [
            r"(\d[\d.,]+)\s*l/min",
            r"[Ff]örderstrom\s*(?:mind\.?)?\s*(\d[\d.,]+)\s*l",
            r"(\d[\d.,]+)\s*[Ll]iter/[Mm]in",
        ],
        "unit": "l/min",
        "prefix": "min. ",
    },

    # TECHNIK — Tank
    {
        "category": "technik",
        "label": "Löschwassertank",
        "patterns": [
            r"[Ll].schwasser(?:beh.lter|tank)\s*(?:mind\.?|min\.?|von)?\s*(\d[\d.,]+)\s*[Ll]iter",
            r"[Tt]ank(?:inhalt|volumen|fassungsverm.gen)\s*(?:mind\.?)?\s*(\d[\d.,]+)\s*[Ll]",
            r"[Ff]assungsverm.gen\s*(?:mind\.?)?\s*(\d[\d.,]+)\s*[Ll]iter",
            r"(\d[\d.,]+)\s*[Ll]iter\s*(?:[Ll].sch)?[Ww]asser",
            r"[Ww]assertank\s*(?:mind\.?)?\s*(\d[\d.,]+)",
            r"[Ll].schwasser\s*(\d[\d.,]+)\s*[Ll]",
        ],
        "unit": "Liter",
        "prefix": "min. ",
    },

    # TECHNIK — Antrieb
    {
        "category": "technik",
        "label": "Antrieb",
        "patterns": [
            r"(Allrad(?:antrieb)?(?:\s*4[×x]4)?)",
            r"(4[×x]4[\s-]*Allrad)",
            r"([Aa]llrad(?:antrieb)?)",
        ],
        "unit": "",
        "prefix": "",
    },

    # TECHNIK — Fahrzeugmasse
    {
        "category": "technik",
        "label": "Gesamtmasse (zGM)",
        "patterns": [
            r"(?:zGM|zul(?:ässige)?\.?\s*Gesamtmasse|Gesamtgewicht)\s*(?:max\.?|von)?\s*(\d[\d.,]+)\s*(?:kg|t)",
            r"(\d[\d.,]+)\s*kg\s*(?:zGM|Gesamtmasse)",
            r"(?:max(?:imal)?\.?\s*)?(\d{4,5})\s*kg",
        ],
        "unit": "kg",
        "prefix": "max. ",
    },

    # TECHNIK — Höhe/Breite
    {
        "category": "technik",
        "label": "Max. Fahrzeughöhe",
        "patterns": [
            r"[Ff]ahrzeughöhe\s*(?:max\.?|von)?\s*(\d[\d.,]+)\s*m",
            r"[Gg]esamthöhe\s*(?:max\.?|von)?\s*(\d[\d.,]+)\s*m",
            r"[Hh]öhe\s*(?:max\.?)?\s*(\d[,.]\d+)\s*m",
        ],
        "unit": "m",
        "prefix": "max. ",
    },

    # TECHNIK — Geschwindigkeit
    {
        "category": "technik",
        "label": "Höchstgeschwindigkeit",
        "patterns": [
            r"[Hh]öchstgeschwindigkeit\s*(?:mind\.?|min\.?|max\.?)?\s*(\d+)\s*km/h",
            r"(\d+)\s*km/h\s*[Hh]öchstgeschwindigkeit",
            r"[Gg]eschwindigkeit\s*(?:mind\.?)?\s*(\d+)\s*km/h",
        ],
        "unit": "km/h",
        "prefix": "min. ",
    },

    # FRISTEN
    {
        "category": "frist",
        "label": "Angebotsabgabe",
        "patterns": [
            r"[Aa]bgabe(?:frist|termin|datum)?\s*[:\s]+(\d{1,2}\.\d{1,2}\.\d{2,4})",
            r"[Ee]ingangsfrist\s*[:\s]+(\d{1,2}\.\d{1,2}\.\d{2,4})",
            r"(?:bis\s+spätestens|bis\s+zum)\s+(\d{1,2}\.\d{1,2}\.\d{2,4})",
            r"[Aa]ngebotsfrist.*?(\d{1,2}\.\d{1,2}\.\d{2,4})",
        ],
        "unit": "",
        "prefix": "",
    },
    {
        "category": "frist",
        "label": "Lieferzeit",
        "patterns": [
            r"[Ll]ieferzeit\s*(?:von|max\.?|mind\.?)?\s*(\d+)\s*(?:Kalender)?[Ww]ochen",
            r"[Ll]ieferfrist\s*[:\s]*(\d+)\s*(?:Kalender)?[Mm]onate",
            r"(\d+)\s*[Mm]onate\s*ab\s*(?:Auftrags|Bestell)",
            r"[Ll]ieferung\s*(?:innerhalb\s*von)?\s*(\d+)\s*[Mm]onate",
        ],
        "unit": "Monate",
        "prefix": "",
        "suffix": " ab Auftragserteilung",
    },

    # RECHTLICH — Normen
    {
        "category": "rechtlich",
        "label": "Fahrzeugnorm",
        "patterns": [
            r"(DIN\s*1453\d[-–]\d+)",
            r"(DIN\s*EN\s*1846[-–]\d)",
            r"(DIN\s*14530[-–]\d+)",
        ],
        "unit": "",
        "prefix": "",
    },
    {
        "category": "rechtlich",
        "label": "Pumpennorm",
        "patterns": [
            r"(DIN\s*EN\s*1028[-–]\d)",
            r"(EN\s*1028)",
        ],
        "unit": "",
        "prefix": "gem. ",
    },
    {
        "category": "rechtlich",
        "label": "Vergabeverfahren",
        "patterns": [
            r"(VgV\s*§\s*\d+)",
            r"(VOL/A)",
            r"(VOB/A)",
            r"(UVgO)",
            r"EU-weite\s+Ausschreibung",
        ],
        "unit": "",
        "prefix": "",
    },
    {
        "category": "rechtlich",
        "label": "ISO-Zertifizierung",
        "patterns": [
            r"(ISO\s*9\d{3}(?::\d{4})?)",
            r"[Zz]ertifizierung\s+nach\s+(ISO\s*\d+)",
        ],
        "unit": "",
        "prefix": "",
    },

    # GARANTIE
    {
        "category": "garantie",
        "label": "Herstellergarantie",
        "patterns": [
            r"[Gg]arantie\s*(?:von\s*)?(?:mind\.?|min\.?)?\s*(\d+)\s*(?:Kalender)?[Mm]onate",
            r"(\d+)\s*[Mm]onate\s*[Gg]arantie",
            r"[Gg]ewährleistung\s*(?:von)?\s*(\d+)\s*[Mm]onate",
        ],
        "unit": "Monate",
        "prefix": "min. ",
    },
    {
        "category": "garantie",
        "label": "Ersatzteilversorgung",
        "patterns": [
            r"[Ee]rsatzteil(?:versorgung|verfügbarkeit)\s*(?:von\s*)?(?:mind\.?|min\.?)?\s*(\d+)\s*Jahre",
            r"(\d+)\s*Jahre\s*[Ee]rsatzteil",
        ],
        "unit": "Jahre",
        "prefix": "min. ",
    },
    {
        "category": "garantie",
        "label": "Servicereaktion",
        "patterns": [
            r"[Ss]ervice(?:leistungen)?\s*(?:innerhalb\s*von\s*)?(\d+)\s*Stunden",
            r"(\d+)\s*Stunden\s*(?:Service|Reaktionszeit)",
            r"[Rr]eaktionszeit\s*(?:von\s*)?(\d+)\s*[Ss]tunden",
        ],
        "unit": "Stunden",
        "prefix": "innerhalb ",
    },
]

# ─── Haupt-Parser ──────────────────────────────────────────────────────────────

def parse_pdf(filepath: str) -> ParseResult:
    """Liest ein PDF und extrahiert alle Anforderungen."""

    result = ParseResult(filename=Path(filepath).name, pages=0, chars=0)

    try:
        with pdfplumber.open(filepath) as pdf:
            result.pages = len(pdf.pages)
            pages_text = []
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    pages_text.append(t)
            result.raw_text = "\n".join(pages_text)
            result.chars = len(result.raw_text)
    except Exception as e:
        result.warnings.append(f"PDF-Fehler: {str(e)}")
        return result

    if not result.raw_text.strip():
        result.warnings.append("Kein Text extrahiert — möglicherweise gescanntes PDF.")
        return result

    # Anforderungen extrahieren
    found_labels = set()

    for rule in RULES:
        for pattern in rule["patterns"]:
            match = re.search(pattern, result.raw_text, re.IGNORECASE | re.MULTILINE)
            if match and rule["label"] not in found_labels:
                raw_val = match.group(1) if match.lastindex else match.group(0)
                raw_val = raw_val.strip()

                prefix = rule.get("prefix", "")
                suffix = rule.get("suffix", "")
                unit   = rule.get("unit", "")

                if unit and unit not in raw_val:
                    value = f"{prefix}{raw_val} {unit}{suffix}".strip()
                else:
                    value = f"{prefix}{raw_val}{suffix}".strip()

                result.requirements.append(Requirement(
                    category=rule["category"],
                    label=rule["label"],
                    value=value,
                    unit=unit,
                    mandatory=True,
                    status="found",
                ))
                found_labels.add(rule["label"])
                break

    # Fehlende Pflichtfelder
    pflicht = ["Motorleistung", "Löschwassertank", "Feuerlöschkreiselpumpe", "Lieferzeit"]
    for p in pflicht:
        if p not in found_labels:
            result.requirements.append(Requirement(
                category="technik",
                label=p,
                value="Nicht gefunden",
                status="missing",
                mandatory=True,
            ))
            result.warnings.append(f"Pflichtfeld nicht gefunden: {p}")

    return result


def result_to_dict(r: ParseResult) -> dict:
    """Konvertiert ParseResult zu JSON-serialisierbarem Dict."""
    return {
        "filename": r.filename,
        "pages": r.pages,
        "chars": r.chars,
        "warnings": r.warnings,
        "summary": {
            "total": len(r.requirements),
            "found": sum(1 for x in r.requirements if x.status == "found"),
            "missing": sum(1 for x in r.requirements if x.status == "missing"),
        },
        "requirements": [
            {
                "category": req.category,
                "label": req.label,
                "value": req.value,
                "unit": req.unit,
                "mandatory": req.mandatory,
                "status": req.status,
            }
            for req in r.requirements
        ],
    }


# ─── Test lokal ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys, json
    if len(sys.argv) > 1:
        r = parse_pdf(sys.argv[1])
        print(json.dumps(result_to_dict(r), indent=2, ensure_ascii=False))
    else:
        print("Usage: python3 parser.py datei.pdf")
