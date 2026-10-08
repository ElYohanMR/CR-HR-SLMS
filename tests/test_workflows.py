import copy
from concurrent.futures import ThreadPoolExecutor

import pytest
from PySide6.QtCore import Qt, QPointF
from PySide6.QtWidgets import QDialog, QTableWidget, QPushButton

from conftest import cmd, version
from slms.block_rows import plan_row
from slms.forms import Form
from slms.local import LocalStore
from slms.window import Window
from slms.service import execute


def row_values(data, count=40):
    return dict(
        count=count,
        rows=4,
        columns=3,
        prefix="E",
        first_label="01",
        first_number="001000",
        building_id=data["buildings"][0]["id"],
        location="EXT",
        side="E",
        rotation=0,
    )


def test_forty_blocks_atomic_and_right_to_left(system):
    _, client, _ = system
    data = client.get("/snapshot").json()
    operations = plan_row(data, "campus", (700, 200), (700, 900), row_values(data))
    assert len(operations) == 40
    assert operations[0]["payload"]["numbers"][0] == "001000"
    assert operations[-1]["payload"]["label"] == "E40"
    assert operations[-1]["payload"]["y"] == 900
    command = cmd("inventory.import", {"operations": operations})
    assert client.post("/commands", json=command).json()["status"] == "confirmada"
    assert client.post("/commands", json=command).json()["status"] == "confirmada"
    after = client.get("/snapshot").json()
    assert len(after["blocks"]) == len(data["blocks"]) + 40
    assert len(after["lockers"]) == len(data["lockers"]) + 480
    lockers = sorted([x for x in after["lockers"] if x["number"].startswith("001")], key=lambda x: x["number"])
    assert [(x["row"], x["column"]) for x in lockers[:4]] == [(0, 0), (0, 1), (0, 2), (1, 0)]
    # A race between preview and save must roll back every block, not keep the first.
    operations = plan_row(
        after, "campus", (500, 200), (500, 900), dict(row_values(data, 2), prefix="W", first_number="500000")
    )
    operations[-1]["payload"]["numbers"][-1] = "001000"
    assert (
        client.post("/commands", json=cmd("inventory.import", {"operations": operations})).json()["status"]
        == "conflicto"
    )
    assert len(client.get("/snapshot").json()["blocks"]) == len(after["blocks"])


def test_row_validation_reserves_archived_names_and_numbers(system):
    _, client, _ = system
    data = client.get("/snapshot").json()
    values = row_values(data)
    data["archived_lockers"] = [{"number": "001000"}]
    with pytest.raises(ValueError, match="coincide"):
        plan_row(data, "campus", (0, 0), (100, 100), values)
    data["archived_lockers"] = []
    data["archived_blocks"] = [dict(building_id=values["building_id"], location="EXT", label="e01")]
    with pytest.raises(ValueError, match="Elementos eliminados / restaurar"):
        plan_row(data, "campus", (0, 0), (100, 100), values)
    with pytest.raises(ValueError, match="diferentes"):
        plan_row(data, "campus", (100, 100), (100, 100), values)


