import copy
from concurrent.futures import ThreadPoolExecutor

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QTableWidget, QPushButton, QLabel
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from conftest import cmd, version
from test_inventory_removal import removal
from slms.models import Admin, Audit
from slms.service import execute
from slms.tableview import checked_ids, mark_rows
from slms.local import LocalStore
from slms.window import Window
from slms.forms import Form


def archive(client):
    data = client.get("/snapshot").json()
    block = data["blocks"][0]
    assert client.post("/commands", json=removal(data, "block", block)).json()["status"] == "confirmada"
    return client.get("/snapshot").json()


def batch(data, purge=False):
    block = data["archived_blocks"][0]
    items = [{"kind": "block", "id": block["id"]}]
    items += [{"kind": "locker", "id": entry["id"]} for entry in data["archived_lockers"]]
    versions = version("block", block)
    for locker in data["archived_lockers"]:
        versions.update(version("locker", locker))
    return cmd(
        "inventory.purge" if purge else "inventory.restore_many",
        {"items": items, "reason": "Inventario ficticio", "confirmation": "ELIMINAR"},
        versions,
    )


def test_restore_batch_deduplicates_and_is_atomic(system):
    _, client, _ = system
    data = archive(client)
    request = batch(data)
    bad = copy.deepcopy(request)
    bad["versions"]["locker:" + data["archived_lockers"][-1]["id"]] = 999
    assert client.post("/commands", json=bad).json()["status"] == "conflicto"
    assert not client.get("/snapshot").json()["lockers"]
    request["id"] = cmd("", {})["id"]
    result = client.post("/commands", json=request).json()
    assert result["status"] == "confirmada"
    assert client.post("/commands", json=request).json() == result
    after = client.get("/snapshot").json()
    assert len(after["lockers"]) == 16 and not after["archived_lockers"]
    assert len([a for a in after["audit"] if a["action"] == "locker.restore"]) == 16
    assert all(x["condition"] == "pendiente" for x in after["lockers"])


def test_restore_explicit_child_deleted_before_parent(system):
    _, client, _ = system
    data = client.get("/snapshot").json()
    assert client.post("/commands", json=removal(data, "locker", data["lockers"][0])).json()["status"] == "confirmada"
    data = archive(client)
    assert client.post("/commands", json=batch(data)).json()["status"] == "confirmada"
    assert len(client.get("/snapshot").json()["lockers"]) == 16


def test_only_initial_admin_can_purge_and_cannot_be_impersonated(system):
    engine, client, initial = system
    assert initial["actor"]["is_initial"]
    request = cmd(
        "admin.create",
        {
            "username": "secondary",
            "name": "Administrador inicial",
            "role": "admin",
            "password": "Fictional-password-2026",
            "is_initial": True,
        },
    )
    assert client.post("/commands", json=request).json()["status"] == "rechazada"
    request["payload"].pop("is_initial")
    request["id"] = cmd("", {})["id"]
    assert client.post("/commands", json=request).json()["status"] == "confirmada"
    data = archive(client)
    with Session(engine) as db:
        secondary = db.scalar(select(Admin).where(Admin.username == "secondary"))
        other_id = secondary.id
        assert not secondary.is_initial
    purge = batch(data, True)
    assert execute(engine, other_id, purge)["status"] == "rechazada"
    # Naming an account like the founder or possessing admin role grants no privilege.
    change = cmd("admin.update", dict(initial["actor"], password="Fictional-new-password"))
    change["payload"].pop("is_initial")
    assert execute(engine, other_id, change)["status"] == "rechazada"
    purge["id"] = cmd("", {})["id"]
    purge["payload"]["confirmation"] = "yes"
    assert client.post("/commands", json=purge).json()["status"] == "rechazada"
    assert len(client.get("/snapshot").json()["archived_lockers"]) == 16


def test_purge_frees_codes_keeps_audit_and_replay_does_not_delete_replacement(system):
    engine, client, session = system
    data = archive(client)
    request = batch(data, True)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: execute(engine, session["actor"]["id"], request), range(2)))
    assert results[0] == results[1] and results[0]["status"] == "confirmada"
    after = client.get("/snapshot").json()
    assert not after["archived_lockers"] and not after["archived_blocks"]
    assert len(after["employees"]) == 1
    with Session(engine) as db:
        assert len(list(db.scalars(select(Audit).where(Audit.action == "locker.purge")))) == 16
    block = data["archived_blocks"][0]
    payload = {
        k: block[k] for k in ("plan_id", "building_id", "label", "rows", "columns", "side", "location", "x", "y")
    }
    payload["numbers"] = [
        entry["number"] for entry in sorted(data["archived_lockers"], key=lambda entry: (entry["row"], entry["column"]))
    ]
    assert client.post("/commands", json=cmd("block.create", payload)).json()["status"] == "confirmada"
    assert client.post("/commands", json=request).json() == results[0]
    current = client.get("/snapshot").json()
    assert len(current["lockers"]) == 16
    assert current["blocks"][0]["id"] != block["id"]


