import copy
from concurrent.futures import ThreadPoolExecutor
import pytest
from sqlalchemy import select, func
from sqlalchemy.orm import sessionmaker
from slms.models import Assignment, Audit, Receipt, Admin
from slms.service import execute
from conftest import cmd, version


def assignment_command(client, locker_index=0):
    data = client.get("/snapshot").json()
    employee = data["employees"][0]
    locker = data["lockers"][locker_index]
    return cmd(
        "assignment.assign",
        {"employee_id": employee["id"], "locker_id": locker["id"], "reason": "Entrega verificada"},
        version("employee", employee) | version("locker", locker),
    )


def test_idempotency_survives_lost_response(system):
    engine, client, session = system
    command = assignment_command(client)
    result = client.post("/commands", json=command)
    assert result.json()["status"] == "confirmada"
    assert client.post("/commands", json=command).json() == result.json()
    with sessionmaker(engine)() as db:
        assert db.scalar(select(func.count()).select_from(Assignment)) == 1
        assert db.scalar(select(func.count()).select_from(Audit)) == 1
        assert db.scalar(select(func.count()).select_from(Receipt)) == 1


def test_reused_identifier_cannot_change_payload(system):
    _, client, _ = system
    command = assignment_command(client)
    client.post("/commands", json=command)
    command["payload"]["reason"] = "Different"
    assert client.post("/commands", json=command).status_code == 409


def test_two_disconnected_requests_only_one_wins(system):
    engine, client, session = system
    first = assignment_command(client)
    second = copy.deepcopy(first)
    second["id"] = cmd("", {})["id"]
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda c: execute(engine, session["actor"]["id"], c), [first, second]))
    assert sorted(r["status"] for r in results) == ["confirmada", "conflicto"]
    with sessionmaker(engine)() as db:
        assert db.scalar(select(func.count()).select_from(Assignment).where(Assignment.ended_at.is_(None))) == 1


def test_same_locker_two_employees(system):
    engine, client, session = system
    client.post(
        "/commands",
        json=cmd("employee.create", {"employee_number": "SECOND", "first_name": "Segundo", "surname": "Ejemplo"}),
    )
    data = client.get("/snapshot").json()
    locker = data["lockers"][0]
    requests = [
        cmd(
            "assignment.assign",
            {"employee_id": e["id"], "locker_id": locker["id"], "reason": "Entrega"},
            version("employee", e) | version("locker", locker),
        )
        for e in data["employees"]
    ]
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda c: execute(engine, session["actor"]["id"], c), requests))
    assert sum(r["status"] == "confirmada" for r in results) == 1


def test_transfer_rollback_and_release(system):
    _, client, _ = system
    client.post("/commands", json=assignment_command(client))
    data = client.get("/snapshot").json()
    employee = data["employees"][0]
    current = data["assignments"][0]
    old = next(x for x in data["lockers"] if x["id"] == current["locker_id"])
    new = data["lockers"][1]
    request = cmd(
        "assignment.transfer",
        {"employee_id": employee["id"], "locker_id": new["id"], "assignment_id": current["id"], "reason": "Traslado"},
        version("employee", employee) | version("locker", old) | version("locker", new),
    )
    request["versions"]["locker:" + new["id"]] = 999
    assert client.post("/commands", json=request).json()["status"] == "conflicto"
    assert client.get("/snapshot").json()["assignments"][0]["ended_at"] is None
    request["id"] = cmd("", {})["id"]
    request["versions"]["locker:" + new["id"]] = new["version"]
    assert client.post("/commands", json=request).json()["status"] == "confirmada"
    data = client.get("/snapshot").json()
    current = next(a for a in data["assignments"] if a["ended_at"] is None)
    assert current["locker_id"] == new["id"]
    employee = data["employees"][0]
    locker = next(x for x in data["lockers"] if x["id"] == new["id"])
    release = cmd(
        "assignment.release",
        {"employee_id": employee["id"], "assignment_id": current["id"], "reason": "Devolución"},
        version("employee", employee) | version("locker", locker),
    )
    assert client.post("/commands", json=release).json()["status"] == "confirmada"
    assert all(a["ended_at"] for a in client.get("/snapshot").json()["assignments"])