def test_restored_blocks_rejoin_row_without_losing_identity_or_history(system):
    from test_inventory_removal import removal

    _, client, _ = system
    initial = client.get("/snapshot").json()
    values = row_values(initial, 5)
    operations = plan_row(initial, "campus", (500, 100), (500, 500), values)
    assert (
        client.post("/commands", json=cmd("inventory.import", {"operations": operations})).json()["status"]
        == "confirmada"
    )
    created = client.get("/snapshot").json()
    # A pre-existing side label is not rewritten just by arranging a row.
    from sqlalchemy.orm import Session
    from slms.models import Block

    with Session(system[0]) as db:
        block = next(b for b in created["blocks"] if b["label"] == "E03")
        db.get(Block, block["id"]).side = "N"
        db.commit()
    created = client.get("/snapshot").json()
    blocks = [b for b in created["blocks"] if b["label"].startswith("E")]
    for block in blocks:
        assert client.post("/commands", json=removal(created, "block", block)).json()["status"] == "confirmada"
    archived = client.get("/snapshot").json()
    with pytest.raises(ValueError, match="No necesitas borrar el historial"):
        plan_row(archived, "campus", (700, 200), (700, 900), dict(values, count=8))
    for block in archived["archived_blocks"]:
        assert client.post("/commands", json=removal(archived, "block", block, True)).json()["status"] == "confirmada"
    restored = client.get("/snapshot").json()
    operations = plan_row(restored, "campus", (700, 200), (700, 900), dict(values, count=8))
    assert [op["action"] for op in operations] == ["block.update"] * 5 + ["block.create"] * 3
    versions = {key: value for op in operations for key, value in op["versions"].items()}
    command = cmd("inventory.import", {"operations": operations}, versions)
    assert client.post("/commands", json=command).json()["status"] == "confirmada"
    result = client.get("/snapshot").json()
    assert {b["id"] for b in blocks} <= {b["id"] for b in result["blocks"]}
    assert {x["id"] for x in created["lockers"]} <= {x["id"] for x in result["lockers"]}
    assert {x["id"] for x in restored["audit"]} <= {x["id"] for x in result["audit"]}
    assert len(result["lockers"]) == len(created["lockers"]) + 36
    assert next(b for b in result["blocks"] if b["label"] == "E03")["side"] == "N"
    # Reapplying an obsolete row cannot move its existing blocks or create a partial row.
    command["id"] = cmd("", {})["id"]
    assert client.post("/commands", json=command).json()["status"] == "conflicto"
    assert len(client.get("/snapshot").json()["lockers"]) == len(result["lockers"])
    with pytest.raises(ValueError, match="numeración"):
        plan_row(result, "campus", (700, 200), (700, 900), dict(values, first_number="800000"))
    with pytest.raises(ValueError, match="dimensiones"):
        plan_row(result, "campus", (700, 200), (700, 900), dict(values, rows=3))


def test_row_preview_submits_versions_for_existing_blocks(window, monkeypatch):
    block = window.data["blocks"][0]
    # Demo is 4x4 and its numbers use a prefix; supply a synthetic numeric sequence
    # in this isolated UI fixture to exercise the actual preview/save path.
    block.update(label="N01", side="N")
    lockers = sorted(window.data["lockers"], key=lambda x: (x["row"], x["column"]))
    for i, locker in enumerate(lockers):
        locker["number"] = str(1000 + i)

    def form_exec(form):
        form.widgets["count"].setValue(2)
        form.widgets["columns"].setValue(4)
        form.widgets["first_number"].setText("1000")
        form.widgets["building_id"].setCurrentIndex(form.widgets["building_id"].findData(block["building_id"]))
        return QDialog.DialogCode.Accepted

    monkeypatch.setattr(Form, "exec", form_exec)
    monkeypatch.setattr(QDialog, "exec", lambda dialog: QDialog.DialogCode.Accepted)
    window.create_block_row((100, 100), (500, 500))
    command = window.store.queue(window.session["actor"]["id"])[0]["command"]
    assert command["versions"] == version("block", block)
    assert [op["action"] for op in command["payload"]["operations"]] == ["block.update", "block.create"]


def start_round(client, lockers):
    result = client.post(
        "/commands",
        json=cmd("inspection.create", {"title": "Recorrido de prueba", "locker_ids": [x["id"] for x in lockers]}),
    ).json()
    assert result["status"] == "confirmada"
    return result["target_id"]


def observe(client, round_id, locker, outcome, **extra):
    return cmd(
        "inspection.record",
        dict(round_id=round_id, locker_id=locker["id"], outcome=outcome, notes="Observación de prueba", **extra),
        version("locker", locker),
    )


def test_inspection_resume_idempotence_conflict_and_close(system):
    _, client, session = system
    data = client.get("/snapshot").json()
    assert data["features"]["inspections"]
    lockers = data["lockers"][:2]
    round_id = start_round(client, lockers)
    round = client.get("/snapshot").json()["inspection_rounds"][0]

    def close():
        return cmd("inspection.complete", {"round_id": round_id}, version("inspection_round", round))

    assert client.post("/commands", json=close()).json()["status"] == "conflicto"
    first = observe(client, round_id, lockers[0], "vacio")
    assert client.post("/commands", json=first).json()["status"] == "confirmada"
    assert client.post("/commands", json=first).json()["status"] == "confirmada"
    stale = observe(client, round_id, lockers[0], "dano")
    assert client.post("/commands", json=stale).json()["status"] == "conflicto"
    # Independent lockers do not conflict with a stale round version.
    assert client.post("/commands", json=observe(client, round_id, lockers[1], "dano")).json()["status"] == "confirmada"
    resumed = client.get("/snapshot").json()
    assert len(resumed["inspection_entries"]) == 2
    assert all(e["actor_id"] == session["actor"]["id"] for e in resumed["inspection_entries"])
    assert resumed["inspection_entries"][0]["observed_at"]
    assert client.post("/commands", json=close()).json()["status"] == "confirmada"
    latest = next(x for x in resumed["lockers"] if x["id"] == lockers[0]["id"])
    assert client.post("/commands", json=observe(client, round_id, latest, "vacio")).json()["status"] == "conflicto"


