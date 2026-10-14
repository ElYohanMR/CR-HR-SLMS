"""Editable workstation drafts; mailto opens a composer and never confirms delivery."""
import re
from urllib.parse import quote, urlencode

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QApplication, QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLineEdit,
    QPlainTextEdit, QLabel, QPushButton, QMessageBox,
)


def addresses(value):
    parts = [p.strip() for p in re.split(r"[,;]", value) if p.strip()]
    if len(parts) > 20 or any(not re.fullmatch(r"[^\s@,;<>?#%]+@[^\s@,;<>?#%]+\.[^\s@,;<>?#%]+", p) for p in parts):
        raise ValueError("Revisa los correos. Separa varias direcciones con punto y coma.")
    return list(dict.fromkeys(parts))


def mailto_url(values):
    to, cc = addresses(values["recipient"]), addresses(values["cc"])
    if not to:
        raise ValueError("Escribe al menos un destinatario.")
    subject = values["subject"]
    if not subject.strip() or any(c in subject for c in ("\r", "\n", "\x00")):
        raise ValueError("Escribe un asunto válido en una sola línea.")
    if not values["body"].strip():
        raise ValueError("Escribe el cuerpo del mensaje.")
    query = urlencode({"cc": ",".join(cc), "subject": subject,
                       "body": values["body"].replace("\r\n", "\n").replace("\n", "\r\n")}, quote_via=quote)
    url = "mailto:" + quote(",".join(to), safe="@,") + "?" + query
    if len(url) > 8000:
        raise ValueError("El mensaje es demasiado largo para abrirlo por enlace. Copia los campos en tu correo.")
    return url


def original_draft(notification):
    # Earlier releases included simulation metadata in the message body.
    body = notification["body"].removesuffix("\n\nSIMULACIÓN: este correo no se ha enviado.")
    return {"recipient": notification["recipient"], "cc": "; ".join(notification.get("cc", [])),
            "subject": notification["subject"], "body": body}


class MailPreview(QDialog):
    def __init__(self, window, notification):
        super().__init__(window)
        self.setWindowTitle("Vista previa del correo")
        self.resize(780, 650)
        self.store = window.store
        self.key = "mail-draft:" + window.session["actor"]["id"] + ":" + notification["id"]
        self.original = original_draft(notification)
        self.saved = self.store.get(self.key) or dict(self.original)
        self.widgets = {}
        layout = QVBoxLayout(self)
        title = QLabel("Vista previa del correo")
        title.setObjectName("title")
        layout.addWidget(title)
        note = QLabel("Borrador editable · Guardado local por cuenta. El envío externo no tiene seguimiento en SLMS.")
        note.setWordWrap(True)
        layout.addWidget(note)
        form = QFormLayout()
        layout.addLayout(form, 1)
        for key, label in (("recipient", "Para"), ("cc", "CC"), ("subject", "Asunto"), ("body", "Mensaje")):
            field = QPlainTextEdit() if key == "body" else QLineEdit()
            if key != "body":
                field.setMaxLength(500 if key == "subject" else 2000)
            else:
                field.setMinimumHeight(230)
            field.setAccessibleName(label)
            self.widgets[key] = field
            row = QHBoxLayout()
            row.addWidget(field, 1)
            copy = QPushButton("Copiar")
            copy.setAccessibleName("Copiar " + label.lower())
            copy.clicked.connect(lambda checked=False, k=key: QApplication.clipboard().setText(self.values()[k]))
            row.addWidget(copy)
            form.addRow(label, row)
        self.fill(self.saved)
        self.status = QLabel("")
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        actions = QHBoxLayout()
        layout.addLayout(actions)
        self.save_button = QPushButton("Guardar borrador")
        self.save_button.clicked.connect(self.save)
        actions.addWidget(self.save_button)
        reset = QPushButton("Restablecer mensaje")
        reset.clicked.connect(lambda: self.fill(self.original))
        actions.addWidget(reset)
        self.open_button = QPushButton("Abrir en correo")
        self.open_button.setToolTip("Abre Outlook si es tu aplicación de correo predeterminada. Revisa el mensaje y pulsa Enviar allí.")
        self.open_button.clicked.connect(self.open_mail)
        actions.addWidget(self.open_button)
        graph = QPushButton("Enviar con Microsoft")
        graph.setEnabled(False)
        graph.setToolTip("Pendiente de integración y habilitación por TI.")
        actions.addWidget(graph)
        layout.addWidget(QLabel("Envío automático con Microsoft: pendiente de habilitación por TI."))
        close = QPushButton("Cerrar")
        close.clicked.connect(self.reject)
        layout.addWidget(close)
        self.editor = window.session["actor"]["role"] in ("admin", "operator")
        self.open_button.setEnabled(self.editor)

    def values(self):
        return {k: w.toPlainText() if isinstance(w, QPlainTextEdit) else w.text()
                for k, w in self.widgets.items()}

    def fill(self, values):
        for k, w in self.widgets.items():
            if isinstance(w, QPlainTextEdit):
                w.setPlainText(values[k])
            else:
                w.setText(values[k])

    def save(self):
        values = self.values()
        if len(values["body"]) > 20000:
            QMessageBox.warning(self, "Borrador", "El mensaje admite hasta 20 000 caracteres.")
            return False
        self.store.put(self.key, values)
        self.saved = dict(values)
        self.status.setText("Borrador guardado. No se ha enviado desde SLMS.")
        return True

    def open_mail(self):
        if not self.editor:
            self.status.setText("La cuenta de consulta no puede abrir mensajes para envío.")
            return
        try:
            url = mailto_url(self.values())
        except ValueError as exc:
            QMessageBox.warning(self, "Revisa el correo", str(exc))
            return
        if not self.save():
            return
        if QDesktopServices.openUrl(QUrl(url)):
            self.status.setText("Se solicitó abrir el borrador en tu aplicación de correo. El envío se realiza allí.")
        else:
            self.status.setText("No se pudo abrir una aplicación de correo. Puedes copiar los campos manualmente.")

    def reject(self):
        if self.values() != self.saved:
            choice = QMessageBox.question(self, "Borrador sin guardar", "¿Guardar los cambios antes de cerrar?",
                QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Save)
            if choice == QMessageBox.StandardButton.Cancel:
                return
            if choice == QMessageBox.StandardButton.Save and not self.save():
                return
        super().reject()

    def closeEvent(self, event):
        event.ignore()
        self.reject()
