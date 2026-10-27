"""Reception/HR padlock cutting desk, using the existing durable command queue."""
import base64
from datetime import timezone
from pathlib import Path

import httpx
from PySide6.QtCore import Qt, QTimer, QDateTime, QBuffer, QByteArray, QIODevice
from PySide6.QtGui import QPixmap, QImageReader
from PySide6.QtWidgets import (
    QComboBox, QDateTimeEdit, QDialog, QHBoxLayout, QLabel, QLineEdit,
    QScrollArea, QTextEdit, QVBoxLayout, QWidget,
)
from .cuts import CHANNELS, EVIDENCE, STATUSES, MAX_PHOTO, validate_photo
from .forms import Form, info


def photo_pixmap(content):
    buffer = QBuffer()
    buffer.setData(QByteArray(content))
    buffer.open(QIODevice.OpenModeFlag.ReadOnly)
    reader = QImageReader(buffer)
    reader.setAutoTransform(True)
    return QPixmap.fromImage(reader.read())


class CutWorkflows:
    def make_cuts(self):
        layout = self.page("Solicitudes de corte de candado",
                           "Solicitada → En proceso → Finalizada. Recepción o HR registra cada paso y sus evidencias.")
        row = QHBoxLayout()
        self.cut_search = QLineEdit()
        self.cut_search.setPlaceholderText("Empleado, ID, casillero, supervisor o encargado…")
        row.addWidget(self.cut_search, 1)
        self.cut_filter = QComboBox()
        self.cut_filter.addItem("Todos los estados", "")
        for key, title in STATUSES.items():
            self.cut_filter.addItem(title, key)
        row.addWidget(self.cut_filter)
        self.cut_create_button = self.button(row, "Nueva solicitud", self.new_cut)
        self.cut_create_button.setProperty("primary", True)
        self.button(row, "Abrir solicitud", self.open_cut)
        layout.addLayout(row)
        self.cut_notice = QLabel()
        self.cut_notice.setWordWrap(True)
        layout.addWidget(self.cut_notice)
        self.cut_table = self.table(layout, ["Creada", "Estado", "ID empleado", "Empleado",
                                             "Casillero", "Supervisor", "Encargado"])
        self.cut_table.cellDoubleClicked.connect(lambda *_: self.open_cut())
        self.cut_table.context_actions = lambda key: [("Abrir solicitud de corte", lambda: self.open_cut(key), None)]
        self.cut_search.textChanged.connect(self.refresh_cuts)
        self.cut_filter.currentIndexChanged.connect(self.refresh_cuts)

    def refresh_cuts(self, *_, queue=None):
        from .window import local_date
        query, state = self.cut_search.text().strip().casefold(), self.cut_filter.currentData()
        rows = []
        for item in sorted(self.data.get("cut_requests", []), key=lambda x: x["created_at"], reverse=True):
            ref = item["reference"]
            values = [local_date(item["created_at"]), STATUSES[item["status"]], ref["employee_number"],
                      ref["employee_name"], ref["location"], item["supervisor"], item["assignee"] or "Sin asignar"]
            if (not state or state == item["status"]) and (not query or query in " ".join(values).casefold()):
                rows.append((item["id"], values))
        self.fill(self.cut_table, rows)
        ready = self.data.get("features", {}).get("padlock_cuts", False)
        self.cut_create_button.setEnabled(ready and self.allowed("editor"))
        if queue is None:
            queue = self.store.queue(self.session["actor"]["id"])
        pending = sum(q["command"]["action"].startswith("cut.") and q["status"] != "confirmada" for q in queue)
        self.cut_notice.setText(f"Cambios pendientes de confirmación: {pending}."
                               if ready else "Actualiza la conexión para utilizar este apartado.")
        self.cut_notice.setVisible(bool(pending) or not ready)

    def cut_pending(self, id):
        return any(q["command"]["action"].startswith("cut.") and q["command"]["payload"].get("id") == id
                   and q["status"] in ("pendiente", "requiere_sesion", "error_temporal")
                   for q in self.store.queue(self.session["actor"]["id"]))

    def cut_submit(self, item, action, payload):
        if self.cut_pending(item["id"]):
            info(self, "Hay un cambio pendiente para esta solicitud. Sincroniza o revisa Solicitudes antes de continuar.")
            return None
        request_id = self.submit(action, dict(payload, id=item["id"]), self.versions(("cut_request", item)))
        self.refresh_cuts()
        return request_id

    def cut_form(self, item=None):
        from .window import full_name
        fields = []
        if item is None:
            fields = [
                ("employee_id", "Empleado que requiere el corte", [("Selecciona al empleado", None)] +
                 [(f"{e['employee_number']} · {full_name(e)}", e["id"])
                  for e in self.data["employees"] if e["active"]]),
                ("locker_id", "Casillero que requiere el corte", [("Selecciona el casillero", None)] +
                 [(self.locker_code(e), e["id"]) for e in self.data["lockers"]]),
            ]
        fields += [("supervisor", "Supervisor que solicita", "line"),
                   ("channel", "Recibida por", [(label, key) for key, label in CHANNELS.items()]),
                   ("reason", "Motivo del corte", "text")]
        form = Form("Editar solicitud" if item else "Nueva solicitud de corte de candado", fields,
                    item or {"channel": "teams"}, self,
                    description="Al confirmarse la solicitud, el casillero queda en mantenimiento hasta finalizar o cancelar el corte. La asignación del empleado se conserva.")
        if item is None:
            def choose_locker():
                employee_id = form.widgets["employee_id"].currentData()
                assignment = self.assignment_for(employee_id=employee_id) if employee_id else None
                combo = form.widgets["locker_id"]
                combo.setCurrentIndex(max(0, combo.findData(assignment["locker_id"])) if assignment else 0)
            form.widgets["employee_id"].currentIndexChanged.connect(choose_locker)
        return form

    def new_cut(self):
        if not self.allowed("editor") or not self.data.get("features", {}).get("padlock_cuts"):
            return
        form = self.cut_form()
        while form.exec() == QDialog.DialogCode.Accepted:
            p = form.values()
            if not p.get("employee_id") or not p.get("locker_id") or not p["supervisor"].strip() or not p["reason"].strip():
                info(self, "Completa empleado, supervisor, casillero y motivo.")
                continue
            if len(p["supervisor"].strip()) > 200 or len(p["reason"].strip()) > 2000:
                info(self, "El supervisor admite 200 caracteres y el motivo 2000.")
                continue
            versions = self.versions(("employee", self.lookup("employees", p["employee_id"])),
                                     ("locker", self.lookup("lockers", p["locker_id"])))
            self.submit("cut.create", p, versions)
            self.refresh_cuts()
            return

    def open_cut(self, id=None):
        id = id if isinstance(id, str) else self.selected(self.cut_table)
        if self.lookup("cut_requests", id):
            CutDialog(self, id).exec()
        else:
            info(self, "Selecciona una solicitud confirmada en la lista.")

    def edit_cut(self, item):
        form = self.cut_form(item)
        while form.exec() == QDialog.DialogCode.Accepted:
            p = form.values()
            if not p["supervisor"].strip() or not p["reason"].strip() or len(p["reason"]) > 2000 or len(p["supervisor"]) > 200:
                info(self, "Completa supervisor (hasta 200 caracteres) y motivo (hasta 2000).")
                continue
            return self.cut_submit(item, "cut.update", p)

    def assign_cut(self, item):
        fields = [("assignee", "Encargado de realizar el corte", "line")]
        if item["assignee"]:
            fields.append(("reason", "Motivo del cambio de encargado", "text"))
        form = Form("Asignar encargado", fields, item, self,
                    description="Identifica a la persona de Seguridad u otro responsable que realizará el corte. La solicitud pasará a En proceso.")
        while form.exec() == QDialog.DialogCode.Accepted:
            p = form.values()
            if not p["assignee"].strip() or len(p["assignee"]) > 200 or (item["assignee"] and not p["reason"].strip()):
                info(self, "Escribe el nombre del encargado y, si cambia, el motivo.")
                continue
            return self.cut_submit(item, "cut.assign", p)

    def attach_cut_photo(self, item, kind):
        from PySide6.QtWidgets import QFileDialog
        path, _ = QFileDialog.getOpenFileName(self, EVIDENCE[kind], "", "Fotografías (*.jpg *.jpeg *.png)")
        if not path:
            return
        try:
            if Path(path).stat().st_size > MAX_PHOTO:
                raise ValueError("La fotografía debe ocupar como máximo 6 MB.")
            content = Path(path).read_bytes()
            validate_photo(content)
        except (OSError, ValueError) as exc:
            info(self, str(exc))
            return
        previous = any(e["request_id"] == item["id"] and e["kind"] == kind and e["current"]
                       for e in self.data.get("cut_evidence", []))
        form = Form("Confirmar fotografía", [("reason", "Motivo de sustitución", "text")] if previous else [],
                    parent=self, description=EVIDENCE[kind] + ". La imagen original se conservará en el expediente.",
                    accept_label="Adjuntar")
        preview = QLabel()
        pix = photo_pixmap(content)
        preview.setPixmap(pix.scaled(480, 250, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        form.form_layout.addRow(preview)
        while form.exec() == QDialog.DialogCode.Accepted:
            p = form.values()
            if previous and not p["reason"].strip():
                info(self, "Indica por qué sustituyes la fotografía.")
                continue
            return self.cut_submit(item, "cut.evidence",
                                   dict(p, kind=kind, filename=Path(path).name,
                                        photo=base64.b64encode(content).decode("ascii")))

    def complete_cut(self, item):
        if not self.data.get("features", {}).get("optional_cut_photos", False):
            info(self, "Actualiza el servidor para finalizar solicitudes con fotografías opcionales.")
            return
        form = Form("Finalizar corte de candado",
                    [("result", "Detalle del corte realizado", "text"),
                     ("identity_verified", "Empleado presente e identidad verificada con Samtec ID", "bool")],
                    parent=self, description=f"Encargado: {item['assignee']}",
                    accept_label="Finalizar solicitud")
        date = QDateTimeEdit(QDateTime.currentDateTime(), form)
        date.setCalendarPopup(True)
        date.setDisplayFormat("dd/MM/yyyy HH:mm:ss")
        form.form_layout.insertRow(0, "Fecha y hora real del corte (hora de este equipo)", date)
        while form.exec() == QDialog.DialogCode.Accepted:
            p = form.values()
            if not p["identity_verified"] or not p["result"].strip() or len(p["result"]) > 4000:
                info(self, "Confirma identidad y presencia; describe el resultado (hasta 4000 caracteres).")
                continue
            p["performed_at"] = date.dateTime().toPython().astimezone(timezone.utc).isoformat()
            return self.cut_submit(item, "cut.complete", p)

    def cancel_cut(self, item):
        form = Form("Cancelar solicitud de corte", [("reason", "Motivo de cancelación", "text")],
                    parent=self, description="Se conservarán la solicitud, sus cambios y las evidencias adjuntas.",
                    accept_label="Confirmar cancelación")
        while form.exec() == QDialog.DialogCode.Accepted:
            p = form.values()
            if not p["reason"].strip() or len(p["reason"]) > 2000:
                info(self, "Escribe el motivo (hasta 2000 caracteres).")
                continue
            return self.cut_submit(item, "cut.cancel", p)

    def view_cut_photo(self, id):
        try:
            response = httpx.get(self.config["url"] + "/cuts/evidence/" + id,
                                 headers={"Authorization": "Bearer " + self.session["token"]},
                                 timeout=8, trust_env=False)
            response.raise_for_status()
            pix = photo_pixmap(response.content)
            if pix.isNull():
                raise ValueError("No se pudo leer la fotografía.")
        except (httpx.HTTPError, ValueError):
            info(self, "No se pudo abrir la evidencia. Revisa la conexión y la sesión; requiere acceso de Operación o Administración.")
            return
        dialog = QDialog(self)
        dialog.setWindowTitle("Evidencia del corte de candado")
        layout = QVBoxLayout(dialog)
        label = QLabel()
        available = self.screen().availableGeometry()
        label.setPixmap(pix.scaled(int(available.width() * .75), int(available.height() * .75),
                                   Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        layout.addWidget(label)
        self.button(layout, "Cerrar", dialog.accept)
        dialog.exec()


class CutDialog(QDialog):
    def __init__(self, window, id):
        super().__init__(window)
        self.window, self.id, self.signature = window, id, None
        self.setWindowTitle("Expediente de corte de candado")
        self.resize(950, 740)
        outer = QVBoxLayout(self)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        layout = QVBoxLayout(content)
        scroll.setWidget(content)
        outer.addWidget(scroll)
        self.heading = QLabel()
        self.heading.setObjectName("title")
        layout.addWidget(self.heading)
        self.detail = QTextEdit()
        self.detail.setReadOnly(True)
        self.detail.setMinimumHeight(190)
        layout.addWidget(self.detail)
        self.pending = QLabel()
        self.pending.setWordWrap(True)
        layout.addWidget(self.pending)
        row = QHBoxLayout()
        self.actions = {}
        for key, title, method in [("edit", "Editar datos", window.edit_cut),
                                    ("assign", "Asignar encargado", window.assign_cut),
                                    ("complete", "Finalizar", window.complete_cut),
                                    ("cancel", "Cancelar solicitud", window.cancel_cut)]:
            button = window.button(row, title, lambda checked=False, fn=method: fn(self.item()))
            self.actions[key] = button
        layout.addLayout(row)
        layout.addWidget(QLabel("Fotografías opcionales · JPG o PNG · hasta 6 MB por archivo"))
        self.photo_buttons = {}
        for key, title in EVIDENCE.items():
            row = QHBoxLayout()
            label = QLabel(title)
            label.setWordWrap(True)
            row.addWidget(label, 1)
            button = window.button(row, "Adjuntar fotografía", lambda checked=False, k=key: window.attach_cut_photo(self.item(), k))
            self.photo_buttons[key] = button
            layout.addLayout(row)
        self.photos = window.table(layout, ["Tipo", "Archivo", "Vigencia", "Registrada", "Registró"])
        self.photos.setMinimumHeight(155)
        self.photos.context_actions = lambda key: [("Ver fotografía", lambda: window.view_cut_photo(key), "editor")]
        self.photos.cellDoubleClicked.connect(lambda *_: window.view_cut_photo(window.selected(self.photos)))
        self.photos.setToolTip("Doble clic para ver la fotografía. Las versiones sustituidas se conservan.")
        foot = QHBoxLayout()
        window.button(foot, "Ver historial de la solicitud", self.history)
        window.button(foot, "Cerrar", self.accept)
        outer.addLayout(foot)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self.timer.start(400)
        self.finished.connect(self.timer.stop)
        self.refresh()

    def item(self):
        return self.window.lookup("cut_requests", self.id)

    def refresh(self):
        from .window import local_date
        w, item = self.window, self.item()
        if not item:
            return
        pending = w.cut_pending(self.id)
        signature = (item["version"], pending, w.session["actor"]["id"], w.session["actor"]["role"])
        if signature == self.signature:
            return
        self.signature = signature
        ref = item["reference"]
        self.heading.setText("Corte de candado · " + STATUSES[item["status"]])
        def actor(id):
            return (w.lookup("admins", id) or {}).get("name", "—")
        self.detail.setPlainText(
            f"Empleado: {ref['employee_number']} · {ref['employee_name']}\n"
            f"Casillero: {ref['location']}\nSupervisor: {item['supervisor']} · Recibida por: {CHANNELS[item['channel']]}\n"
            f"Motivo: {item['reason']}\nEncargado del corte: {item['assignee'] or 'Sin asignar'}\n"
            f"Registrada: {local_date(item['created_at'])} · {actor(item['created_by'])}\n"
            f"Encargado asignado: {local_date(item['assigned_at'])}\n"
            f"Corte realizado: {local_date(item['performed_at'])}\n"
            f"Cierre registrado: {local_date(item['completed_at'])} · {actor(item['completed_by'])}\n"
            f"Resultado / cancelación: {item['result'] or 'Pendiente'}\nReferencia: {item['id']}"
        )
        self.pending.setText("Cambio pendiente de confirmación. Espera la sincronización; consulta Solicitudes si hay un error."
                             if pending else "")
        self.pending.setVisible(pending)
        editable = w.allowed("editor") and not pending and item["status"] in ("solicitada", "en_proceso")
        self.actions["edit"].setEnabled(editable and item["status"] == "solicitada")
        self.actions["assign"].setEnabled(editable)
        self.actions["assign"].setText("Cambiar encargado" if item["assignee"] else "Asignar encargado")
        self.actions["complete"].setEnabled(editable and item["status"] == "en_proceso")
        self.actions["cancel"].setEnabled(editable)
        evidence = [e for e in w.data.get("cut_evidence", []) if e["request_id"] == self.id]
        for key, button in self.photo_buttons.items():
            button.setEnabled(editable and item["status"] == "en_proceso")
            button.setText("Sustituir fotografía" if any(e["kind"] == key and e["current"] for e in evidence) else "Adjuntar fotografía")
        names = {"identidad": "Identidad", "antes": "Antes del corte", "despues": "Después del corte"}
        w.fill(self.photos, [(e["id"], [names[e["kind"]], e["filename"], "Actual" if e["current"] else "Sustituida",
                                      local_date(e["uploaded_at"]), actor(e["uploaded_by"])]) for e in evidence])

    def history(self):
        # Load this complete case directly; global snapshots only contain recent audit entries.
        w = self.window
        try:
            response = httpx.get(w.config["url"] + "/cuts/" + self.id + "/history",
                                 headers={"Authorization": "Bearer " + w.session["token"]}, timeout=8, trust_env=False)
            response.raise_for_status()
            events = response.json()
        except (httpx.HTTPError, ValueError):
            info(self, "Conecta al servidor para consultar el historial completo de esta solicitud.")
            return
        from .window import ACTIONS, local_date
        dialog = QDialog(self)
        dialog.setWindowTitle("Historial de la solicitud de corte")
        dialog.resize(950, 500)
        layout = QVBoxLayout(dialog)
        table = w.table(layout, ["Fecha", "Acción", "Registró", "Motivo"])
        w.fill(table, [(e["id"], [local_date(e["at"]), ACTIONS.get(e["action"], e["action"]),
                                 (w.lookup("admins", e["actor_id"]) or {}).get("name", "—"), e["reason"]]) for e in events])
        def detail():
            from .audit_ui import show_audit_detail
            event = next((e for e in events if e["id"] == w.selected(table)), None)
            if event:
                show_audit_detail(dialog, event, ACTIONS.get(event["action"], event["action"]))
        table.cellDoubleClicked.connect(lambda *_: detail())
        w.button(layout, "Cerrar", dialog.accept)
        dialog.exec()
