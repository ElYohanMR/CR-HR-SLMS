"""Capture the cutting desk using a fictitious, isolated case."""
import uuid
import base64
from PySide6.QtCore import QBuffer, QIODevice
from PySide6.QtGui import QImage, QColor
from PySide6.QtWidgets import QApplication
from fastapi.testclient import TestClient
from .api import create_app
from .config import home
from .cut_ui import CutDialog
from .models import now


def capture_cuts(window, engine, session):
    with TestClient(create_app(engine, demo=True)) as client:
        client.headers["Authorization"] = "Bearer " + session["token"]
        def send(action, payload, versions):
            result = client.post("/commands", json={
                "id": str(uuid.uuid4()), "device_id": "preview", "client_at": now(),
                "action": action, "payload": payload, "versions": versions,
            }).json()
            assert result["status"] == "confirmada", result
            window.data = client.get("/snapshot").json()
            window.refresh()
            return result
        window.data = client.get("/snapshot").json()
        window.refresh()
        form = window.cut_form()
        form.widgets["employee_id"].setCurrentIndex(1)
        form.widgets["locker_id"].setCurrentIndex(1)
        form.widgets["supervisor"].setText("Supervisora de ejemplo")
        form.widgets["reason"].setPlainText("Ejemplo ficticio: pérdida de las llaves del candado.")
        form.show()
        QApplication.processEvents()
        form.grab().save(str(home() / "corte-nueva.png"))
        p = form.values()
        form.close()
        result = send("cut.create", p, window.versions(
            ("employee", window.lookup("employees", p["employee_id"])),
            ("locker", window.lookup("lockers", p["locker_id"]))))
        id = result["target_id"]
        def mutate(action, p):
            return send(action, dict(p, id=id), window.versions(("cut_request", window.lookup("cut_requests", id))))
        mutate("cut.assign", {"assignee": "Encargado de seguridad · ejemplo"})
        # Synthetic color cards exercise validation; these are not real employee evidence.
        for kind, color in (("identidad", "orange"), ("antes", "gray"), ("despues", "green")):
            image = QImage(320, 240, QImage.Format.Format_RGB32)
            image.fill(QColor(color))
            buffer = QBuffer()
            buffer.open(QIODevice.OpenModeFlag.WriteOnly)
            assert image.save(buffer, "PNG")
            mutate("cut.evidence", {"kind": kind, "filename": "EJEMPLO-FICTICIO-" + kind + ".png",
                                    "photo": base64.b64encode(bytes(buffer.data())).decode()})
        window.nav.setCurrentRow(7)
        QApplication.processEvents()
        window.grab().save(str(home() / "cortes-lista.png"))
        dialog = CutDialog(window, id)
        dialog.show()
        QApplication.processEvents()
        dialog.grab().save(str(home() / "corte-expediente.png"))
        dialog.close()
        mutate("cut.complete", {"identity_verified": True, "performed_at": now(),
                                "result": "Demostración ficticia del cierre; no se realizó un corte real."})
        assert window.lookup("cut_requests", id)["status"] == "finalizada"