def test_inspection_never_releases_assignment_and_requires_current_entry(system):
    _, client, _ = system
    data = client.get("/snapshot").json()
    employee, locker = data["employees"][0], data["lockers"][0]
    assert (
        client.post(
            "/commands",
            json=cmd(
                "assignment.assign",
                {"employee_id": employee["id"], "locker_id": locker["id"], "reason": "Entrega"},
                version("employee", employee) | version("locker", locker),
            ),
        ).json()["status"]
        == "confirmada"
    )
    locker = next(x for x in client.get("/snapshot").json()["lockers"] if x["id"] == locker["id"])
    round_id = start_round(client, [locker])
    assert client.post("/commands", json=observe(client, round_id, locker, "vacio")).json()["status"] == "conflicto"
    assert (
        client.post("/commands", json=observe(client, round_id, locker, "diferencia")).json()["status"] == "confirmada"
    )
    after = client.get("/snapshot").json()
    assert after["assignments"][0]["ended_at"] is None
    latest = next(x for x in after["lockers"] if x["id"] == locker["id"])
    assert latest["condition"] == "pendiente"
    entry = after["inspection_entries"][0]
    change = observe(client, round_id, latest, "coincide", entry_id=entry["id"])
    assert client.post("/commands", json=change).json()["status"] == "conflicto"
    change["id"] = cmd("", {})["id"]
    change["versions"].update(version("inspection_entry", entry))
    assert client.post("/commands", json=change).json()["status"] == "confirmada"


def test_inspection_concurrent_observations_and_permissions(system):
    _, client, session = system
    engine = system[0]
    locker = client.get("/snapshot").json()["lockers"][0]
    round_id = start_round(client, [locker])
    requests = [observe(client, round_id, locker, result) for result in ("vacio", "dano")]
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda c: execute(engine, session["actor"]["id"], c), requests))
    assert sorted(r["status"] for r in results) == ["confirmada", "conflicto"]
    data = client.get("/snapshot").json()
    assert len(data["inspection_entries"]) == 1
    for role, expected in (("viewer", "rechazada"), ("operator", "confirmada")):
        result = client.post(
            "/commands",
            json=cmd(
                "admin.create",
                {"username": role, "name": role, "password": "Fictional-password-2026", "role": role, "active": True},
            ),
        ).json()
        assert result["status"] == "confirmada"
        from sqlalchemy.orm import sessionmaker
        from sqlalchemy import select
        from slms.models import Admin

        with sessionmaker(engine)() as db:
            actor = db.scalar(select(Admin).where(Admin.username == role))
            result = execute(
                engine, actor.id, cmd("inspection.create", {"title": "Permisos", "locker_ids": [locker["id"]]})
            )
            assert result["status"] == expected


def test_upgrade_from_previous_schema_keeps_inventory(system):
    from alembic import command
    from alembic.config import Config
    from sqlalchemy import text
    from slms.config import asset
    from slms.database import migrate

    engine, _, _ = system
    cfg = Config()
    cfg.set_main_option("script_location", str(asset("../migrations").resolve()))
    with engine.begin() as conn:
        count = conn.execute(text("SELECT count(*) FROM lockers")).scalar()
        cfg.attributes["connection"] = conn
        command.downgrade(cfg, "0003")
    migrate(engine)
    migrate(engine)
    with engine.connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM lockers")).scalar() == count
        assert conn.execute(text("SELECT count(*) FROM inspection_rounds")).scalar() == 0


