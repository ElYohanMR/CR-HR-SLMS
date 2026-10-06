from concurrent.futures import ThreadPoolExecutor
import pytest
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker
from slms.models import Admin, Audit
from slms.service import execute
from conftest import cmd, version


def configure(client, hr="hr@example.com", employee_email="person@example.com", copy_hr=True):
    snapshot = client.get("/snapshot").json()
    settings = snapshot["mail_settings"][0]
    assert (
        client.post(
            "/commands",
            json=cmd(
                "mail_settings.update",
                {
                    "hr_email": hr,
                    "copy_hr_on_release": copy_hr,
                },
                version("mail_settings", settings),
            ),
        ).json()["status"]
        == "confirmada"
    )
    employee = snapshot["employees"][0]
    assert (
        client.post(
            "/commands",
            json=cmd("employee.update", dict(employee, email=employee_email), version("employee", employee)),
        ).json()["status"]
        == "confirmada"
    )


def assign(client):
    snapshot = client.get("/snapshot").json()
    employee, locker = snapshot["employees"][0], snapshot["lockers"][0]
    assert (
        client.post(
            "/commands",
            json=cmd(
                "assignment.assign",
                {
                    "employee_id": employee["id"],
                    "locker_id": locker["id"],
                    "reason": "Entrega",
                },
                version("employee", employee) | version("locker", locker),
            ),
        ).json()["status"]
        == "confirmada"
    )


def departure(client, kind="despido", verified=False):
    snapshot = client.get("/snapshot").json()
    employee = snapshot["employees"][0]
    current = next((a for a in snapshot["assignments"] if a["ended_at"] is None), None)
    locker = next((item for item in snapshot["lockers"] if current and item["id"] == current["locker_id"]), None)
    return cmd(
        "employee.deactivate",
        {
            "employee_id": employee["id"],
            "assignment_id": current["id"] if current else None,
            "departure_type": kind,
            "reason": "DETALLE INTERNO RESERVADO",
            "locker_verified": verified,
        },
        version("employee", employee) | (version("locker", locker) if locker else {}),
    )


@pytest.mark.parametrize("kind", ["despido", "renuncia", "fin_contrato", "otra_baja"])
def test_departure_atomic_audited_and_idempotent(system, kind):
    engine, client, session = system
    configure(client)
    assign(client)
    request = departure(client, kind)
    result = client.post("/commands", json=request).json()
    assert result["status"] == "confirmada"
    assert client.post("/commands", json=request).json() == result
    snapshot = client.get("/snapshot").json()
    employee, assignment = snapshot["employees"][0], snapshot["assignments"][0]
    assert not employee["active"] and employee["extra"]["departure"]["type"] == kind
    assert assignment["ended_at"] and assignment["ended_by"] == session["actor"]["id"]
    assert (
        next(item for item in snapshot["lockers"] if item["id"] == assignment["locker_id"])["condition"] == "pendiente"
    )
    notices = [n for n in snapshot["notifications"] if n["command_id"] == request["id"]]
    assert len(notices) == 1 and notices[0]["recipient"] == "hr@example.com" and notices[0]["cc"] == []
    assert "DETALLE INTERNO" not in notices[0]["body"] and "despido" not in notices[0]["body"].lower()
    with sessionmaker(engine)() as db:
        audits = list(db.scalars(select(Audit).where(Audit.command_id == request["id"])))
        assert {a.action for a in audits} == {"employee.deactivate", "assignment.release"}


def test_departure_without_locker_and_missing_hr(system):
    _, client, _ = system
    request = departure(client)
    assert client.post("/commands", json=request).json()["status"] == "confirmada"
    snapshot = client.get("/snapshot").json()
    assert not snapshot["employees"][0]["active"]
    notice = next(n for n in snapshot["notifications"] if n["command_id"] == request["id"])
    assert notice["recipient"] == "" and notice["status"] == "sin_destinatario"
    assert "Sin casillero" in notice["body"]


def test_departure_stale_locker_rolls_back_everything(system):
    _, client, _ = system
    assign(client)
    request = departure(client)
    for key in request["versions"]:
        if key.startswith("locker:"):
            request["versions"][key] = 999
    assert client.post("/commands", json=request).json()["status"] == "conflicto"
    snapshot = client.get("/snapshot").json()
    assert snapshot["employees"][0]["active"]
    assert snapshot["assignments"][0]["ended_at"] is None
    assert not any(n["command_id"] == request["id"] for n in snapshot["notifications"])
    assert not any(a["command_id"] == request["id"] for a in snapshot["audit"])


