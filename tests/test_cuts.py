import base64
import hashlib
from datetime import datetime, timedelta, timezone

import pytest
from PySide6.QtCore import QBuffer, QIODevice
from PySide6.QtGui import QImage, QColor
from sqlalchemy import select
from sqlalchemy.orm import Session

from conftest import cmd, version
from slms.models import CutRequest, CutEvidence, Admin, now


def photo(color="red"):
    image = QImage(80, 60, QImage.Format.Format_RGB32)
    image.fill(QColor(color))
    buffer = QBuffer()
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    assert image.save(buffer, "PNG")
    return bytes(buffer.data())


def post(client, action, payload, item=None):
    return client.post("/commands", json=cmd(action, payload, version("cut_request", item) if item else {})).json()


def latest(client, id):
    return next(e for e in client.get("/snapshot").json()["cut_requests"] if e["id"] == id)


def create(client, locker_id=None, employee_id=None):
    snapshot = client.get("/snapshot").json()
    employee = next(e for e in snapshot["employees"] if e["id"] == employee_id) if employee_id else snapshot["employees"][0]
    locker = next(e for e in snapshot["lockers"] if e["id"] == locker_id) if locker_id else snapshot["lockers"][0]
    request = cmd("cut.create", {"employee_id": employee["id"], "locker_id": locker["id"],
                                "supervisor": "Supervisora ficticia", "reason": "Llaves extraviadas",
                                "channel": "teams"},
                  version("employee", employee) | version("locker", locker))
    result = client.post("/commands", json=request).json()
    assert result["status"] == "confirmada", result
    return latest(client, result["target_id"]), request


def assigned(client):
    item, _ = create(client)
    assert post(client, "cut.assign", {"id": item["id"], "assignee": "Seguridad de prueba"}, item)["status"] == "confirmada"
    return latest(client, item["id"])


def attach(client, item, kind, color, **extra):
    return post(client, "cut.evidence", {"id": item["id"], "kind": kind, "filename": "evidencia.png",
                                       "photo": base64.b64encode(photo(color)).decode(), **extra}, item)


def test_complete_case_original_photos_and_audit(system):
    engine, client, session = system
    item, request = create(client)
    assert client.post("/commands", json=request).json()["target_id"] == item["id"]
    snapshot_before = client.get("/snapshot").json()
    assert post(client, "cut.assign", {"id": item["id"], "assignee": "Encargado de seguridad"}, item)["status"] == "confirmada"
    item = latest(client, item["id"])
    for kind, color in (("identidad", "red"), ("antes", "green"), ("despues", "blue")):
        assert attach(client, item, kind, color)["status"] == "confirmada"
        item = latest(client, item["id"])
    done = cmd("cut.complete", {"id": item["id"], "identity_verified": True, "performed_at": now(),
                               "result": "Corte realizado en presencia del empleado."}, version("cut_request", item))
    result = client.post("/commands", json=done).json()
    assert result["status"] == "confirmada", result
    assert client.post("/commands", json=done).json() == result
    snapshot = client.get("/snapshot").json()
    item = latest(client, item["id"])
    assert item["status"] == "finalizada" and item["completed_by"] == session["actor"]["id"]
    assert item["identity_verified"] and item["performed_at"]
    before_locker = next(e for e in snapshot_before["lockers"] if e["id"] == item["locker_id"])
    after_locker = next(e for e in snapshot["lockers"] if e["id"] == item["locker_id"])
    assert before_locker["condition"] == "mantenimiento"
    assert after_locker["condition"] == before_locker["condition_after_cut"]
    assert after_locker["condition_after_cut"] is None
    assert after_locker["version"] == before_locker["version"] + 1
    assert snapshot["assignments"] == snapshot_before["assignments"]
    assert snapshot["employees"] == snapshot_before["employees"]
    evidence = snapshot["cut_evidence"][0]
    assert "content" not in evidence and "photo" not in evidence
    response = client.get("/cuts/evidence/" + evidence["id"])
    assert response.headers["cache-control"] == "no-store"
    assert hashlib.sha256(response.content).hexdigest() == evidence["sha256"]
    history = client.get("/cuts/" + item["id"] + "/history").json()
    assert len(history) == 9
    assert all(e["actor_id"] == session["actor"]["id"] for e in history)
    assert all("content" not in e["after"] for e in history)
    assert post(client, "cut.cancel", {"id": item["id"], "reason": "No modificar"}, item)["status"] == "conflicto"
    with Session(engine) as db:
        assert len(list(db.scalars(select(CutRequest)))) == 1
        assert len(list(db.scalars(select(CutEvidence)))) == 3


