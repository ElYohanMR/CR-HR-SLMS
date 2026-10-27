
import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from conftest import cmd, version
from slms.models import Locker, Audit, now
from test_cuts import create, latest, post


def locker_now(client, id):
    return next(x for x in client.get("/snapshot").json()["lockers"] if x["id"] == id)


def close(client, item, cancel=False):
    if cancel:
        return post(client, "cut.cancel", {"id": item["id"], "reason": "Se encontraron las llaves"}, item)
    assert post(client, "cut.assign", {"id": item["id"], "assignee": "Seguridad"}, item)["status"] == "confirmada"
    item = latest(client, item["id"])
    return post(client, "cut.complete", {"id": item["id"], "performed_at": now(),
                "identity_verified": True, "result": "Corte realizado"}, item)


@pytest.mark.parametrize("condition", ["utilizable", "pendiente", "mantenimiento", "retirado"])
@pytest.mark.parametrize("cancel", [False, True])
def test_open_cut_holds_condition_until_closed(system, condition, cancel):
    engine, client, _ = system
    selected = client.get("/snapshot").json()["lockers"][0]
    with Session(engine) as db:
        db.get(Locker, selected["id"]).condition = condition
        db.commit()
    item, request = create(client, locker_id=selected["id"])
    held = locker_now(client, item["locker_id"])
    assert held["condition"] == "mantenimiento" and held["condition_after_cut"] == condition
    assert held["version"] == selected["version"] + 1
    assert client.post("/commands", json=request).json()["status"] == "confirmada"
    assert locker_now(client, item["locker_id"]) == held
    assert close(client, item, cancel)["status"] == "confirmada"
    restored = locker_now(client, item["locker_id"])
    assert restored["condition"] == condition and restored["condition_after_cut"] is None
    with Session(engine) as db:
        events = list(db.scalars(select(Audit).where(Audit.action == "locker.cut_maintenance")))
        assert len(events) == 2
        assert events[0].target_id == selected["id"]


def test_cannot_assign_held_locker_or_overwrite_with_stale_edit(system):
    _, client, _ = system
    snapshot = client.get("/snapshot").json()
    old = snapshot["lockers"][0]
    employee = snapshot["employees"][0]
    item, _ = create(client, locker_id=old["id"], employee_id=employee["id"])
    held = locker_now(client, item["locker_id"])
    assignment = cmd("assignment.assign", {"employee_id": employee["id"], "locker_id": held["id"],
                                           "reason": "Prueba"}, version("employee", employee) | version("locker", held))
    assert client.post("/commands", json=assignment).json()["status"] == "rechazada"
    update = cmd("locker.update", {"id": held["id"], "number": held["number"], "condition": "utilizable"},
                 version("locker", old))
    assert client.post("/commands", json=update).json()["status"] == "conflicto"
    update = cmd("locker.update", update["payload"], version("locker", held))
    assert client.post("/commands", json=update).json()["status"] == "confirmada"
    assert locker_now(client, held["id"])["condition"] == "mantenimiento"


@pytest.mark.parametrize("departure", [False, True])
def test_release_or_departure_keeps_hold_then_requires_verification(system, departure):
    _, client, _ = system
    snapshot = client.get("/snapshot").json()
    employee, locker = snapshot["employees"][0], snapshot["lockers"][0]
    result = client.post("/commands", json=cmd("assignment.assign", {
        "employee_id": employee["id"], "locker_id": locker["id"], "reason": "Asignación de prueba"},
        version("employee", employee) | version("locker", locker))).json()
    assert result["status"] == "confirmada"
    item, _ = create(client, locker_id=locker["id"], employee_id=employee["id"])
    snapshot = client.get("/snapshot").json()
    assignment = next(a for a in snapshot["assignments"] if a["locker_id"] == locker["id"] and a["ended_at"] is None)
    employee = next(e for e in snapshot["employees"] if e["id"] == employee["id"])
    held = locker_now(client, locker["id"])
    payload = {"employee_id": employee["id"], "assignment_id": assignment["id"],
               "reason": "Devolución durante corte", "locker_verified": False}
    if departure:
        payload["departure_type"] = "renuncia"
    result = client.post("/commands", json=cmd("employee.deactivate" if departure else "assignment.release", payload,
              version("employee", employee) | version("locker", held))).json()
    assert result["status"] == "confirmada", result
    held = locker_now(client, locker["id"])
    assert held["condition"] == "mantenimiento" and held["condition_after_cut"] == "pendiente"
    assert close(client, item)["status"] == "confirmada"
    assert locker_now(client, locker["id"])["condition"] == "pendiente"


