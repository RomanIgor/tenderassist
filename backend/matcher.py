"""
TenderAssist Matcher — Vergleich Ausschreibungsanforderungen vs. Ziegler-Katalog.
100% lokal, kein KI, kein Internet.
"""

import re
from product_db import VEHICLES


def _num(text: str) -> float | None:
    """
    Erste Zahl aus Text extrahieren — unterstützt deutsches Format.
    '14.000' → 14000  (Tausenderpunkt)
    '3,30' → 3.3     (Komma als Dezimal)
    '0.5' → 0.5      (Englischer Dezimalpunkt)
    """
    m = re.search(r'(\d[\d.,]*)', text)
    if not m:
        return None
    raw = m.group(1)
    # Deutsches Tausenderformat: z.B. 14.000 oder 1.400 (Punkt vor genau 3 Stellen)
    if re.match(r'^\d{1,3}(\.\d{3})+$', raw):
        return float(raw.replace('.', ''))
    if re.match(r'^\d{1,3}(\.\d{3})+,\d+$', raw):
        return float(raw.replace('.', '').replace(',', '.'))
    return float(raw.replace(',', '.'))


def _vehicle_display(label: str, specs: dict) -> str:
    mapping = {
        "Motorleistung":       f"{specs.get('motor_kw', '?')} kW",
        "Drehmoment":          f"{specs.get('torque_nm', '?')} Nm",
        "Feuerlöschkreiselpumpe": specs.get("pump_type", "?"),
        "Pumpenleistung":      f"{specs.get('pump_lpm', '?')} l/min",
        "Löschwassertank":     f"{specs.get('tank_liters', '?')} Liter",
        "Antrieb":             specs.get("drive", "?"),
        "Gesamtmasse (zGM)":   f"{specs.get('weight_kg', '?')} kg",
        "Max. Fahrzeughöhe":   f"{specs.get('height_m', '?')} m",
        "Höchstgeschwindigkeit": f"{specs.get('speed_kmh', '?')} km/h",
        "Herstellergarantie":  f"{specs.get('guarantee_months', '?')} Monate",
        "Ersatzteilversorgung": f"{specs.get('spare_parts_years', '?')} Jahre",
        "Servicereaktion":     f"{specs.get('service_hours', '?')} Stunden",
        "Fahrzeugnorm":        " · ".join(specs.get("norms", [])),
        "Pumpennorm":          next((n for n in specs.get("norms", []) if "1028" in n), "—"),
        "ISO-Zertifizierung":  next((n for n in specs.get("norms", []) if "ISO" in n), "—"),
        "Vergabeverfahren":    next((n for n in specs.get("norms", []) if any(x in n for x in ("VOL", "VOB", "VgV", "UVgO"))), "—"),
    }
    return mapping.get(label, "—")


def _evaluate(req: dict, specs: dict) -> str:
    """'met' | 'not_met' | 'neutral' | 'missing'"""
    label  = req["label"]
    value  = req.get("value", "")
    status = req.get("status", "found")

    if status == "missing":
        return "missing"

    if label == "Motorleistung":
        n = _num(value)
        if n is None: return "neutral"
        return "met" if specs.get("motor_kw", 0) >= n else "not_met"

    if label == "Drehmoment":
        n = _num(value)
        if n is None: return "neutral"
        return "met" if specs.get("torque_nm", 0) >= n else "not_met"

    if label == "Feuerlöschkreiselpumpe":
        req_clean = re.sub(r"\s+", "", value).upper()
        veh_clean = re.sub(r"\s+", "", specs.get("pump_type", "")).upper()
        if req_clean in veh_clean or veh_clean in req_clean:
            return "met"
        req_n = _num(value)
        veh_n = _num(specs.get("pump_type", ""))
        if req_n and veh_n:
            return "met" if veh_n >= req_n else "not_met"
        return "not_met"

    if label == "Pumpenleistung":
        n = _num(value)
        if n is None: return "neutral"
        return "met" if specs.get("pump_lpm", 0) >= n else "not_met"

    if label == "Löschwassertank":
        n = _num(value)
        if n is None: return "neutral"
        return "met" if specs.get("tank_liters", 0) >= n else "not_met"

    if label == "Antrieb":
        if re.search(r"allrad|4[×x]4", value, re.I):
            return "met" if "allrad" in specs.get("drive", "").lower() else "not_met"
        return "neutral"

    if label == "Gesamtmasse (zGM)":
        n = _num(value)
        if n is None: return "neutral"
        return "met" if specs.get("weight_kg", 0) <= n else "not_met"

    if label == "Max. Fahrzeughöhe":
        n = _num(value)
        if n is None: return "neutral"
        return "met" if specs.get("height_m", 0) <= n else "not_met"

    if label == "Höchstgeschwindigkeit":
        n = _num(value)
        if n is None: return "neutral"
        return "met" if specs.get("speed_kmh", 0) >= n else "not_met"

    if label == "Herstellergarantie":
        n = _num(value)
        if n is None: return "neutral"
        return "met" if specs.get("guarantee_months", 0) >= n else "not_met"

    if label == "Ersatzteilversorgung":
        n = _num(value)
        if n is None: return "neutral"
        return "met" if specs.get("spare_parts_years", 0) >= n else "not_met"

    if label == "Servicereaktion":
        n = _num(value)
        if n is None: return "neutral"
        return "met" if specs.get("service_hours", 0) <= n else "not_met"

    if label == "Fahrzeugnorm":
        norm_req = value.replace(" ", "").upper()
        for n in specs.get("norms", []):
            if norm_req in n.replace(" ", "").upper():
                return "met"
        return "not_met"

    if label == "Pumpennorm":
        return "met" if any("1028" in n for n in specs.get("norms", [])) else "not_met"

    if label == "ISO-Zertifizierung":
        return "met" if any("ISO" in n for n in specs.get("norms", [])) else "not_met"

    # Fristen und Vergabeverfahren → neutral (wird nur erkannt, nicht bewertet)
    return "neutral"


def match_requirements(requirements: list, vehicles: list = None) -> list:
    """
    Vergleicht extrahierte Anforderungen gegen jeden Ziegler-Fahrzeugtyp.
    Gibt sortierte Liste mit Match-Score zurück.
    """
    if vehicles is None:
        vehicles = VEHICLES

    results = []
    for vehicle in vehicles:
        specs = vehicle["specs"]
        req_results = []
        met = not_met = 0

        for req in requirements:
            ev = _evaluate(req, specs)
            req_results.append({
                "label":         req["label"],
                "category":      req["category"],
                "tender_value":  req["value"],
                "vehicle_value": _vehicle_display(req["label"], specs),
                "match":         ev,
            })
            if ev == "met":
                met += 1
            elif ev in ("not_met", "missing"):
                not_met += 1

        total = met + not_met
        score = round(met / total * 100) if total > 0 else 0

        results.append({
            "id":       vehicle["id"],
            "name":     vehicle["name"],
            "type":     vehicle["type"],
            "score":    score,
            "met":      met,
            "not_met":  not_met,
            "specs_display": {
                "motor":  f"{specs.get('motor_kw', '?')} kW / {specs.get('torque_nm', '?')} Nm",
                "pump":   specs.get("pump_type", "?"),
                "tank":   f"{specs.get('tank_liters', '?'):,} L".replace(",", "."),
                "drive":  specs.get("drive", "?"),
            },
            "requirements": req_results,
        })

    results.sort(key=lambda x: x["score"], reverse=True)
    return results
