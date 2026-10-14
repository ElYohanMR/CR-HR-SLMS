"""Guided workflows for row creation, inspections and conflict review."""

import copy
import csv
from datetime import datetime

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QFileDialog

from .forms import Form, info, confirm
from .mapview import MapView
from .block_rows import plan_row
from .numbering import numbering_fields, bind_order_combos
from .inspections import OUTCOMES, DISCREPANCIES


class Workflows:
    def conflict_context(self, item):
        """Readable request/current-state comparison; never expose passwords or images."""
        from .window import ACTIONS, STATES, full_name

        action, payload = item["command"]["action"], item["command"]["payload"]
        rows = [("Operación", ACTIONS.get(action, action), item["message"])]
        labels = {
            "number": "Número",
            "label": "Bloque",
            "notes": "Notas",
            "reason": "Motivo",
            "first_name": "Nombre",
            "surname": "Primer apellido",
            "second_surname": "Segundo apellido",
            "employee_number": "ID de empleado",
            "email": "Correo",
            "department": "Departamento",
            "shift": "Turno",
            "condition": "Estado",
            "x": "Posición X",
            "y": "Posición Y",
            "outcome": "Resultado observado",
            "active": "Activo",
        }
        kind = {"employee": "employees", "block": "blocks", "locker": "lockers"}.get(action.split(".")[0])
        current = self.lookup(kind, payload.get("id")) if kind else None

        def translate(value):
            return OUTCOMES.get(value, STATES.get(value, value)) if isinstance(value, str) else str(value)

        for key, title in labels.items():
            if key in payload:
                rows.append(
                    (title, translate(payload[key]), translate(current[key]) if current and key in current else "—")
                )
        employee_id = payload.get("employee_id")
        if employee_id:
            employee = self.lookup("employees", employee_id)
            assigned = self.assignment_for(employee_id=employee_id)
            locker = self.lookup("lockers", assigned["locker_id"]) if assigned else None
            rows.append(
                (
                    "Empleado",
                    full_name(employee) if employee else "No encontrado",
                    "Casillero actual: " + locker["number"] if locker else "Sin asignación vigente",
                )
            )
        locker_id = payload.get("locker_id")
        if locker_id:
            locker = self.lookup("lockers", locker_id)
            assigned = self.assignment_for(locker_id=locker_id)
            occupant = self.lookup("employees", assigned["employee_id"]) if assigned else None
            rows.append(
                (
                    "Casillero solicitado",
                    locker["number"] if locker else "No encontrado",
                    "Asignado a " + full_name(occupant)
                    if occupant
                    else STATES.get(locker["condition"], locker["condition"])
                    if locker
                    else "No encontrado",
                )
            )
        if action == "inventory.import":
            rows.append(
                (
                    "Lote",
                    str(len(payload.get("operations", []))) + " bloques",
                    "El lote no se aplicó. Revisa numeración y ubicaciones antes de prepararlo de nuevo.",
                )
            )
        if current and current.get("deleted_at"):
            rows.append(("Registro", "Modificar registro", "Eliminado del inventario"))
        return rows

    def correct_conflict(self, item):
        """Open a fresh, explicit form. A rejected command/receipt is immutable."""
        action, p = item["command"]["action"], item["command"]["payload"]
        if action.startswith("cut."):
            if action == "cut.create":
                return self.new_cut()
            return self.open_cut(p.get("id"))
        if action in ("assignment.assign", "assignment.transfer"):
            return self.employee_assignment(p.get("employee_id"))
        if action == "employee.update":
            return self.employee_form(True, p.get("id"))
        if action == "assignment.release":
            assigned = self.assignment_for(employee_id=p.get("employee_id"))
            if assigned:
                return self.release(assigned)
        if action == "inspection.record":
            round = self.lookup("inspection_rounds", p.get("round_id"))
            locker = self.lookup("lockers", p.get("locker_id"))
            entry = next(
                (
                    e
                    for e in self.data.get("inspection_entries", [])
                    if e["round_id"] == p.get("round_id") and e["locker_id"] == p.get("locker_id")
                ),
                None,
            )
            if round and locker and not round["completed_at"]:
                return self.record_inspection(round, locker, entry)
        kind = action.split(".")[0]
        current = self.lookup({"block": "blocks", "locker": "lockers"}.get(kind, ""), p.get("id"))
        if current and not current.get("deleted_at"):
            if action == "block.update" and self.allowed("admin"):
                return self.block_form(current)
            if action == "locker.update":
                return self.locker_dialog(current["id"])
            if action in ("block.delete", "locker.delete") and self.allowed("admin"):
                return self.delete_inventory(kind, current)
        info(
            self,
            "Esta operación requiere revisar su sección de origen. El resultado original se conserva. "
            "Para un lote, vuelve a prepararlo en Inventario o Crear fila; para una revisión cerrada, inicia otra.",
        )

    def resolve_conflict(self):
        from .window import local_date

        item = next(
            (q for q in self.store.queue(self.session["actor"]["id"]) if q["id"] == self.selected(self.queue_table)),
            None,
        )
        if not item or item["status"] not in ("conflicto", "rechazada"):
            return
        dialog = QDialog(self)
        dialog.setWindowTitle("Revisar conflicto")
        dialog.resize(1000, 550)
        layout = QVBoxLayout(dialog)
        header = QLabel()
        header.setWordWrap(True)
        layout.addWidget(header)
        table = self.table(layout, ["Dato", "Solicitud original", "Última información recibida"])
        status = QLabel()
        status.setWordWrap(True)
        layout.addWidget(status)

        def replacements():
            return [
                q
                for q in self.store.queue(self.session["actor"]["id"])
                if q["command"]["payload"].get("resolves_command_id") == item["id"]
            ]

        def update():
            header.setText(
                "Información recibida: "
                + local_date(self.data.get("at"))
                + ". Sincroniza antes de decidir. La solicitud original se conserva; "
                "la corrección requiere revisar y guardar un formulario nuevo."
            )
            self.fill(table, [(str(i), row) for i, row in enumerate(self.conflict_context(item))])
            table.resizeRowsToContents()
            related = replacements()
            status.setText(
                "Corrección más reciente: " + related[-1]["status"] + " · " + related[-1]["message"]
                if related
                else "Todavía no se ha enviado una corrección desde este asistente."
            )
            correct.setEnabled(
                self.allowed("editor")
                and not any(
                    q["status"] in ("pendiente", "requiere_sesion", "error_temporal", "confirmada") for q in related
                )
            )

        def correct():
            # Recheck immediately: a previous correction can finish while the dialog is open.
            if any(
                q["status"] in ("pendiente", "requiere_sesion", "error_temporal", "confirmada") for q in replacements()
            ):
                return
            self.resolving_command = item["id"]
            try:
                self.correct_conflict(item)
            finally:
                self.resolving_command = None
            update()

        buttons = QHBoxLayout()
        layout.addLayout(buttons)
        self.button(buttons, "Sincronizar información", self.sync)
        correct = self.button(buttons, "Preparar corrección", correct)
        self.button(buttons, "Cerrar", dialog.accept)
        timer = QTimer(dialog)
        timer.timeout.connect(update)
        timer.start(1500)
        update()
        dialog.exec()
        timer.stop()

    def start_block_row(self, position=None):
        if not self.allowed("admin") or not self.map.plan:
            return
        if self.map.dirty or self.map.shapes != self.map.plan["polygons"]:
            info(self, "Guarda los cambios del mapa antes de crear una fila.")
            return
        self.nav.setCurrentRow(1)
        self.map.hide_card()
        self.map.editing = True  # Keep automatic refresh from discarding the picked points.
        self.map.moves.clear()
        self.map.picking_row = True
        self.map.row_start = position
        self.map.setToolTip("Marca el inicio y el final de la fila. Clic derecho para cancelar.")
        self.statusBar().showMessage(
            "Marca el final de la fila." if position else "Marca inicio y final de la fila. Clic derecho cancela."
        )

    def cancel_block_row(self):
        self.map.picking_row = False
        self.map.row_start = None
        self.map.setToolTip("")
        self.map.set_editing(False)
        self.edit_map.setChecked(False)
        self.consult_map.setChecked(True)
        self.statusBar().clearMessage()

    def create_block_row(self, start, end):
        plan_id = self.map.plan["id"]
        self.cancel_block_row()
        fields = [
            ("building_id", "Edificio", [(b["name"], b["id"]) for b in self.data["buildings"]]),
            ("side", "Lado", [("Norte", "N"), ("Sur", "S"), ("Este", "E"), ("Oeste", "O")]),
            ("location", "Ubicación", [("Exterior", "EXT"), ("Interior", "INT")]),
            ("count", "Cantidad de bloques", "int"),
            ("prefix", "Prefijo del bloque", "line"),
            ("first_label", "Inicio del nombre", "line"),
            ("first_number", "Primer casillero", "line"),
            ("rows", "Filas por bloque", "int"),
            ("columns", "Columnas por bloque", "int"),
            *numbering_fields(),
            ("rotation", "Rotación de etiquetas", "float"),
        ]
        form = Form(
            "Crear fila de bloques",
            fields,
            {**self.new_block_defaults(), "first_label": "01"},
            self,
            description="Los bloques se distribuyen entre ambos puntos. Los existentes conservan su numeración y lado registrado; restaura primero los eliminados. El lado y el orden de numeración elegidos se aplican a los nuevos.",
            accept_label="Vista previa",
        )
        bind_order_combos(form.widgets["numbering_first"], form.widgets["numbering_second"])
        form.widgets["count"].setRange(1, 200)
        form.widgets["count"].setValue(self.preferences["block"]["count"])
        form.widgets["rotation"].setRange(-360, 360)
        while form.exec() == QDialog.DialogCode.Accepted:
            try:
                operations = plan_row(self.data, plan_id, start, end, form.values())
            except ValueError as exc:
                info(self, str(exc))
                continue
            preview = QDialog(self)
            preview.setWindowTitle("Revisar fila antes de crear")
            preview.resize(1000, 700)
            layout = QVBoxLayout(preview)
            summary = QLabel(
                f"{len(operations)} bloques · "
                f"{sum(op['action'] == 'block.create' for op in operations)} nuevos · "
                f"{sum(op['action'] == 'block.update' for op in operations)} existentes a reubicar. "
                "Se aplicará todo o nada; se conserva la numeración y el lado de los existentes."
            )
            summary.setWordWrap(True)
            layout.addWidget(summary)
            data = copy.deepcopy(self.data)
            moved = {op["payload"].get("id") for op in operations if op["action"] == "block.update"}
            data["blocks"] = [b for b in data["blocks"] if b["id"] not in moved]
            for i, op in enumerate(operations):
                data["blocks"].append(dict(op["payload"], id=op["payload"].get("id", f"preview-row-{i}"), version=1))
            view = MapView()
            view.set_satellite(self.preferences["satellite"])
            view.render(data, plan_id)
            layout.addWidget(view, 2)
            table = self.table(layout, ["Bloque", "Acción", "Lado", "Desde", "Hasta", "X", "Y"])
            self.fill(
                table,
                [
                    (
                        str(i),
                        [
                            p["label"],
                            "Reubicar" if op["action"] == "block.update" else "Crear",
                            {"N": "Norte", "S": "Sur", "E": "Este", "O": "Oeste"}[p["side"]],
                            min(p["numbers"], key=int),
                            max(p["numbers"], key=int),
                            p["x"],
                            p["y"],
                        ],
                    )
                    for i, op in enumerate(operations)
                    for p in [op["payload"]]
                ],
            )
            actions = QHBoxLayout()
            layout.addLayout(actions)
            self.button(actions, "Crear fila", preview.accept)
            self.button(actions, "Volver a editar", preview.reject)
            QTimer.singleShot(0, view.fit)
            if preview.exec() == QDialog.DialogCode.Accepted:
                versions = {key: value for op in operations for key, value in op.get("versions", {}).items()}
                self.submit("inventory.import", {"operations": operations}, versions)
                return

    def inspections_dialog(self):
        if not self.data.get("features", {}).get("inspections"):
            info(self, "Sincroniza con el servidor actualizado para abrir las revisiones físicas.")
            return
        from .window import local_date

        dialog = QDialog(self)
        dialog.setWindowTitle("Revisiones físicas")
        dialog.resize(1100, 700)
        layout = QVBoxLayout(dialog)
        top = QHBoxLayout()
        rounds, mode = QComboBox(), QComboBox()
        top.addWidget(rounds, 1)
        for title, key in [("Todos", "all"), ("Por revisar", "pending"), ("Discrepancias", "issues")]:
            mode.addItem(title, key)
        top.addWidget(mode)
        self.button(top, "Nueva revisión", self.new_inspection)
        layout.addLayout(top)
        summary = QLabel()
        layout.addWidget(summary)
        table = self.table(layout, ["Bloque", "Casillero", "Resultado", "Responsable", "Confirmado el", "Notas"])

        def entries():
            return {
                e["locker_id"]: e
                for e in self.data.get("inspection_entries", [])
                if e["round_id"] == rounds.currentData()
            }

        def pending_ids():
            return {
                q["command"]["payload"].get("locker_id")
                for q in self.store.queue(self.session["actor"]["id"])
                if q["command"]["action"] == "inspection.record"
                and q["command"]["payload"].get("round_id") == rounds.currentData()
                and q["status"] in ("pendiente", "requiere_sesion", "error_temporal")
            }

        def update():
            current = rounds.currentData()
            rounds.blockSignals(True)
            rounds.clear()
            for r in reversed(self.data.get("inspection_rounds", [])):
                rounds.addItem(r["title"] + (" · Cerrada" if r["completed_at"] else " · En curso"), r["id"])
            if rounds.findData(current) >= 0:
                rounds.setCurrentIndex(rounds.findData(current))
            rounds.blockSignals(False)
            round = self.lookup("inspection_rounds", rounds.currentData())
            found, pending, rows = entries(), pending_ids(), []
            for id in round["locker_ids"] if round else []:
                locker = self.lookup("lockers", id) or {}
                block = self.lookup("blocks", locker.get("block_id")) or {}
                entry = found.get(id)
                if mode.currentData() == "pending" and entry and id not in pending:
                    continue
                if mode.currentData() == "issues" and (not entry or entry["outcome"] not in DISCREPANCIES):
                    continue
                actor = self.lookup("admins", entry["actor_id"]) if entry else None
                rows.append(
                    (
                        id,
                        [
                            block.get("label", ""),
                            locker.get("number", id),
                            "Por sincronizar"
                            if id in pending
                            else OUTCOMES[entry["outcome"]]
                            if entry
                            else "Por revisar",
                            (actor or {}).get("name", ""),
                            local_date(entry["at"]) if entry else "",
                            entry["notes"] if entry else "",
                        ],
                    )
                )
            rows.sort(
                key=lambda row: (
                    row[1][0],
                    (self.lookup("lockers", row[0]) or {}).get("row", 0),
                    (self.lookup("lockers", row[0]) or {}).get("column", 0),
                )
            )
            self.fill(table, rows)
            summary.setText(
                f"{len(found)}/{len(round['locker_ids']) if round else 0} revisados · {len(pending)} por sincronizar. Doble clic o clic derecho para registrar."
            )

        def record_selected():
            round = self.lookup("inspection_rounds", rounds.currentData())
            locker = self.lookup("lockers", self.selected(table))
            if not round or not locker:
                return
            if locker["id"] in pending_ids():
                info(self, "Ya hay una observación pendiente para este casillero. Espera su confirmación.")
                return
            self.record_inspection(round, locker, entries().get(locker["id"]))
            update()

        def complete():
            round = self.lookup("inspection_rounds", rounds.currentData())
            if not round or round["completed_at"] or not self.allowed("editor"):
                return
            if pending_ids() or len(entries()) != len(round["locker_ids"]):
                info(self, "Revisa todos los casilleros y sincroniza las observaciones antes de cerrar.")
                return
            if confirm(self, "¿Cerrar la revisión? Las discrepancias se conservan y deben resolverse por separado."):
                self.submit(
                    "inspection.complete", {"round_id": round["id"]}, self.versions(("inspection_round", round))
                )

        def export():
            path, _ = QFileDialog.getSaveFileName(
                dialog, "Exportar revisión visible", "revision-fisica.csv", "CSV (*.csv)"
            )
            if path:
                from .window import csv_safe

                try:
                    with open(path, "w", newline="", encoding="utf-8-sig") as stream:
                        writer = csv.writer(stream)
                        writer.writerow([table.horizontalHeaderItem(c).text() for c in range(table.columnCount())])
                        writer.writerows(
                            [
                                [csv_safe(table.item(r, c).text()) for c in range(table.columnCount())]
                                for r in range(table.rowCount())
                            ]
                        )
                except OSError as exc:
                    info(self, "No se pudo exportar: " + str(exc))

        table.cellDoubleClicked.connect(lambda r, c: record_selected())
        table.context_actions = lambda key: [("Registrar revisión", record_selected, "editor")]
        bottom = QHBoxLayout()
        layout.addLayout(bottom)
        self.button(bottom, "Registrar resultado", record_selected)
        self.button(bottom, "Exportar vista CSV", export)
        self.button(bottom, "Cerrar revisión", complete)
        self.button(bottom, "Salir", dialog.accept)
        rounds.currentIndexChanged.connect(lambda: update())
        mode.currentIndexChanged.connect(lambda: update())
        timer = QTimer(dialog)
        timer.timeout.connect(update)
        timer.start(1500)
        update()
        dialog.exec()
        timer.stop()

    def new_inspection(self):
        if not self.allowed("editor"):
            return
        form = Form(
            "Nueva revisión física",
            [
                ("title", "Nombre", "line"),
                ("building_id", "Edificio", [("Todos", "")] + [(b["name"], b["id"]) for b in self.data["buildings"]]),
                ("side", "Lado", [("Todos", ""), ("Norte", "N"), ("Sur", "S"), ("Este", "E"), ("Oeste", "O")]),
                (
                    "block_id",
                    "Bloque",
                    [("Todos", "")]
                    + [
                        (self.lookup("buildings", b["building_id"])["code"] + " · " + b["label"], b["id"])
                        for b in self.data["blocks"]
                    ],
                ),
            ],
            {"title": "Revisión " + datetime.now().strftime("%d/%m/%Y")},
            self,
            description="El recorrido conserva los casilleros seleccionados y puede retomarse desde cualquier equipo tras sincronizar.",
        )
        if form.exec() == QDialog.DialogCode.Accepted:
            p = form.values()
            blocks = {
                b["id"]
                for b in self.data["blocks"]
                if (not p["building_id"] or b["building_id"] == p["building_id"])
                and (not p["side"] or b["side"] == p["side"])
                and (not p["block_id"] or b["id"] == p["block_id"])
            }
            ids = [x["id"] for x in self.data["lockers"] if x["block_id"] in blocks]
            if not ids or not p["title"].strip():
                info(self, "Escribe un nombre y selecciona un conjunto con casilleros.")
                return
            self.submit("inspection.create", {"title": p["title"], "locker_ids": ids})

    def record_inspection(self, round, locker, entry=None):
        if not self.allowed("editor") or round["completed_at"]:
            return
        from .window import full_name

        assignment = self.assignment_for(locker_id=locker["id"])
        employee = self.lookup("employees", assignment["employee_id"]) if assignment else None
        form = Form(
            "Revisar casillero " + locker["number"],
            [
                (
                    "outcome",
                    "Resultado observado",
                    [("Selecciona un resultado", "")] + [(v, k) for k, v in OUTCOMES.items()],
                ),
                ("notes", "Observaciones", "text"),
            ],
            entry,
            self,
            description=("Asignado a " + full_name(employee) if employee else "Sin asignación registrada")
            + ". Vacío y utilizable habilita su asignación solo si no tiene ocupante registrado. Las discrepancias no liberan asignaciones.",
        )
        if form.exec() == QDialog.DialogCode.Accepted:
            p = form.values()
            if not p["outcome"] or (p["outcome"] in DISCREPANCIES and not p["notes"].strip()):
                info(self, "Selecciona el resultado y describe las discrepancias.")
                return
            self.submit(
                "inspection.record",
                dict(p, round_id=round["id"], locker_id=locker["id"], entry_id=entry["id"] if entry else None),
                self.versions(("locker", locker), *([("inspection_entry", entry)] if entry else [])),
            )