def test_damage_recorded_during_cut_is_preserved(system):
    _, client, _ = system
    item, _ = create(client)
    held = locker_now(client, item["locker_id"])
    round_result = client.post("/commands", json=cmd("inspection.create", {
        "title": "Revisión", "locker_ids": [held["id"]]})).json()
    assert round_result["status"] == "confirmada", round_result
    result = client.post("/commands", json=cmd("inspection.record", {
        "round_id": round_result["target_id"], "locker_id": held["id"], "entry_id": None,
        "outcome": "dano", "notes": "Bisagra dañada"}, version("locker", held))).json()
    assert result["status"] == "confirmada", result
    assert close(client, item)["status"] == "confirmada"
    assert locker_now(client, held["id"])["condition"] == "mantenimiento"


def test_upgrade_applies_hold_to_existing_open_requests_once(system):
    from alembic import command
    from alembic.config import Config
    from slms.config import asset
    from slms.database import migrate
    engine, client, _ = system
    item, _ = create(client)
    cfg = Config()
    cfg.set_main_option("script_location", str(asset("../migrations").resolve()))
    with engine.begin() as connection:
        cfg.attributes["connection"] = connection
        command.downgrade(cfg, "0007")
    migrate(engine)
    first = locker_now(client, item["locker_id"])
    migrate(engine)
    assert locker_now(client, item["locker_id"]) == first
    assert first["condition"] == "mantenimiento" and first["condition_after_cut"] == "utilizable"
    assert close(client, item, cancel=True)["status"] == "confirmada"
    assert locker_now(client, item["locker_id"])["condition"] == "utilizable"


def test_inventory_displays_maintenance_even_when_assigned(system, qtbot, tmp_path, monkeypatch):
    from PySide6.QtWidgets import QDialog
    from slms.forms import Form
    from slms.window import Window
    from slms.local import LocalStore
    _, client, session = system
    snapshot = client.get("/snapshot").json()
    employee, locker = snapshot["employees"][0], snapshot["lockers"][0]
    result = client.post("/commands", json=cmd("assignment.assign", {
        "employee_id": employee["id"], "locker_id": locker["id"], "reason": "Prueba"},
        version("employee", employee) | version("locker", locker))).json()
    assert result["status"] == "confirmada"
    item, _ = create(client, locker_id=locker["id"], employee_id=employee["id"])
    monkeypatch.setattr(Window, "sync", lambda self: None)
    store = LocalStore(tmp_path / "hold-ui.sqlite3")
    store.put("snapshot", client.get("/snapshot").json())
    window = Window({"url": "http://test"}, session, store)
    qtbot.addWidget(window)
    assert window.locker_state(locker_now(client, item["locker_id"])) == "mantenimiento"
    assert window.assignment_for(locker_id=item["locker_id"]) is not None

    def edit_notes(form):
        assert form.widgets["condition"].currentData() == "utilizable"
        form.widgets["notes"].setPlainText("Nota durante el corte")
        return QDialog.DialogCode.Accepted

    monkeypatch.setattr(Form, "exec", edit_notes)
    window.locker_dialog(item["locker_id"])
    task = store.queue(session["actor"]["id"])[0]
    assert client.post("/commands", json=task["command"]).json()["status"] == "confirmada"
    assert locker_now(client, item["locker_id"])["condition_after_cut"] == "utilizable"
    assert close(client, item)["status"] == "confirmada"
    assert window.locker_state(locker_now(client, item["locker_id"])) == "ocupado"
    assert any(a["locker_id"] == item["locker_id"] and a["ended_at"] is None
               for a in client.get("/snapshot").json()["assignments"])
    window.close()


def test_concurrent_cut_and_assignment_do_not_bypass_maintenance(system):
    from concurrent.futures import ThreadPoolExecutor
    from slms.service import execute
    engine, client, session = system
    snapshot = client.get("/snapshot").json()
    employee, locker = snapshot["employees"][0], snapshot["lockers"][0]
    versions = version("employee", employee) | version("locker", locker)
    payload = {"employee_id": employee["id"], "locker_id": locker["id"], "reason": "Prueba simultánea"}
    requests = [cmd("cut.create", payload | {"supervisor": "Supervisor", "channel": "teams"}, versions),
                cmd("assignment.assign", payload, versions)]
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda command: execute(engine, session["actor"]["id"], command), requests))
    assert sorted(r["status"] for r in results) == ["confirmada", "conflicto"]
    if results[0]["status"] == "confirmada":
        assert locker_now(client, locker["id"])["condition"] == "mantenimiento"
        assert not any(a["locker_id"] == locker["id"] and a["ended_at"] is None
                       for a in client.get("/snapshot").json()["assignments"])
