from conftest import cmd, version
from slms.inventory_io import export_rows, prepare_import


def removal(data, kind, item, restore=False):
    versions = version(kind, item)
    if kind == "block":
        for locker in data["archived_lockers" if restore else "lockers"]:
            if locker["block_id"] == item["id"] and (not restore or locker["deleted_at"] == item["deleted_at"]):
                versions.update(version("locker", locker))
    return cmd(
        kind + (".restore" if restore else ".delete"), {"id": item["id"], "reason": "Prueba inventario"}, versions
    )


def test_remove_restore_and_export_sparse_block(system):
    _, client, _ = system
    data = client.get("/snapshot").json()
    locker = data["lockers"][0]
    request = removal(data, "locker", locker)
    result = client.post("/commands", json=request).json()
    assert result["status"] == "confirmada"
    assert client.post("/commands", json=request).json() == result
    data = client.get("/snapshot").json()
    assert len(data["lockers"]) == 15
    assert len(data["archived_lockers"]) == 1
    assert prepare_import(export_rows(data), data) == ([], {})
    request = removal(data, "block", data["blocks"][0])
    # One stale child version must roll back the whole removal.
    request["versions"]["locker:" + data["lockers"][-1]["id"]] = 999
    assert client.post("/commands", json=request).json()["status"] == "conflicto"
    assert len(client.get("/snapshot").json()["lockers"]) == 15
    request = removal(data, "block", data["blocks"][0])
    assert client.post("/commands", json=request).json()["status"] == "confirmada"
    data = client.get("/snapshot").json()
    assert not data["blocks"] and not data["lockers"]
    assert len(data["archived_lockers"]) == 16
    # Restore of the parent restores only children removed with it.
    request = removal(data, "block", data["archived_blocks"][0], True)
    assert client.post("/commands", json=request).json()["status"] == "confirmada"
    data = client.get("/snapshot").json()
    assert len(data["lockers"]) == 15
    assert all(item["condition"] == "pendiente" for item in data["lockers"])
    assert data["archived_lockers"][0]["id"] == locker["id"]
    assert (
        client.post("/commands", json=removal(data, "locker", data["archived_lockers"][0], True)).json()["status"]
        == "confirmada"
    )
    assert len(client.get("/snapshot").json()["lockers"]) == 16


def test_removal_preserves_history_and_blocks_active_assignments(system):
    _, client, _ = system
    data = client.get("/snapshot").json()
    employee, locker = data["employees"][0], data["lockers"][0]
    assert (
        client.post(
            "/commands",
            json=cmd(
                "assignment.assign",
                {"employee_id": employee["id"], "locker_id": locker["id"], "reason": "Prueba"},
                {**version("employee", employee), **version("locker", locker)},
            ),
        ).json()["status"]
        == "confirmada"
    )
    data = client.get("/snapshot").json()
    locker = next(item for item in data["lockers"] if item["id"] == locker["id"])
    for kind, item in [("block", data["blocks"][0]), ("locker", locker)]:
        assert client.post("/commands", json=removal(data, kind, item)).json()["status"] == "conflicto"
    a = data["assignments"][0]
    assert (
        client.post(
            "/commands",
            json=cmd(
                "assignment.release",
                {"employee_id": employee["id"], "assignment_id": a["id"], "reason": "Devuelto"},
                {**version("employee", data["employees"][0]), **version("locker", locker)},
            ),
        ).json()["status"]
        == "confirmada"
    )
    data = client.get("/snapshot").json()
    history = data["assignments"]
    assert client.post("/commands", json=removal(data, "block", data["blocks"][0])).json()["status"] == "confirmada"
    data = client.get("/snapshot").json()
    assert data["assignments"] == history
    assert len(data["employees"]) == 1
    assert any(event["action"] == "block.delete" for event in data["audit"])
    archived = data["archived_lockers"][0]
    assert (
        client.post(
            "/commands", json=cmd("locker.update", dict(archived, number="bad"), version("locker", archived))
        ).json()["status"]
        == "conflicto"
    )


def test_default_block_dimensions_and_permissions(system):
    engine, client, session = system
    payload = dict(
        plan_id="campus",
        building_id="building-1",
        label="N12",
        side="N",
        location="EXT",
        numbers=[str(i) for i in range(12)],
    )
    result = client.post("/commands", json=cmd("block.create", payload)).json()
    assert result["status"] == "confirmada"
    data = client.get("/snapshot").json()
    block = next(b for b in data["blocks"] if b["id"] == result["target_id"])
    assert (block["rows"], block["columns"]) == (4, 3)
    from sqlalchemy.orm import Session
    from slms.models import Admin

    with Session(engine) as db:
        db.get(Admin, session["actor"]["id"]).role = "operator"
        db.commit()
    for kind, item in [("block", block), ("locker", data["lockers"][0])]:
        assert client.post("/commands", json=removal(data, kind, item)).json()["status"] == "rechazada"