@pytest.mark.parametrize(
    "employee_email,hr,copy_hr,expected_to,expected_cc,expected_status",
    [
        ("person@example.com", "hr@example.com", True, "person@example.com", ["hr@example.com"], "simulado"),
        ("", "hr@example.com", True, "hr@example.com", [], "simulado"),
        ("person@example.com", "", True, "person@example.com", [], "simulado_sin_hr"),
        ("", "", True, "", [], "sin_destinatario"),
        ("person@example.com", "hr@example.com", False, "person@example.com", [], "simulado"),
        ("hr@example.com", "HR@example.com", True, "hr@example.com", [], "simulado"),
    ],
)
def test_voluntary_release_routes_notice_and_keeps_employee_active(
    system, employee_email, hr, copy_hr, expected_to, expected_cc, expected_status
):
    _, client, _ = system
    configure(client, hr, employee_email, copy_hr)
    assign(client)
    request = departure(client)
    request["action"] = "assignment.release"
    request["payload"]["reason"] = "Solicitud del empleado: observación interna"
    request["payload"]["locker_verified"] = True
    result = client.post("/commands", json=request).json()
    assert result["status"] == "confirmada"
    assert client.post("/commands", json=request).json() == result
    snapshot = client.get("/snapshot").json()
    assert snapshot["employees"][0]["active"]
    assert snapshot["assignments"][0]["ended_at"]
    assert all(item["condition"] == "utilizable" for item in snapshot["lockers"])
    notices = [n for n in snapshot["notifications"] if n["command_id"] == request["id"]]
    assert len(notices) == 1
    assert (notices[0]["recipient"], notices[0]["cc"], notices[0]["status"]) == (
        expected_to,
        expected_cc,
        expected_status,
    )
    assert "observación interna" not in notices[0]["body"]


def test_offline_departure_competes_with_reassignment(system):
    engine, client, session = system
    assign(client)
    request = departure(client)
    snapshot = client.get("/snapshot").json()
    new = next(item for item in snapshot["lockers"] if "locker:" + item["id"] not in request["versions"])
    transfer = cmd(
        "assignment.transfer",
        {
            "employee_id": request["payload"]["employee_id"],
            "assignment_id": request["payload"]["assignment_id"],
            "locker_id": new["id"],
            "reason": "Cambio simultáneo",
        },
        request["versions"] | version("locker", new),
    )
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda c: execute(engine, session["actor"]["id"], c), [request, transfer]))
    assert sum(r["status"] == "confirmada" for r in results) == 1
    snapshot = client.get("/snapshot").json()
    current = [a for a in snapshot["assignments"] if a["ended_at"] is None]
    assert len(current) == (1 if snapshot["employees"][0]["active"] else 0)


def test_only_admin_changes_mail_routing_and_readers_cannot_depart(system):
    engine, client, session = system
    request = departure(client)
    for role in ("operator", "viewer"):
        with sessionmaker(engine).begin() as db:
            db.get(Admin, session["actor"]["id"]).role = role
        settings = client.get("/snapshot").json()["mail_settings"][0]
        setting_request = cmd(
            "mail_settings.update", {"hr_email": "hr@example.com"}, version("mail_settings", settings)
        )
        assert client.post("/commands", json=setting_request).json()["status"] == "rechazada"
    assert client.post("/commands", json=request).json()["status"] == "rechazada"


def test_upgrade_keeps_existing_notifications_and_history(system):
    engine, client, _ = system
    from alembic import command
    from alembic.config import Config
    from slms.config import asset
    from slms.database import migrate

    assign(client)
    old = client.get("/snapshot").json()
    cfg = Config()
    cfg.set_main_option("script_location", str(asset("../migrations").resolve()))
    with engine.begin() as connection:
        cfg.attributes["connection"] = connection
        command.downgrade(cfg, "0001")
    migrate(engine)
    new = client.get("/snapshot").json()
    assert new["employees"] == old["employees"]
    assert new["assignments"] == old["assignments"]
    assert new["notifications"][0]["recipient"] == old["notifications"][0]["recipient"]
    assert new["notifications"][0]["cc"] == []
    assert new["mail_settings"][0]["id"] == "mail"
