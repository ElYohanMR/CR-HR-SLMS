"""Readable, read-only comparison of the values stored in an audit event."""
import json

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView, QCheckBox, QDialog, QDialogButtonBox, QHeaderView,
    QLabel, QTableWidget, QTableWidgetItem, QVBoxLayout,
)

LABELS = {
    "number": "Número de casillero", "has_padlock": "Tiene candado",
    "condition": "Condición", "condition_after_cut": "Condición al cerrar el corte",
    "notes": "Notas", "row": "Fila", "column": "Columna", "version": "Versión del registro",
    "id": "Identificador", "block_id": "Identificador del bloque", "locker_id": "Identificador del casillero",
    "employee_id": "Identificador del empleado", "employee_number": "ID del empleado",
    "first_name": "Nombre", "surname": "Primer apellido", "second_surname": "Segundo apellido",
    "email": "Correo electrónico", "department": "Departamento", "shift": "Turno", "active": "Activo",
    "name": "Nombre", "username": "Usuario", "role": "Permiso", "is_initial": "Administrador inicial",
    "deleted_at": "Fecha de eliminación", "started_at": "Fecha de asignación", "ended_at": "Fecha de devolución",
    "started_by": "Asignado por", "ended_by": "Devuelto por", "reason": "Motivo", "end_reason": "Motivo de devolución",
    "status": "Estado", "supervisor": "Supervisor solicitante", "assignee": "Encargado del corte",
    "channel": "Medio de solicitud", "result": "Resultado", "identity_verified": "Identidad verificada",
    "created_at": "Fecha de creación", "created_by": "Creado por", "assigned_at": "Fecha de asignación del encargado",
    "performed_at": "Fecha del corte", "completed_at": "Fecha de cierre", "completed_by": "Cerrado por",
    "reference": "Referencia", "employee_name": "Nombre del empleado", "locker_number": "Número de casillero",
    "label": "Código del bloque", "rows": "Filas", "columns": "Columnas", "rotation": "Rotación",
    "x": "Posición horizontal", "y": "Posición vertical", "location": "Ubicación", "side": "Lado",
    "floor": "Piso / nivel", "background": "Imagen del plano", "polygons": "Contornos", "extra": "Datos adicionales",
    "filename": "Nombre del archivo", "current": "Evidencia actual", "uploaded_by": "Adjuntado por",
    "uploaded_at": "Fecha del archivo", "size": "Tamaño del archivo (bytes)",
}
VALUES = {
    "condition": {"utilizable": "Utilizable", "pendiente": "Pendiente de verificar",
                  "mantenimiento": "Mantenimiento", "retirado": "Retirado"},
    "status": {"solicitada": "Solicitada", "en_proceso": "En proceso", "finalizada": "Finalizada", "cancelada": "Cancelada"},
    "role": {"admin": "Administración", "operator": "Operación", "viewer": "Consulta"},
    "channel": {"teams": "Teams", "correo": "Correo electrónico", "otro": "Otro medio"},
}
MISSING = object()


def comparison(before, after, path=()):
    """Keep missing fields distinct from null and compare nested fields individually."""
    if isinstance(before, dict) and isinstance(after, dict):
        for key in dict.fromkeys([*before, *after]):
            yield from comparison(before.get(key, MISSING), after.get(key, MISSING), path + (key,))
    else:
        changed = type(before) is not type(after) or before != after
        yield path, before, after, changed


def display_value(path, value):
    if value is MISSING:
        return "No existía"
    if value is None:
        return "Sin dato"
    if isinstance(value, bool):
        return "Sí" if value else "No"
    if value == "":
        return "Vacío"
    key = path[-1] if path else ""
    if key == "background" and isinstance(value, str):
        return f"Imagen guardada ({len(value):,} caracteres)"
    if key in ("row", "column") and isinstance(value, int):
        return str(value + 1)
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, indent=2)
    values = VALUES.get("condition" if key == "condition_after_cut" else key, {})
    return values.get(value, str(value))


class AuditDialog(QDialog):
    def __init__(self, event, parent=None, title="Detalle del cambio"):
        super().__init__(parent)
        self.setWindowTitle("Detalle del cambio")
        area = self.screen().availableGeometry()
        self.resize(min(1000, area.width() - 60), min(620, area.height() - 80))
        layout = QVBoxLayout(self)
        heading = QLabel(title)
        heading.setTextFormat(Qt.TextFormat.PlainText)
        heading.setObjectName("title")
        heading.setWordWrap(True)
        layout.addWidget(heading)
        self.rows = sorted(comparison(event.get("before", {}), event.get("after", {})), key=lambda row: not row[3])
        count = sum(row[3] for row in self.rows)
        layout.addWidget(QLabel(f"{count} campo{'s' if count != 1 else ''} con cambios · Resaltados en negrita"))
        if event.get("reason"):
            reason = QLabel("Motivo: " + event["reason"])
            reason.setTextFormat(Qt.TextFormat.PlainText)
            reason.setWordWrap(True)
            layout.addWidget(reason)
        self.show_unchanged = QCheckBox("Mostrar también los campos sin cambios")
        self.show_unchanged.toggled.connect(self.refresh)
        layout.addWidget(self.show_unchanged)
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Campo", "Antes", "Después"])
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().hide()
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setWordWrap(True)
        layout.addWidget(self.table, 1)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.button(QDialogButtonBox.StandardButton.Close).setText("Cerrar")
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.refresh()

    def refresh(self):
        rows = [row for row in self.rows if row[3] or self.show_unchanged.isChecked()]
        self.table.setRowCount(len(rows))
        for index, (path, before, after, changed) in enumerate(rows):
            label = " / ".join(LABELS.get(key, key.replace("_", " ").capitalize()) for key in path) or "Registro"
            for column, value in enumerate((label, display_value(path, before), display_value(path, after))):
                item = QTableWidgetItem(value)
                item.setToolTip(value)
                if changed:
                    font = item.font()
                    font.setBold(True)
                    item.setFont(font)
                    item.setBackground(QColor("#fff0df"))
                self.table.setItem(index, column, item)
        self.table.resizeRowsToContents()


def show_audit_detail(parent, event, title="Detalle del cambio"):
    AuditDialog(event, parent, title).exec()