def test_purge_refuses_assignment_history_and_inspection_scope(system):
    _, client, _ = system
    data = client.get("/snapshot").json()
    employee, locker = data["employees"][0], data["lockers"][0]
    assign = cmd(
        "assignment.assign",
        {"employee_id": employee["id"], "locker_id": locker["id"], "reason": "Prueba"},
        version("employee", employee) | version("locker", locker),
    )
    assert client.post("/commands", json=assign).json()["status"] == "confirmada"
    data = client.get("/snapshot").json()
    employee = data["employees"][0]
    locker = next(entry for entry in data["lockers"] if entry["id"] == locker["id"])
    release = cmd(
        "assignment.release",
        {"employee_id": employee["id"], "assignment_id": data["assignments"][0]["id"], "reason": "Prueba"},
        version("employee", employee) | version("locker", locker),
    )
    assert client.post("/commands", json=release).json()["status"] == "confirmada"
    data = archive(client)
    assert client.post("/commands", json=batch(data, True)).json()["status"] == "rechazada"
    assert client.get("/snapshot").json()["assignments"] == data["assignments"]
    # A different, never-assigned locker included in a pending inspection is protected too.
    assert client.post("/commands", json=batch(data)).json()["status"] == "confirmada"
    unused = next(entry for entry in data["archived_lockers"] if entry["id"] != locker["id"])
    assert (
        client.post(
            "/commands", json=cmd("inspection.create", {"title": "Recorrido", "locker_ids": [unused["id"]]})
        ).json()["status"]
        == "confirmada"
    )
    data = archive(client)
    current = next(entry for entry in data["archived_lockers"] if entry["id"] == unused["id"])
    purge = cmd(
        "inventory.purge",
        {"items": [{"kind": "locker", "id": unused["id"]}], "reason": "Prueba", "confirmation": "ELIMINAR"},
        version("locker", current),
    )
    assert client.post("/commands", json=purge).json()["status"] == "rechazada"
    assert len(client.get("/snapshot").json()["archived_lockers"]) == 16


def test_legacy_migration_identifies_initial_account_and_preserves_data(system):
    from alembic import command
    from alembic.config import Config
    from slms.config import asset
    from slms.database import migrate

    engine, client, session = system
    assert (
        client.post(
            "/commands",
            json=cmd(
                "admin.create",
                {"username": "other", "name": "Other", "role": "admin", "password": "Fictional-password-2026"},
            ),
        ).json()["status"]
        == "confirmada"
    )
    cfg = Config()
    cfg.set_main_option("script_location", str(asset("../migrations").resolve()))
    with engine.begin() as conn:
        cfg.attributes["connection"] = conn
        command.downgrade(cfg, "0004")
    migrate(engine)
    with engine.connect() as conn:
        assert conn.execute(text("SELECT id FROM administrators WHERE is_initial = true")).scalars().all() == [
            session["actor"]["id"]
        ]
        assert conn.execute(text("SELECT count(*) FROM lockers")).scalar() == 16


@pytest.fixture
def window(qtbot, system, tmp_path, monkeypatch):
    _, client, session = system
    monkeypatch.setattr(Window, "sync", lambda self: None)
    store = LocalStore(tmp_path / "batch.sqlite3")
    store.put("snapshot", archive(client))
    win = Window({"url": "http://127.0.0.1:8765", "mode": "demo"}, session, store)
    qtbot.addWidget(win)
    win.show()
    return win


def test_checkboxes_survive_sort_refresh_and_drop_filtered_records(window):
    table = window.employees
    rows = [("a", ["1", "A", "", "", "", "", ""]), ("b", ["2", "B", "", "", "", "", ""])]
    window.fill(table, rows)
    mark_rows(table, True)
    table.sortItems(0, Qt.SortOrder.DescendingOrder)
    window.fill(table, rows[::-1])
    assert set(checked_ids(table)) == {"a", "b"}
    window.fill(table, rows[:1])
    assert checked_ids(table) == ["a"]
    window.fill(table, rows)
    assert checked_ids(table) == ["a"]
    menu = window.table_menu(table, 0, 0)
    next(a for a in menu.actions() if a.text() == "Copiar filas marcadas").trigger()
    from PySide6.QtWidgets import QApplication

    assert QApplication.clipboard().text().startswith("1\tA")