def test_missing_fields_duplicate_open_and_stale_version(system):
    _, client, _ = system
    item, request = create(client)
    request["id"] = cmd("unused", {})["id"]
    assert client.post("/commands", json=request).json()["status"] == "conflicto"
    assert post(client, "cut.complete", {"id": item["id"]}, item)["status"] == "rechazada"
    assert attach(client, item, "antes", "red")["status"] == "rechazada"
    assert post(client, "cut.assign", {"id": item["id"], "assignee": "Encargado"}, item)["status"] == "confirmada"
    assert post(client, "cut.cancel", {"id": item["id"], "reason": "Solicitud antigua"}, item)["status"] == "conflicto"
    current = latest(client, item["id"])
    assert post(client, "cut.update", {"id": item["id"], "supervisor": "Otro", "reason": "Nuevo",
                                     "channel": "correo"}, current)["status"] == "rechazada"
    assert latest(client, item["id"])["version"] == current["version"]


def test_cancel_retains_case_and_allows_new_request(system):
    _, client, _ = system
    item, _ = create(client)
    assert post(client, "cut.cancel", {"id": item["id"], "reason": ""}, item)["status"] == "rechazada"
    assert post(client, "cut.cancel", {"id": item["id"], "reason": "Encontró las llaves"}, item)["status"] == "confirmada"
    closed = latest(client, item["id"])
    assert closed["status"] == "cancelada" and closed["completed_at"]
    assert create(client)[0]["id"] != item["id"]


def test_photo_replacement_history_and_duplicates(system):
    _, client, _ = system
    item = assigned(client)
    assert attach(client, item, "identidad", "red")["status"] == "confirmada"
    item = latest(client, item["id"])
    assert attach(client, item, "antes", "red")["status"] == "rechazada"
    assert attach(client, item, "identidad", "yellow")["status"] == "rechazada"
    assert attach(client, item, "identidad", "yellow", reason="Primera foto desenfocada")["status"] == "confirmada"
    evidence = client.get("/snapshot").json()["cut_evidence"]
    assert len(evidence) == 2 and sum(e["current"] for e in evidence) == 1
    old = next(e for e in evidence if not e["current"])
    assert client.get("/cuts/evidence/" + old["id"]).content == photo("red")


@pytest.mark.parametrize("value", ["!!!", base64.b64encode(b"not an image").decode(), "a" * 8_000_001],
                         ids=["invalid-base64", "invalid-image", "oversized"])
def test_bad_evidence_does_not_change_version(system, value):
    _, client, _ = system
    item = assigned(client)
    result = post(client, "cut.evidence", {"id": item["id"], "kind": "identidad",
                                         "filename": "test.png", "photo": value}, item)
    assert result["status"] == "rechazada"
    assert latest(client, item["id"])["version"] == item["version"]
    assert client.get("/snapshot").json()["cut_evidence"] == []


def test_completion_requires_identity_and_valid_date(system):
    _, client, _ = system
    item = assigned(client)
    for kind, color in (("identidad", "red"), ("antes", "green"), ("despues", "blue")):
        assert attach(client, item, kind, color)["status"] == "confirmada"
        item = latest(client, item["id"])
    for overrides in ({"identity_verified": False}, {"identity_verified": "true"}, {"result": ""},
                      {"performed_at": "2020-01-01"}, {"performed_at": "2020-01-01T00:00:00Z"},
                      {"performed_at": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()}):
        p = {"id": item["id"], "identity_verified": True, "performed_at": now(), "result": "Prueba"} | overrides
        assert post(client, "cut.complete", p, item)["status"] == "rechazada"
    assert latest(client, item["id"])["status"] == "en_proceso"