def test_unverified_is_not_available_and_unique_block_numbers(system):
    _, client, _ = system
    block = cmd(
        "block.create",
        {
            "plan_id": "campus",
            "building_id": "building-1",
            "label": "S02",
            "side": "S",
            "location": "EXT",
            "rows": 3,
            "columns": 4,
            "numbers": [str(i) for i in range(100, 112)],
        },
    )
    assert client.post("/commands", json=block).json()["status"] == "confirmada"
    data = client.get("/snapshot").json()
    employee = data["employees"][0]
    locker = next(item for item in data["lockers"] if item["number"] == "100")
    assert locker["condition"] == "pendiente"
    command = cmd(
        "assignment.assign",
        {"employee_id": employee["id"], "locker_id": locker["id"], "reason": "Entrega"},
        version("employee", employee) | version("locker", locker),
    )
    assert client.post("/commands", json=command).json()["status"] == "rechazada"
    block["id"] = cmd("", {})["id"]
    block["payload"]["label"] = "S03"
    assert client.post("/commands", json=block).json()["status"] == "conflicto"
    assert len(client.get("/snapshot").json()["blocks"]) == 2


def test_stale_employee_and_inactivation_with_assignment(system):
    _, client, _ = system
    employee = client.get("/snapshot").json()["employees"][0]
    update = cmd("employee.update", dict(employee, notes="Actualización"), version("employee", employee))
    assert client.post("/commands", json=update).json()["status"] == "confirmada"
    update["id"] = cmd("", {})["id"]
    assert client.post("/commands", json=update).json()["status"] == "conflicto"
    client.post("/commands", json=assignment_command(client))
    employee = client.get("/snapshot").json()["employees"][0]
    assert (
        client.post(
            "/commands", json=cmd("employee.update", dict(employee, active=False), version("employee", employee))
        ).json()["status"]
        == "rechazada"
    )


def test_auth_roles_and_notification_transaction(system):
    engine, client, _ = system
    employee = client.get("/snapshot").json()["employees"][0]
    client.post(
        "/commands",
        json=cmd("employee.update", dict(employee, email="demo@example.com"), version("employee", employee)),
    )
    client.post("/commands", json=assignment_command(client))
    assert client.get("/snapshot").json()["notifications"][0]["status"] == "simulado"
    create = cmd(
        "admin.create", {"username": "reader", "name": "Consulta", "role": "viewer", "password": "ReaderPassword42"}
    )
    assert client.post("/commands", json=create).json()["status"] == "confirmada"
    token = client.post("/login", json={"username": "reader", "password": "ReaderPassword42"}).json()["token"]
    client.headers["Authorization"] = "Bearer " + token
    assert (
        client.post(
            "/commands", json=cmd("employee.create", {"employee_number": "X", "first_name": "X", "surname": "X"})
        ).json()["status"]
        == "rechazada"
    )
    assert client.post("/backup").status_code == 403
    client.headers.pop("Authorization")
    assert client.get("/snapshot").status_code == 401


def test_map_roundtrip_and_invalid_geometry(system):
    _, client, _ = system
    plan = client.get("/snapshot").json()["plans"][0]
    payload = copy.deepcopy(plan)
    payload["polygons"][0]["points"][0] = [200, 200]
    assert (
        client.post("/commands", json=cmd("plan.update", payload, version("plan", plan))).json()["status"]
        == "confirmada"
    )
    plan = client.get("/snapshot").json()["plans"][0]
    assert plan["polygons"][0]["points"][0] == [200, 200]
    payload = copy.deepcopy(plan)
    payload["polygons"][0]["points"][0] = [-5, 200]
    assert (
        client.post("/commands", json=cmd("plan.update", payload, version("plan", plan))).json()["status"]
        == "rechazada"
    )


def test_database_enforces_active_uniqueness(system):
    engine, client, _ = system
    client.post("/commands", json=assignment_command(client))
    from sqlalchemy.exc import IntegrityError

    with sessionmaker(engine)() as db:
        current = db.scalar(select(Assignment))
        db.add(
            Assignment(
                employee_id=current.employee_id,
                locker_id=current.locker_id,
                started_by=current.started_by,
                reason="Invalid direct insert",
            )
        )
        with pytest.raises(IntegrityError):
            db.commit()


def test_initialization_preserves_existing_data(system):
    from slms.database import initialize, password_matches

    engine, _, _ = system
    assert initialize(engine, "different", "DifferentPassword42") is False
    with sessionmaker(engine)() as db:
        admin = db.scalar(select(Admin))
        assert admin.username == "admin" and password_matches("A-test-password-42", admin.password_hash)
