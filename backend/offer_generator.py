"""
TenderAssist — Angebots-PDF Generator
Erstellt professionelle Angebotsschreiben lokal mit ReportLab.
Kein Word, kein Cloud, kein Internet.
"""

import tempfile
from datetime import datetime
from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
)
from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER

# Ziegler Rot
ZIEGLER_RED = colors.HexColor("#C8102E")
DARK        = colors.HexColor("#1A1917")
LIGHT_GRAY  = colors.HexColor("#F5F5F3")
MID_GRAY    = colors.HexColor("#9C9A95")
TEXT        = colors.HexColor("#333333")

OUTPUT_DIR = Path(__file__).parent.parent / "data" / "tenders"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def generate_offer_pdf(data: dict) -> str:
    """
    data = {
      client, vehicle, price, delivery, ref, specs,
      motor, pump, tank, drive, guarantee
    }
    Gibt den Dateipfad des generierten PDFs zurück.
    """

    client   = data.get("client", "")
    vehicle  = data.get("vehicle", "")
    price    = data.get("price", "")
    delivery = data.get("delivery", "12 Monate ab Auftragserteilung")
    ref      = data.get("ref", "")
    specs    = data.get("specs", "")
    today    = datetime.now().strftime("%d. %B %Y")

    # Technische Daten aus Analyse oder Defaults
    motor    = data.get("motor", "min. 290 kW / 1.400 Nm")
    pump     = data.get("pump", "FPN 10-3000")
    tank     = data.get("tank", "2.000 Liter")
    drive    = data.get("drive", "Allradantrieb 4×4")
    guarantee= data.get("guarantee", "24 Monate")

    import re as _re
    safe_v    = _re.sub(r'[^\w\-]', '_', vehicle)
    safe_c    = _re.sub(r'[^\w\-]', '_', client.split(',')[0].strip())
    safe_name = f"Angebot_{safe_v}_{safe_c}.pdf"
    out_path  = str(OUTPUT_DIR / safe_name)

    doc = SimpleDocTemplate(
        out_path,
        pagesize=A4,
        leftMargin=2.5*cm, rightMargin=2.5*cm,
        topMargin=2*cm, bottomMargin=2*cm,
    )

    styles = getSampleStyleSheet()

    # Custom styles
    def style(name, **kw):
        return ParagraphStyle(name, **kw)

    s_company = style("Company",
        fontName="Helvetica-Bold", fontSize=18,
        textColor=ZIEGLER_RED, spaceAfter=2)
    s_company_sub = style("CompanySub",
        fontName="Helvetica", fontSize=9,
        textColor=MID_GRAY, spaceAfter=0)
    s_addr_right = style("AddrRight",
        fontName="Helvetica", fontSize=9,
        textColor=TEXT, alignment=TA_RIGHT, leading=14)
    s_meta_label = style("MetaLabel",
        fontName="Helvetica-Bold", fontSize=8,
        textColor=MID_GRAY, spaceAfter=1)
    s_meta_val = style("MetaVal",
        fontName="Helvetica-Bold", fontSize=10,
        textColor=DARK, spaceAfter=0)
    s_subject = style("Subject",
        fontName="Helvetica-Bold", fontSize=13,
        textColor=DARK, spaceBefore=16, spaceAfter=14)
    s_body = style("Body",
        fontName="Helvetica", fontSize=10,
        textColor=TEXT, leading=16, spaceAfter=10)
    s_section = style("Section",
        fontName="Helvetica-Bold", fontSize=9,
        textColor=ZIEGLER_RED, spaceBefore=8, spaceAfter=4,
        letterSpacing=1)
    s_footer = style("Footer",
        fontName="Helvetica", fontSize=8,
        textColor=MID_GRAY, alignment=TA_CENTER)
    s_sig_label = style("SigLabel",
        fontName="Helvetica", fontSize=9, textColor=MID_GRAY)
    s_local_badge = style("LocalBadge",
        fontName="Helvetica-Bold", fontSize=8,
        textColor=colors.HexColor("#15803D"),
        alignment=TA_RIGHT)

    story = []

    # ── Briefkopf ──────────────────────────────────────────────────────────────
    header_data = [[
        [Paragraph("ZIEGLER", s_company),
         Paragraph("Albert Ziegler GmbH · Wir geben Sicherheit.", s_company_sub)],
        Paragraph(
            "Albert Ziegler GmbH<br/>Rosenheimer Str. 9<br/>"
            "87616 Marktoberdorf<br/>info@ziegler.de · www.ziegler.de",
            s_addr_right)
    ]]
    header_tbl = Table(header_data, colWidths=[10*cm, 6.5*cm])
    header_tbl.setStyle(TableStyle([
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("ALIGN",  (1,0), (1,0),  "RIGHT"),
        ("LINEBELOW", (0,0), (-1,0), 2, ZIEGLER_RED),
        ("BOTTOMPADDING", (0,0), (-1,0), 10),
    ]))
    story.append(header_tbl)
    story.append(Spacer(1, 16))

    # ── Empfänger ──────────────────────────────────────────────────────────────
    story.append(Paragraph("AN", s_meta_label))
    story.append(Paragraph(client, s_meta_val))
    story.append(Paragraph("z. Hd. Beschaffungsverantwortliche/r", s_body))
    story.append(Spacer(1, 12))

    # ── Metadaten Box ──────────────────────────────────────────────────────────
    meta_data = [[
        [Paragraph("DATUM", s_meta_label), Paragraph(today, s_meta_val)],
        [Paragraph("AKTENZEICHEN", s_meta_label), Paragraph(ref or "—", s_meta_val)],
        [Paragraph("ANSPRECHPARTNER", s_meta_label), Paragraph("Vertrieb Ausschreibungen", s_meta_val)],
        [Paragraph("GÜLTIG BIS", s_meta_label), Paragraph("90 Tage ab Datum", s_meta_val)],
    ]]
    # Flatten to single row
    meta_row = [[
        [Paragraph("DATUM", s_meta_label), Paragraph(today, s_meta_val)],
        [Paragraph("AKTENZEICHEN", s_meta_label), Paragraph(ref or "—", s_meta_val)],
        [Paragraph("GÜLTIG", s_meta_label), Paragraph("90 Tage", s_meta_val)],
    ]]
    meta_tbl = Table(meta_row, colWidths=[5.5*cm, 5.5*cm, 5.5*cm])
    meta_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), LIGHT_GRAY),
        ("LEFTPADDING",  (0,0), (-1,-1), 10),
        ("RIGHTPADDING", (0,0), (-1,-1), 10),
        ("TOPPADDING",   (0,0), (-1,-1), 8),
        ("BOTTOMPADDING",(0,0), (-1,-1), 8),
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("LINEAFTER", (0,0), (1,-1), 0.5, colors.HexColor("#D8D6D0")),
        ("ROUNDEDCORNERS", [4]),
    ]))
    story.append(meta_tbl)
    story.append(Spacer(1, 14))

    # ── Betreff ────────────────────────────────────────────────────────────────
    story.append(Paragraph(
        f"Betr.: Angebot — Beschaffung {vehicle} gemäß Ausschreibungsunterlagen"
        + (f" Az. {ref}" if ref else ""),
        s_subject))

    # ── Anschreiben ────────────────────────────────────────────────────────────
    story.append(Paragraph("Sehr geehrte Damen und Herren,", s_body))
    story.append(Paragraph(
        f"vielen Dank für die Übersendung Ihrer Ausschreibungsunterlagen. Wir freuen uns, "
        f"Ihnen nachstehend unser Angebot für die Lieferung eines einsatzbereiten "
        f"<b>{vehicle}</b> unterbreiten zu dürfen.", s_body))
    story.append(Paragraph(
        "Das angebotene Fahrzeug entspricht vollständig dem aktuellen Stand der Technik, "
        "sämtlichen Unfallverhütungsvorschriften sowie den einschlägigen DIN-Normen "
        "(insbesondere DIN 14530, DIN EN 1846). Alle Mindest- und Sonderanforderungen "
        "Ihrer Leistungsbeschreibung werden erfüllt.", s_body))

    # ── Spezifikationstabelle ──────────────────────────────────────────────────
    story.append(Paragraph("TECHNISCHE SPEZIFIKATION", s_section))

    spec_rows = [
        ["Anforderung", "Ausführung / Spezifikation", "Norm / Basis"],
        ["Fahrzeugtyp",     f"{vehicle} mit Allradantrieb",    "DIN 14530-27"],
        ["Motorleistung",   motor,                             "DIN EN 1846"],
        ["Pumpentyp",       pump + " eingebaut",               "DIN EN 1028"],
        ["Löschwassertank", tank + " (nutzbar), Edelstahl V4A","EN 1846-2"],
        ["Antrieb",         drive,                             "Serienausstattung"],
        ["Lieferzeit",      delivery,                          "gem. Ausschreibung"],
        ["Garantie",        guarantee + " Herstellergarantie", "§443 BGB"],
        ["ISO-Zertifizierung","ISO 9001:2015 · TÜV-geprüft",  "Zertifikat beigelegt"],
        ["Ersatzteile",     "min. 20 Jahre ab Auslieferung",   "§4 Ausschreibung"],
    ]

    col_w = [4.5*cm, 7*cm, 5*cm]
    spec_tbl = Table(spec_rows, colWidths=col_w)
    spec_tbl.setStyle(TableStyle([
        # Header
        ("BACKGROUND",    (0,0), (-1,0), ZIEGLER_RED),
        ("TEXTCOLOR",     (0,0), (-1,0), colors.white),
        ("FONTNAME",      (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE",      (0,0), (-1,0), 9),
        ("TOPPADDING",    (0,0), (-1,0), 7),
        ("BOTTOMPADDING", (0,0), (-1,0), 7),
        # Body
        ("FONTNAME",  (0,1), (-1,-1), "Helvetica"),
        ("FONTSIZE",  (0,1), (-1,-1), 9),
        ("TEXTCOLOR", (0,1), (-1,-1), TEXT),
        ("TOPPADDING",    (0,1), (-1,-1), 6),
        ("BOTTOMPADDING", (0,1), (-1,-1), 6),
        ("LEFTPADDING",   (0,0), (-1,-1), 8),
        ("ROWBACKGROUNDS",(0,1), (-1,-1), [colors.white, LIGHT_GRAY]),
        ("GRID", (0,0), (-1,-1), 0.3, colors.HexColor("#E0DEDB")),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        # First column bold
        ("FONTNAME", (0,1), (0,-1), "Helvetica-Bold"),
        ("FONTSIZE", (0,1), (0,-1), 9),
    ]))
    story.append(spec_tbl)
    story.append(Spacer(1, 12))

    # ── Preisbox ───────────────────────────────────────────────────────────────
    story.append(Paragraph("ANGEBOTSPREIS", s_section))
    price_data = [[
        [Paragraph("NETTO (zzgl. gesetzl. MwSt.)", style("pl", fontName="Helvetica", fontSize=8, textColor=colors.white)),
         Paragraph(f"<b>{price}</b>", style("pv", fontName="Helvetica-Bold", fontSize=18, textColor=colors.white))],
        [Paragraph("LIEFERZEIT", style("pl2", fontName="Helvetica", fontSize=8, textColor=colors.HexColor("#AAAAAA"))),
         Paragraph(f"<b>{delivery.split(' ab')[0]}</b>", style("pv2", fontName="Helvetica-Bold", fontSize=13, textColor=colors.white)),
         Paragraph("ab Auftragserteilung", style("pv3", fontName="Helvetica", fontSize=9, textColor=colors.HexColor("#AAAAAA")))],
    ]]
    # Simpler price box
    price_simple = [[
        Paragraph(f"<b>{price}</b>", style("pbs", fontName="Helvetica-Bold", fontSize=16, textColor=colors.white)),
        Paragraph(f"<b>{delivery}</b>", style("pbd", fontName="Helvetica-Bold", fontSize=11, textColor=colors.white)),
    ]]
    price_tbl = Table(price_simple, colWidths=[8*cm, 8.5*cm])
    price_tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,-1), DARK),
        ("TOPPADDING",    (0,0), (-1,-1), 14),
        ("BOTTOMPADDING", (0,0), (-1,-1), 14),
        ("LEFTPADDING",   (0,0), (-1,-1), 16),
        ("RIGHTPADDING",  (0,0), (-1,-1), 16),
        ("VALIGN",        (0,0), (-1,-1), "MIDDLE"),
        ("ROUNDEDCORNERS",[4]),
    ]))
    story.append(price_tbl)
    story.append(Spacer(1, 12))

    # ── Schlusstext ────────────────────────────────────────────────────────────
    story.append(Paragraph(
        "Wir sichern Ihnen eine Ersatzteilversorgung für mindestens 20 Jahre ab Auslieferung zu. "
        "Serviceeinsätze und Ersatzteile werden innerhalb von 48 Stunden bereitgestellt. "
        "Eine kostenlose Vorführung bei Ihrer Feuerwehr ist nach Terminabsprache möglich.", s_body))
    story.append(Paragraph(
        "Für Rückfragen stehen wir Ihnen gerne zur Verfügung. "
        "Wir freuen uns sehr auf eine erfolgreiche Zusammenarbeit.", s_body))
    story.append(Paragraph("Mit freundlichen Grüßen,", s_body))
    story.append(Spacer(1, 28))

    # ── Unterschrift ───────────────────────────────────────────────────────────
    sig_data = [[
        [HRFlowable(width=4*cm, color=MID_GRAY, thickness=0.5),
         Paragraph("Vertriebsleiter Ausschreibungen<br/>Albert Ziegler GmbH", s_sig_label)],
        Paragraph("🔒 Lokal generiert · DSGVO-konform<br/>Kein Cloud-Upload · Keine KI", s_local_badge),
    ]]
    sig_tbl = Table(sig_data, colWidths=[9*cm, 7.5*cm])
    sig_tbl.setStyle(TableStyle([
        ("VALIGN",  (0,0), (-1,-1), "BOTTOM"),
        ("TOPPADDING",  (0,0), (-1,-1), 0),
    ]))
    story.append(sig_tbl)

    # ── Trennlinie + Footer ────────────────────────────────────────────────────
    story.append(Spacer(1, 16))
    story.append(HRFlowable(width="100%", color=colors.HexColor("#E0DEDB"), thickness=0.5))
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        "Albert Ziegler GmbH · HRB 13592 · Amtsgericht Kempten · USt-IdNr.: DE129274935 · "
        "Erstellt mit TenderAssist · 100% lokal",
        s_footer))

    doc.build(story)
    return out_path


# ─── Test ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    path = generate_offer_pdf({
        "client":   "Gemeinde Aalen, Feuerwehr",
        "vehicle":  "HLF 20 / Z-Klasse",
        "price":    "€ 485.000,00",
        "delivery": "12 Monate ab Auftragserteilung",
        "ref":      "LF20-2024-087",
        "motor":    "min. 290 kW / 1.400 Nm, Euro 6e",
        "pump":     "FPN 10-3000",
        "tank":     "2.000 Liter",
        "drive":    "Allradantrieb 4×4",
        "guarantee":"24 Monate",
    })
    print(f"PDF generiert: {path}")
