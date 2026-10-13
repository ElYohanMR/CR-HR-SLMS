from sqlalchemy import select
from sqlalchemy.orm import Session
from PySide6.QtWidgets import QDialog, QToolButton, QLabel

from conftest import cmd, version
from slms.models import Audit, Admin
from slms.forms import Form
from slms.local import LocalStore
from slms.window import Window


def test_padlock_edits_audited_versioned_and_assignment_preserved(system):
    engine, client, session = system
    snapshot = client.get("/snapshot").json()
    locker, employee = snapshot["lockers"][0], snapshot["employees"][0]
    assert locker["has_padlock"] is False
    assert client.post("/commands", json=cmd("assignment.assign",
        {"employee_id": employee["id"], "locker_id": locker["id"], "reason": "Prueba"},
        version("employee", employee) | version("locker", locker))).json()["status"] == "confirmada"
    snapshot = client.get("/snapshot").json()
    locker = next(e for e in snapshot["lockers"] if e["id"] == locker["id"])

    def edit(current, **fields):
        return client.post("/commands", json=cmd("locker.update",
            {"id": current["id"], "number": current["number"], "condition": current["condition"],
             "notes": current["notes"], **fields}, version("locker", current))).json()

    assert edit(locker, has_padlock=True)["status"] == "confirmada"
    assert edit(locker, has_padlock=False)["status"] == "conflicto"
    def fresh():
        return next(e for e in client.get("/snapshot").json()["lockers"] if e["id"] == locker["id"])
    assert fresh()["has_padlock"] is True
    for invalid in ("Sí", 1, None):
        assert edit(fresh(), has_padlock=invalid)["status"] == "rechazada"
    assert edit(fresh(), notes="Cliente anterior sin campo nuevo")["status"] == "confirmada"
    assert fresh()["has_padlock"] is True
    assert edit(fresh(), has_padlock=False)["status"] == "confirmada"
    assert fresh()["has_padlock"] is False
    assert client.get("/snapshot").json()["assignments"] == snapshot["assignments"]
    with Session(engine) as db:
        entries = list(db.scalars(select(Audit).where(Audit.action == "locker.update")))
        assert any(e.before["has_padlock"] is False and e.after["has_padlock"] is True for e in entries)
        db.get(Admin, session["actor"]["id"]).role = "viewer"
        db.commit()
    assert edit(fresh(), has_padlock=True)["status"] == "rechazada"


def test_help_navigation_and_padlock_form(qtbot, system, tmp_path, monkeypatch):
    _, client, session = system
    monkeypatch.setattr(Window, "sync", lambda self: None)
    store = LocalStore(tmp_path / "ui.sqlite3")
    snapshot = client.get("/snapshot").json()
    store.put("snapshot", snapshot)
    w = Window({"url": "http://test"}, session, store)
    qtbot.addWidget(w)
    w.show()
    assert w.nav.item(6).text() == "Cortes de candado"
    assert w.nav.item(7).text() == "Administración"
    helpers = w.findChildren(QToolButton, "pageHelp")
    assert len(helpers) == 8 and all(e.toolTip() and not e.icon().isNull() for e in helpers)
    assert "opcionales" in next(e.toolTip() for e in helpers if "corte" in e.accessibleName())
    assert not w.cut_notice.isVisible()
    assert w.inventory.horizontalHeaderItem(5).text() == "Tiene candado"
    footer = w.findChild(QLabel, "administrationFooter")
    assert "Gestión de acceso" in footer.text() and "http" not in footer.text()

    def accept(form):
        combo = form.widgets["has_padlock"]
        assert combo.isEnabled() and combo.currentData() is False
        combo.setCurrentIndex(combo.findData(True))
        return QDialog.DialogCode.Accepted
    monkeypatch.setattr(Form, "exec", accept)
    w.locker_dialog(snapshot["lockers"][0]["id"])
    task = store.queue(session["actor"]["id"])[0]
    assert task["command"]["payload"]["has_padlock"] is True
    result = client.post("/commands", json=task["command"]).json()
    assert result["status"] == "confirmada"
    w.close()