@pytest.fixture
def window(qtbot, system, tmp_path, monkeypatch):
    _, client, session = system
    monkeypatch.setattr(Window, "sync", lambda self: None)
    store = LocalStore(tmp_path / "workflows.sqlite3")
    store.put("snapshot", client.get("/snapshot").json())
    win = Window({"url": "http://127.0.0.1:8765", "mode": "demo"}, session, store)
    qtbot.addWidget(win)
    win.show()
    return win


def test_row_points_survive_zoom_and_cancel_leaves_inventory(window, qtbot):
    window.start_block_row()
    picked = []
    window.map.rowPicked.disconnect()
    window.map.rowPicked.connect(lambda a, b: picked.append((a, b)))
    start = QPointF(400, 400)
    pos = window.map.mapFromScene(start)
    qtbot.mouseClick(window.map.viewport(), Qt.MouseButton.LeftButton, pos=pos)
    first = list(window.map.row_start)
    window.map.scale(1.3, 1.3)
    pos = window.map.mapFromScene(QPointF(550, 500))
    qtbot.mouseClick(window.map.viewport(), Qt.MouseButton.LeftButton, pos=pos)
    assert picked[0][0] == first
    assert picked[0][1][0] == pytest.approx(550, abs=3)
    window.cancel_block_row()
    assert not window.map.editing
    assert not window.store.queue(window.session["actor"]["id"])


def test_row_preview_cancel_does_not_enqueue(window, monkeypatch):
    calls = []

    def form_exec(form):
        calls.append(form.windowTitle())
        form.widgets["first_number"].setText("50000")
        return QDialog.DialogCode.Accepted if len(calls) == 1 else QDialog.DialogCode.Rejected

    monkeypatch.setattr(Form, "exec", form_exec)
    monkeypatch.setattr(QDialog, "exec", lambda dialog: QDialog.DialogCode.Rejected)
    window.create_block_row((100, 100), (500, 500))
    assert len(calls) == 2
    assert not window.store.queue(window.session["actor"]["id"])


def test_conflict_correction_new_request_preserves_original(window, monkeypatch):
    employee, locker = window.data["employees"][0], window.data["lockers"][0]
    original = window.store.enqueue(
        window.session["actor"]["id"],
        "assignment.assign",
        {"employee_id": employee["id"], "locker_id": locker["id"]},
        {},
    )
    window.store.result(original, "conflicto", "Otro equipo cambió el casillero.")
    window.refresh_queue()
    window.queue_table.selectRow(0)
    before = copy.deepcopy(window.store.queue(window.session["actor"]["id"])[0])

    def form_exec(form):
        form.widgets["reason"].setPlainText("Resolver la asignación")
        return QDialog.DialogCode.Accepted

    monkeypatch.setattr(Form, "exec", form_exec)

    def dialog_exec(dialog):
        button = next(b for b in dialog.findChildren(QPushButton) if b.text() == "Preparar corrección")
        button.click()
        assert not button.isEnabled()
        return QDialog.DialogCode.Accepted

    monkeypatch.setattr(QDialog, "exec", dialog_exec)
    window.resolve_conflict()
    queue = window.store.queue(window.session["actor"]["id"])
    assert len(queue) == 2
    assert queue[0] == before
    assert queue[1]["id"] != original
    assert queue[1]["command"]["payload"]["resolves_command_id"] == original
    assert queue[1]["command"]["versions"]
    assert window.resolving_command is None


def test_inspection_dialog_resumes_and_queues_observation(window, system, monkeypatch):
    _, client, _ = system
    locker = window.data["lockers"][0]
    start_round(client, [locker])
    window.data = client.get("/snapshot").json()
    window.refresh()

    def form_exec(form):
        form.widgets["outcome"].setCurrentIndex(form.widgets["outcome"].findData("vacio"))
        return QDialog.DialogCode.Accepted

    monkeypatch.setattr(Form, "exec", form_exec)

    def dialog_exec(dialog):
        table = dialog.findChild(QTableWidget)
        assert table.rowCount() == 1
        table.selectRow(0)
        next(b for b in dialog.findChildren(QPushButton) if b.text() == "Registrar resultado").click()
        assert table.item(0, 2).text() == "Por sincronizar"
        return QDialog.DialogCode.Accepted

    monkeypatch.setattr(QDialog, "exec", dialog_exec)
    window.inspections_dialog()
    assert window.store.queue(window.session["actor"]["id"])[0]["command"]["action"] == "inspection.record"
