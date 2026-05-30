import io

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
from openpyxl.utils import get_column_letter

from .constants import MODULE_LABELS


HEADER_FILL = PatternFill(start_color="2C5282", end_color="2C5282", fill_type="solid")
HEADER_FONT = Font(color="FFFFFF", bold=True)


def _autosize_columns(ws):
    for col_idx, column_cells in enumerate(ws.columns, 1):
        max_len = 0
        for cell in column_cells:
            if cell.value is not None:
                max_len = max(max_len, len(str(cell.value)))
        ws.column_dimensions[get_column_letter(col_idx)].width = min(max_len + 2, 40)


def _write_records_sheet(ws, records: list[dict], title: str):
    ws.title = title[:31]
    if not records:
        ws.append(["Sin registros para este módulo en el alcance consultado."])
        return
    keys = []
    for rec in records:
        for k in rec.keys():
            if k not in keys:
                keys.append(k)
    ws.append([k.replace("_", " ").title() for k in keys])
    for cell in ws[1]:
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
    for rec in records:
        ws.append([rec.get(k, "") for k in keys])
    _autosize_columns(ws)


def export_production_report_xlsx(report_data: dict) -> bytes:
    wb = Workbook()
    summary = wb.active
    summary.title = "Resumen"

    batch = report_data["batch"]
    summary.append(["Reporte histórico del proceso productivo"])
    summary["A1"].font = Font(bold=True, size=14)
    summary.append([])
    summary.append(["Lote", batch["code"]])
    summary.append(["Especie", batch["specie"]])
    summary.append(["Estado biológico", batch["biological_state"]])
    summary.append(["Estado", batch["status"]])
    summary.append(["Cantidad inicial", batch["initial_quantity"]])
    summary.append(["Generado", report_data["generated_at"]])
    summary.append(["Usuario", report_data["generated_by"]])
    if report_data.get("cycle_id"):
        summary.append(["Ciclo consultado (ID)", report_data["cycle_id"]])
    summary.append([])
    summary.append(["Módulos incluidos"])
    for key in report_data["selected_modules"]:
        mod = report_data["modules"][key]
        status = "Con datos" if mod["has_data"] else "Sin registros"
        summary.append([mod["label"], status])

    if report_data["empty_module_labels"]:
        summary.append([])
        summary.append(["Módulos seleccionados sin información"])
        for label in report_data["empty_module_labels"]:
            summary.append([label])

    ctx = report_data["context"]
    if ctx.get("cycles"):
        summary.append([])
        summary.append(["Ciclos asociados"])
        summary.append(["Nombre", "Estanque", "Estado", "Inicio", "Fin"])
        for c in ctx["cycles"]:
            summary.append(
                [c["name"], c["pond"], c["state"], c["start_date"], c["finish_date"] or ""]
            )

    _autosize_columns(summary)

    for module_key in report_data["selected_modules"]:
        mod = report_data["modules"][module_key]
        sheet_name = MODULE_LABELS.get(module_key, module_key)[:31]
        ws = wb.create_sheet(title=sheet_name)
        _write_records_sheet(ws, mod["records"], sheet_name)

    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer.getvalue()