def test_permissions_and_authenticated_photos(system):
    engine, client, session = system
    item = assigned(client)
    assert attach(client, item, "identidad", "red")["status"] == "confirmada"
    photo_id = client.get("/snapshot").json()["cut_evidence"][0]["id"]
    with Session(engine) as db:
        db.get(Admin, session["actor"]["id"]).role = "viewer"
        db.commit()
    assert post(client, "cut.cancel", {"id": item["id"], "reason": "Sin permisos"}, latest(client, item["id"]))["status"] == "rechazada"
    assert client.get("/cuts/evidence/" + photo_id).status_code == 403
    client.headers.pop("Authorization")
    assert client.get("/cuts/evidence/" + photo_id).status_code == 401
    assert client.get("/cuts/" + item["id"] + "/history").status_code == 401


def test_operator_can_process_and_purge_preserves_cut_history(system):
    engine, client, session = system
    with Session(engine) as db:
        db.get(Admin, session["actor"]["id"]).role = "operator"
        db.commit()
    item, _ = create(client)
    assert post(client, "cut.assign", {"id": item["id"], "assignee": "Seguridad"}, item)["status"] == "confirmada"
    with Session(engine) as db:
        db.get(Admin, session["actor"]["id"]).role = "admin"
        db.commit()
    locker = next(e for e in client.get("/snapshot").json()["lockers"] if e["id"] == item["locker_id"])
    result = client.post("/commands", json=cmd("locker.delete", {"id": locker["id"], "reason": "Prueba"},
                                               version("locker", locker))).json()
    assert result["status"] == "confirmada"
    locker = next(e for e in client.get("/snapshot").json()["archived_lockers"] if e["id"] == locker["id"])
    result = client.post("/commands", json=cmd("inventory.purge", {"items": [{"kind": "locker", "id": locker["id"]}],
                                              "reason": "Prueba", "confirmation": "ELIMINAR"},
                                               version("locker", locker))).json()
    assert result["status"] == "rechazada" and "corte" in result["message"]


def test_concurrent_assignments_have_one_winner(system):
    from concurrent.futures import ThreadPoolExecutor
    from slms.service import execute
    engine, client, session = system
    item, _ = create(client)
    requests = [cmd("cut.assign", {"id": item["id"], "assignee": name}, version("cut_request", item))
                for name in ("Seguridad uno", "Seguridad dos")]
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda c: execute(engine, session["actor"]["id"], c), requests))
    assert sorted(r["status"] for r in results) == ["confirmada", "conflicto"]
    assert latest(client, item["id"])["version"] == item["version"] + 1


def test_upgrade_from_previous_release_preserves_existing_data(system):
    from alembic import command
    from alembic.config import Config
    from slms.config import asset
    from slms.database import migrate
    engine, client, _ = system
    before = client.get("/snapshot").json()
    cfg = Config()
    cfg.set_main_option("script_location", str(asset("../migrations").resolve()))
    with engine.begin() as conn:
        cfg.attributes["connection"] = conn
        command.downgrade(cfg, "0005")
    migrate(engine)
    migrate(engine)
    after = client.get("/snapshot").json()
    for locker in before["lockers"]:
        locker["has_padlock"] = None
    for name in ("employees", "lockers", "blocks", "assignments", "admins", "plans"):
        assert after[name] == before[name]
    assert all(e["has_padlock"] is None for e in after["lockers"])
    assert after["cut_requests"] == [] and after["cut_evidence"] == []

@pytest.mark.parametrize("photo_count", [0, 1, 2])
def test_completion_with_optional_photographs(system, photo_count):
    _, client, _ = system
    item = assigned(client)
    for kind, color in list((("identidad", "red"), ("antes", "green")))[:photo_count]:
        assert attach(client, item, kind, color)["status"] == "confirmada"
        item = latest(client, item["id"])
    result = post(client, "cut.complete", {"id": item["id"], "performed_at": now(),
        "identity_verified": True, "result": "Corte realizado"}, item)
    assert result["status"] == "confirmada", result
    assert latest(client, item["id"])["status"] == "finalizada"
    assert len(client.get("/snapshot").json()["cut_evidence"]) == photo_count
