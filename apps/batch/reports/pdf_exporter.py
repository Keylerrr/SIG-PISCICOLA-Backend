import io

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from .constants import MODULE_LABELS, MODULE_FEEDING, MODULE_BIOMETRY

PAGE_MARGIN = 0.6 * inch
AVAILABLE_WIDTH = letter[0] - 2 * PAGE_MARGIN


def _get_table_style():
    return TableStyle(
        [
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#00ffff")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f7fafc")]),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
            ("WORDWRAP", (0, 0), (-1, -1), "CJK"),
        ]
    )


def _create_table(data, col_count=None):
    if not data or len(data) < 1:
        return None
    
    style = _styles()["body"]
    
    formatted_data = []
    for row in data:
        formatted_row = [Paragraph(str(cell), style) for cell in row]
        formatted_data.append(formatted_row)
    
    col_count = col_count or len(data[0])
    col_width = AVAILABLE_WIDTH / col_count
    
    table = Table(formatted_data, colWidths=[col_width] * col_count, repeatRows=1)
    table.setStyle(_get_table_style())
    return table


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
        "subheading": ParagraphStyle(
            "SubSectionHeading",
            parent=base["Heading3"],
            fontSize=10,
            spaceBefore=10,
            spaceAfter=6,
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

    return _create_table(rows, col_count=len(keys))


def _filter_records_by_type(records: list[dict], type_value: str) -> list[dict]:
    """Filter records by their 'tipo' field."""
    return [r for r in records if r.get("tipo") == type_value]


def _build_feeding_section(records: list[dict], styles: dict) -> list:
    story = []
    
    if not records:
        story.append(Paragraph("No se encontró información registrada para este módulo.", styles["note"]))
        return story
    
    # Cronogramas (unique programs)
    plans = _filter_records_by_type(records, "plan")
    if plans:
        story.append(Paragraph("Cronogramas de alimentación", styles["subheading"]))
        programs = {}
        for plan in plans:
            program_name = plan.get("programa", "—")
            if program_name not in programs:
                programs[program_name] = plan
        
        if programs:
            program_rows = [["Programa", "Ciclo", "Inicio", "Fin"]]
            for prog_name, plan in programs.items():
                program_rows.append([
                    prog_name,
                    plan.get("ciclo", "—"),
                    plan.get("inicio", "—"),
                    plan.get("fin", "—"),
                ])
            story.append(_create_table(program_rows, col_count=4))
            story.append(Spacer(1, 0.08 * inch))
    
    # Planes de alimentación
    if plans:
        story.append(Paragraph("Planes de alimentación", styles["subheading"]))
        plan_rows = [["Ciclo", "Programa", "Inicio", "Fin"]]
        for plan in plans:
            plan_rows.append([
                plan.get("ciclo", "—"),
                plan.get("programa", "—"),
                plan.get("inicio", "—"),
                plan.get("fin", "—"),
            ])
        story.append(_create_table(plan_rows, col_count=4))
        story.append(Spacer(1, 0.08 * inch))
    
    # Eventos de alimentación
    events = _filter_records_by_type(records, "evento")
    if events:
        story.append(Paragraph("Eventos de alimentación", styles["subheading"]))
        event_rows = [["Ciclo", "Fecha", "Hora", "Ración", "Estado", "Cantidad", "Unidad"]]
        for event in events:
            event_rows.append([
                event.get("ciclo", "—"),
                event.get("fecha", "—"),
                event.get("hora", "—"),
                event.get("racion", "—"),
                event.get("estado", "—"),
                event.get("cantidad", "—"),
                event.get("unidad", "—"),
            ])
        story.append(_create_table(event_rows, col_count=7))
        story.append(Spacer(1, 0.08 * inch))
    
    return story


def _build_biometry_section(records: list[dict], styles: dict) -> list:
    story = []
    
    if not records:
        story.append(Paragraph("No se encontró información registrada para este módulo.", styles["note"]))
        return story
    
    # Controles realizados
    controls = _filter_records_by_type(records, "control")
    if controls:
        story.append(Paragraph("Controles realizados", styles["subheading"]))
        control_rows = [["Ciclo", "Estanque", "Fecha", "Muestra", "Vivos", "Peso Prom (g)", "Mortalidad (%)", "Biomasa (kg)", "FCA"]]
        for control in controls:
            control_rows.append([
                control.get("ciclo", "—"),
                control.get("estanque", "—"),
                control.get("fecha", "—"),
                str(control.get("muestra", "—")),
                str(control.get("vivos", "—")),
                str(control.get("peso_prom_g", "—")),
                str(control.get("mortalidad_%", "—")),
                str(control.get("biomasa_kg", "—")),
                str(control.get("fca", "—")),
            ])
        story.append(_create_table(control_rows, col_count=9))
        story.append(Spacer(1, 0.08 * inch))
    
    # Evaluaciones realizadas
    evaluations = _filter_records_by_type(records, "evaluacion")
    if evaluations:
        story.append(Paragraph("Evaluaciones realizadas", styles["subheading"]))
        eval_rows = [["Ciclo", "Estanque", "Fecha", "Muestra", "Peso Prom (g)", "Mortalidad"]]
        for eval in evaluations:
            eval_rows.append([
                eval.get("ciclo", "—"),
                eval.get("estanque", "—"),
                eval.get("fecha", "—"),
                str(eval.get("muestra", "—")),
                str(eval.get("peso_prom_g", "—")),
                str(eval.get("mortalidad", "—")),
            ])
        story.append(_create_table(eval_rows, col_count=6))
        story.append(Spacer(1, 0.08 * inch))
    
    return story


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
    indicator_table = _create_table(indicator_rows, col_count=6)
    if indicator_table:
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
        cycle_table = _create_table(cycle_rows, col_count=5)
        if cycle_table:
            story.append(cycle_table)
        story.append(Spacer(1, 0.1 * inch))

    for module_key in report_data["selected_modules"]:
        mod = report_data["modules"][module_key]
        story.append(Paragraph(mod["label"], styles["heading"]))
        
        if module_key == MODULE_FEEDING:
            story.extend(_build_feeding_section(mod["records"], styles))
        elif module_key == MODULE_BIOMETRY:
            story.extend(_build_biometry_section(mod["records"], styles))
        else:
            if mod["has_data"]:
                table = _records_to_table(mod["records"])
                if table:
                    story.append(table)
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
