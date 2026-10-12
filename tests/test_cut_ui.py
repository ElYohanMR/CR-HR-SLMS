import base64
import json

import httpx
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QDateTimeEdit

from slms.cut_ui import CutDialog, photo_pixmap
from slms.forms import Form
from slms.local import LocalStore
from slms.sync import SyncWorker
from slms.window import Window
from test_cuts import create, assigned, photo, latest
from conftest import cmd, version


def test_offline_evidence_replays_original_id_once(system, tmp_path, monkeypatch):
    _, backend, session = system
    item = assigned(backend)
    store = LocalStore(tmp_path / "queue.sqlite3")
    payload = {"id": item["id"], "kind": "identidad", "filename": "prueba.png",
               "photo": base64.b64encode(photo()).decode()}
    id = store.enqueue(session["actor"]["id"], "cut.evidence", payload, version("cut_request", item))
    task = store.queue(session["actor"]["id"])[0]
    assert "photo" not in task["command"]["payload"]
    assert store.command_for_send(task)["payload"] == payload
    # Server commits but workstation loses the response: replay must not add another image.
    assert backend.post("/commands", json=store.command_for_send(task)).json()["status"] == "confirmada"
    original = httpx.Client
    def transport(request):
        response = (backend.post("/commands", json=json.loads(request.content))
                    if request.url.path == "/commands" else backend.get(request.url.path))
        return httpx.Response(response.status_code, json=response.json())
    monkeypatch.setattr("slms.sync.httpx.Client",
                        lambda **kw: original(transport=httpx.MockTransport(transport), **kw))
    SyncWorker(store, "http://test", session).run()
    assert store.queue(session["actor"]["id"])[0]["id"] == id
    assert store.queue(session["actor"]["id"])[0]["status"] == "confirmada"
    assert len(backend.get("/snapshot").json()["cut_evidence"]) == 1


def test_form_table_and_workflow_controls(qtbot, system, tmp_path, monkeypatch):
    assert not photo_pixmap(photo()).isNull()
    _, client, session = system
    item, _ = create(client)
    monkeypatch.setattr(Window, "sync", lambda self: None)
    store = LocalStore(tmp_path / "ui.sqlite3")
    store.put("snapshot", client.get("/snapshot").json())
    w = Window({"url": "http://test"}, session, store)
    qtbot.addWidget(w)
    w.nav.setCurrentRow(7)
    w.show()
    assert w.cut_table.rowCount() == 1
    w.cut_table.sortItems(3, Qt.SortOrder.DescendingOrder)
    w.cut_table.selectRow(0)
    assert w.selected(w.cut_table) == item["id"]
    dialog = CutDialog(w, item["id"])
    qtbot.addWidget(dialog)
    dialog.show()
    assert dialog.actions["edit"].isEnabled()
    assert dialog.actions["assign"].isEnabled()
    assert not dialog.actions["complete"].isEnabled()
    assert not dialog.photo_buttons["antes"].isEnabled()
    assert w.cut_submit(item, "cut.assign", {"assignee": "Encargado de prueba"})
    assert w.cut_notice.text().startswith("1 cambios")
    dialog.refresh()
    assert not dialog.actions["assign"].isEnabled()
    task = store.queue(session["actor"]["id"])[0]
    result = client.post("/commands", json=task["command"]).json()
    assert result["status"] == "confirmada"
    store.result(task["id"], result["status"], result["message"])
    w.data = client.get("/snapshot").json()
    w.refresh()
    dialog.refresh()
    assert not dialog.actions["edit"].isEnabled()
    assert dialog.actions["complete"].isEnabled()
    assert dialog.photo_buttons["antes"].isEnabled()
    w.session["actor"]["role"] = "viewer"
    dialog.refresh()
    assert not any(button.isEnabled() for button in dialog.actions.values())
    w.cut_filter.setCurrentIndex(w.cut_filter.findData("finalizada"))
    assert w.cut_table.rowCount() == 0
    dialog.close()
    w.close()


def test_creation_selects_assigned_locker_and_completion_date(qtbot, system, tmp_path, monkeypatch):
    _, client, session = system
    snapshot = client.get("/snapshot").json()
    e, locker = snapshot["employees"][0], snapshot["lockers"][0]
    assert client.post("/commands", json=cmd("assignment.assign",
        {"employee_id": e["id"], "locker_id": locker["id"], "reason": "Prueba"},
        version("employee", e) | version("locker", locker))).json()["status"] == "confirmada"
    item = assigned(client)
    monkeypatch.setattr(Window, "sync", lambda self: None)
    store = LocalStore(tmp_path / "form.sqlite3")
    store.put("snapshot", client.get("/snapshot").json())
    w = Window({"url": "http://test"}, session, store)
    qtbot.addWidget(w)
    form = w.cut_form()
    qtbot.addWidget(form)
    form.widgets["employee_id"].setCurrentIndex(1)
    assert form.widgets["locker_id"].currentData() == locker["id"]
    from test_cuts import attach
    for kind, color in (("identidad", "red"), ("antes", "green"), ("despues", "blue")):
        assert attach(client, item, kind, color)["status"] == "confirmada"
        item = latest(client, item["id"])
    w.data = client.get("/snapshot").json()
    w.refresh()
    def accept(form):
        assert form.findChild(QDateTimeEdit)
        form.widgets["result"].setPlainText("Prueba de cierre desde el formulario")
        form.widgets["identity_verified"].setChecked(True)
        return QDialog.DialogCode.Accepted
    monkeypatch.setattr(Form, "exec", accept)
    w.complete_cut(item)
    task = store.queue(session["actor"]["id"])[0]
    response = client.post("/commands", json=task["command"]).json()
    assert response["status"] == "confirmada", response
    assert latest(client, item["id"])["status"] == "finalizada"
    w.close()
