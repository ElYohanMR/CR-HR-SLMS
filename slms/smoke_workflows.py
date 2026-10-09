"""Exercise the new dialogs with fictitious data in the smoke-test profile."""

import uuid
import copy

from PySide6.QtWidgets import QApplication, QDialog, QTableWidget, QPushButton
from PySide6.QtCore import Qt
from fastapi.testclient import TestClient

from .api import create_app
from .config import home
from .forms import Form
from .mapview import MapView
from .models import now


def capture_workflows(window, engine, session):
    locker = window.data["lockers"][1]
    with TestClient(create_app(engine, demo=True)) as client:
        client.headers["Authorization"] = "Bearer " + session["token"]
        result = client.post(
            "/commands",
            json={
                "id": str(uuid.uuid4()),
                "device_id": "preview",
                "client_at": now(),
                "action": "inspection.create",
                "payload": {
                    "title": "Recorrido de recepción · ejemplo",
                    "locker_ids": [x["id"] for x in window.data["lockers"]],
                },
                "versions": {},
            },
        ).json()
        assert result["status"] == "confirmada"
        result = client.post(
            "/commands",
            json={
                "id": str(uuid.uuid4()),
                "device_id": "preview",
                "client_at": now(),
                "action": "inspection.record",
                "payload": {
                    "round_id": result["target_id"],
                    "locker_id": locker["id"],
                    "outcome": "dano",
                    "notes": "Ejemplo ficticio: revisar bisagra.",
                },
                "versions": {"locker:" + locker["id"]: locker["version"]},
            },
        ).json()
        assert result["status"] == "confirmada"
        window.data = client.get("/snapshot").json()
        window.refresh()
    old_form, old_dialog = Form.exec, QDialog.exec
    calls = []

    def row_form(form):
        calls.append(True)
        form.widgets["count"].setValue(40)
        form.widgets["first_number"].setText("2000")
        form.widgets["prefix"].setText("E")
        return QDialog.DialogCode.Accepted if len(calls) == 1 else QDialog.DialogCode.Rejected

    def capture(dialog):
        names = {
            "Revisar fila antes de crear": "fila-bloques",
            "Revisiones físicas": "revisiones-fisicas",
            "Revisar conflicto": "conflictos",
        }
        dialog.show()
        QApplication.processEvents()
        if dialog.windowTitle() == "Revisar fila antes de crear":
            view = dialog.findChild(MapView)
            assert len(view.block_items) == 41
            view.fit()
        if dialog.windowTitle() == "Revisiones físicas":
            assert dialog.findChild(QTableWidget).rowCount() == 16
        QApplication.processEvents()
        dialog.grab().save(str(home() / (names[dialog.windowTitle()] + ".png")))
        dialog.close()
        return QDialog.DialogCode.Rejected

    try:
        Form.exec, QDialog.exec = row_form, capture
        window.create_block_row((820, 430), (690, 890))
        assert not window.store.queue(session["actor"]["id"])
        window.inspections_dialog()
        employee = window.data["employees"][0]
        id = window.store.enqueue(
            session["actor"]["id"],
            "assignment.assign",
            {"employee_id": employee["id"], "locker_id": locker["id"], "reason": "Entrega solicitada"},
            {},
        )
        window.store.result(id, "conflicto", "Otro equipo cambió el casillero. Revisa la información actual.")
        window.refresh_queue()
        window.queue_table.selectRow(0)
        window.resolve_conflict()
    finally:
        Form.exec, QDialog.exec = old_form, old_dialog
    capture_archived_selection(window)


def capture_archived_selection(window):
    original = window.data
    window.data = copy.deepcopy(original)
    stamp = now()
    for index in range(2):
        block = dict(
            original["blocks"][0],
            id=f"preview-deleted-{index}",
            label=f"E0{index + 1}",
            rows=4,
            columns=3,
            deleted_at=stamp,
        )
        window.data["archived_blocks"].append(block)
        for cell in range(12):
            window.data["archived_lockers"].append(
                dict(
                    original["lockers"][0],
                    id=f"preview-locker-{index}-{cell}",
                    block_id=block["id"],
                    number=str(61 + index * 12 + cell),
                    row=cell // 3,
                    column=cell % 3,
                    deleted_at=stamp,
                )
            )
    window.refresh()
    old_form, old_dialog = Form.exec, QDialog.exec

    def form_preview(form):
        form.show()
        QApplication.processEvents()
        form.grab().save(str(home() / "eliminacion-definitiva.png"))
        form.close()
        return QDialog.DialogCode.Rejected

    def archive_preview(dialog):
        table = dialog.findChild(QTableWidget)
        for row in range(table.rowCount()):
            if table.item(row, 0).text() == "Bloque":
                table.item(row, 0).setCheckState(Qt.CheckState.Checked)
        dialog.show()
        QApplication.processEvents()
        dialog.grab().save(str(home() / "seleccion-multiple.png"))
        next(b for b in dialog.findChildren(QPushButton) if "definitivamente" in b.text()).click()
        dialog.close()
        return QDialog.DialogCode.Rejected

    try:
        Form.exec, QDialog.exec = form_preview, archive_preview
        window.archived_inventory()
    finally:
        Form.exec, QDialog.exec = old_form, old_dialog
        window.data = original
        window.refresh()