def test_bulk_restore_preview_and_initial_only_visibility(window, monkeypatch):
    def form_exec(form):
        assert "16 casilleros diferentes" in next(
            entry.text() for entry in form.findChildren(QLabel) if "casilleros diferentes" in entry.text()
        )
        form.widgets["reason"].setPlainText("Restaurar pruebas")
        return QDialog.DialogCode.Accepted

    monkeypatch.setattr(Form, "exec", form_exec)

    def dialog_exec(dialog):
        table = dialog.findChild(QTableWidget)
        mark_rows(table, True)
        assert any(b.text() == "Eliminar definitivamente marcados" for b in dialog.findChildren(QPushButton))
        next(b for b in dialog.findChildren(QPushButton) if b.text() == "Restaurar marcados").click()
        return QDialog.DialogCode.Accepted

    monkeypatch.setattr(QDialog, "exec", dialog_exec)
    window.archived_inventory()
    queue = window.store.queue(window.session["actor"]["id"])
    assert len(queue) == 1 and queue[0]["command"]["action"] == "inventory.restore_many"
    assert len(queue[0]["command"]["payload"]["items"]) == 17
    actor = window.lookup("admins", window.session["actor"]["id"])
    actor["is_initial"] = False

    def ordinary_admin(dialog):
        assert not any("definitivamente" in b.text() for b in dialog.findChildren(QPushButton))
        return QDialog.DialogCode.Rejected

    monkeypatch.setattr(QDialog, "exec", ordinary_admin)
    window.archived_inventory()


def test_cancel_purge_does_not_enqueue(window, monkeypatch):
    monkeypatch.setattr(Form, "exec", lambda form: QDialog.DialogCode.Rejected)

    def dialog_exec(dialog):
        mark_rows(dialog.findChild(QTableWidget), True)
        next(b for b in dialog.findChildren(QPushButton) if "definitivamente" in b.text()).click()
        return QDialog.DialogCode.Rejected

    monkeypatch.setattr(QDialog, "exec", dialog_exec)
    window.archived_inventory()
    assert not window.store.queue(window.session["actor"]["id"])


def test_checkbox_mouse_click_and_purge_preview_submission(window, qtbot, monkeypatch):
    def accept_form(form):
        form.widgets["reason"].setPlainText("Retirar pruebas sin uso")
        form.widgets["confirmation"].setText("ELIMINAR")
        return QDialog.DialogCode.Accepted

    monkeypatch.setattr(Form, "exec", accept_form)

    def dialog_exec(dialog):
        dialog.show()
        qtbot.wait(20)
        table = dialog.findChild(QTableWidget)
        # The first row is the archived block; click the native checkbox.
        rectangle = table.visualItemRect(table.item(0, 0))
        from PySide6.QtCore import QPoint

        qtbot.mouseClick(
            table.viewport(), Qt.MouseButton.LeftButton, pos=QPoint(rectangle.left() + 9, rectangle.center().y())
        )
        assert len(checked_ids(table)) == 1
        next(b for b in dialog.findChildren(QPushButton) if "definitivamente" in b.text()).click()
        return QDialog.DialogCode.Accepted

    monkeypatch.setattr(QDialog, "exec", dialog_exec)
    window.archived_inventory()
    queue = window.store.queue(window.session["actor"]["id"])
    assert len(queue) == 1 and queue[0]["command"]["action"] == "inventory.purge"
    assert queue[0]["command"]["payload"]["confirmation"] == "ELIMINAR"
    assert len(queue[0]["command"]["payload"]["items"]) == 1
    assert len(queue[0]["command"]["versions"]) == 17


def test_purge_stale_child_rolls_back_everything(system):
    _, client, _ = system
    data = archive(client)
    request = batch(data, True)
    request["versions"]["locker:" + data["archived_lockers"][-1]["id"]] = 999
    assert client.post("/commands", json=request).json()["status"] == "conflicto"
    after = client.get("/snapshot").json()
    assert after["archived_blocks"] == data["archived_blocks"]
    assert after["archived_lockers"] == data["archived_lockers"]
    assert not any(event["action"].endswith(".purge") for event in after["audit"])
