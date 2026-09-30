from sqlalchemy.orm import sessionmaker
from slms.models import Block, Locker
from slms.window import Window
from slms.local import LocalStore
from conftest import cmd, version


def test_2000_lockers_render_and_filter(qtbot, system, tmp_path, monkeypatch):
    engine, client, session = system
    with sessionmaker(engine).begin() as db:
        for n in range(124):
            block = Block(
                plan_id="campus",
                building_id="building-1",
                label=f"TEST-{n}",
                rows=4,
                columns=4,
                side="N",
                location="EXT",
                x=(n % 20) * 45,
                y=(n // 20) * 45,
            )
            db.add(block)
            db.flush()
            db.add_all([Locker(block_id=block.id, number=f"TEST-{n}-{i}", row=i // 4, column=i % 4) for i in range(16)])
    snapshot = client.get("/snapshot").json()
    assert len(snapshot["lockers"]) == 2000
    monkeypatch.setattr(Window, "sync", lambda self: None)
    store = LocalStore(tmp_path / "scale.sqlite3")
    store.put("snapshot", snapshot)
    window = Window({"url": "http://localhost", "mode": "demo"}, session, store)
    qtbot.addWidget(window)
    assert window.inventory.rowCount() == 2000
    window.inventory_filter.setCurrentIndex(1)
    assert window.inventory.rowCount() == 16
    window.close()


def test_verify_block_is_atomic(system):
    _, client, _ = system
    response = client.post(
        "/commands",
        json=cmd(
            "block.create",
            {
                "plan_id": "campus",
                "building_id": "building-1",
                "label": "NEW",
                "side": "S",
                "location": "EXT",
                "rows": 3,
                "columns": 4,
                "numbers": [str(i) for i in range(12)],
            },
        ),
    ).json()
    data = client.get("/snapshot").json()
    block = next(b for b in data["blocks"] if b["id"] == response["target_id"])
    lockers = [locker for locker in data["lockers"] if locker["block_id"] == block["id"]]
    versions = version("block", block)
    for locker in lockers:
        versions.update(version("locker", locker))
    versions["locker:" + lockers[-1]["id"]] = 999
    request = cmd("lockers.verify", {"block_id": block["id"], "reason": "Verificado físicamente"}, versions)
    assert client.post("/commands", json=request).json()["status"] == "conflicto"
    assert all(
        locker["condition"] == "pendiente"
        for locker in client.get("/snapshot").json()["lockers"]
        if locker["block_id"] == block["id"]
    )
    request["id"] = cmd("", {})["id"]
    request["versions"].update(version("locker", lockers[-1]))
    assert client.post("/commands", json=request).json()["status"] == "confirmada"
    assert all(
        locker["condition"] == "utilizable"
        for locker in client.get("/snapshot").json()["lockers"]
        if locker["block_id"] == block["id"]
    )
