import io

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from .constants import MODULE_LABELS


def _styles():
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "ReportTitle",
            parent=base["Heading1"],
            fontSize=16,
            spaceAfter=12,
        ),
        "heading": ParagraphStyle(
            "SectionHeading",
            parent=base["Heading2"],
            fontSize=12,
            spaceBefore=14,
            spaceAfter=8,
        ),
        "body": ParagraphStyle(
            "ReportBody",
            parent=base["Normal"],
            fontSize=9,
            leading=12,
        ),
        "note": ParagraphStyle(
            "ReportNote",
            parent=base["Italic"],
            fontSize=9,
            textColor=colors.HexColor("#555555"),
        ),
    }


def _records_to_table(records: list[dict]) -> Table | Paragraph:
    if not records:
        return Paragraph("Sin registros.", _styles()["body"])
    keys = []
    for rec in records:
        for k in rec.keys():
            if k not in keys:
                keys.append(k)
    header = [k.replace("_", " ").title() for k in keys]
    rows = [header]
    for rec in records:
        rows.append([str(rec.get(k, "")) for k in keys])
    table = Table(rows, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c5282")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f7fafc")]),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    return table


def export_production_report_pdf(report_data: dict) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=0.6 * inch,
        leftMargin=0.6 * inch,
        topMargin=0.6 * inch,
        bottomMargin=0.6 * inch,
    )
    styles = _styles()
    story = []

    batch = report_data["batch"]
    story.append(Paragraph("Reporte histórico del proceso productivo", styles["title"]))
    story.append(
        Paragraph(
            f"<b>Lote:</b> {batch['code']} &nbsp;|&nbsp; "
            f"<b>Especie:</b> {batch['specie']} &nbsp;|&nbsp; "
            f"<b>Estado:</b> {batch['status']}",
            styles["body"],
        )
    )
    story.append(
        Paragraph(
            f"<b>Generado:</b> {report_data['generated_at']} &nbsp;|&nbsp; "
            f"<b>Usuario:</b> {report_data['generated_by']}",
            styles["body"],
        )
    )
    if report_data.get("cycle_id"):
        story.append(
            Paragraph(
                f"<b>Ciclo consultado (ID):</b> {report_data['cycle_id']}",
                styles["body"],
            )
        )
    story.append(Spacer(1, 0.15 * inch))

    story.append(Paragraph("Indicadores de productividad", styles["heading"]))
    indicator_rows = [["Indicador", "Valor", "Estado", "Clasificación", "Recomendación", "Notas"]]
    for indicator in report_data.get("productivity_indicators", []):
        indicator_rows.append(
            [
                indicator["name"],
                indicator["value"],
                indicator["status"],
                indicator["classification"],
                indicator["recommendation"],
                indicator["notes"],
            ]
        )
    indicator_table = Table(indicator_rows, repeatRows=1)
    indicator_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c5282")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f7fafc")]),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    story.append(indicator_table)
    story.append(Spacer(1, 0.15 * inch))

    ctx = report_data["context"]
    if ctx.get("cycles"):
        story.append(Paragraph("Ciclos asociados", styles["heading"]))
        cycle_rows = [["Ciclo", "Estanque", "Estado", "Inicio", "Fin"]]
        for c in ctx["cycles"]:
            cycle_rows.append(
                [c["name"], c["pond"], c["state"], c["start_date"], c["finish_date"] or "—"]
            )
        t = Table(cycle_rows, repeatRows=1)
        t.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#4a5568")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTSIZE", (0, 0), (-1, -1), 8),
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ]
            )
        )
        story.append(t)
        story.append(Spacer(1, 0.1 * inch))

    for module_key in report_data["selected_modules"]:
        mod = report_data["modules"][module_key]
        story.append(Paragraph(mod["label"], styles["heading"]))
        if mod["has_data"]:
            story.append(_records_to_table(mod["records"]))
        else:
            story.append(
                Paragraph(
                    "No se encontró información registrada para este módulo "
                    "en el alcance consultado.",
                    styles["note"],
                )
            )
        story.append(Spacer(1, 0.12 * inch))

    if report_data["empty_module_labels"]:
        story.append(Paragraph("Módulos sin información registrada", styles["heading"]))
        labels = ", ".join(report_data["empty_module_labels"])
        story.append(
            Paragraph(
                f"Los siguientes módulos fueron seleccionados pero no contaron "
                f"con registros: <b>{labels}</b>.",
                styles["note"],
            )
        )

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()
