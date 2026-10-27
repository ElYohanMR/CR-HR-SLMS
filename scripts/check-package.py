"""Validate the executable's server in an isolated local profile."""

import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import uuid
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
import httpx
from slms.config import save_private

binary = Path(sys.argv[1]).resolve()
profile = Path(tempfile.mkdtemp(prefix="slms-package-check-"))
env = dict(os.environ, SLMS_HOME=str(profile), QT_QPA_PLATFORM="offscreen")
flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
subprocess.run([str(binary), "--self-test"], env=env, check=True, timeout=120, creationflags=flags)
assert (profile / "self-test.json").exists()
os.environ["SLMS_HOME"] = str(profile)

with socket.socket() as sock:
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
url = f"http://127.0.0.1:{port}"
save_private(
    "connection.dat",
    {
        "mode": "demo",
        "database_url": "sqlite:///" + (profile / "smoke.sqlite3").as_posix(),
        "url": url,
        "installation": "package-validation",
        "bind": "127.0.0.1",
        "port": port,
    },
)
process = subprocess.Popen([str(binary), "--server"], env=env, creationflags=flags)
try:
    with httpx.Client(base_url=url, timeout=2, trust_env=False) as client:
        for _ in range(50):
            try:
                if client.get("/health").status_code == 200:
                    break
            except httpx.HTTPError:
                pass
            time.sleep(0.2)
        assert client.get("/snapshot").status_code == 401
        session = client.post("/login", json={"username": "preview", "password": "Preview-only-password-42"}).json()
        client.headers["Authorization"] = "Bearer " + session["token"]
        snapshot = client.get("/snapshot").json()
        assert len(snapshot["lockers"]) == 16
        assert len(snapshot["plans"]) == 1

        def request(action, payload, versions):
            return {
                "id": str(uuid.uuid4()),
                "device_id": "package-check",
                "client_at": datetime.now(timezone.utc).isoformat(),
                "action": action,
                "payload": payload,
                "versions": versions,
            }

        settings = snapshot["mail_settings"][0]
        notice_settings = request(
            "mail_settings.update", {"hr_email": "hr@example.com"}, {"mail_settings:mail": settings["version"]}
        )
        assert client.post("/commands", json=notice_settings).json()["status"] == "confirmada"
        employee = snapshot["employees"][0]
        assignment = next(a for a in snapshot["assignments"] if a["ended_at"] is None)
        locker = next(item for item in snapshot["lockers"] if item["id"] == assignment["locker_id"])
        # The standalone server has no QApplication; verify JPEG decoding and private retrieval there.
        import base64
        from PySide6.QtCore import QBuffer, QIODevice
        from PySide6.QtGui import QImage
        cut = request("cut.create", {"employee_id": employee["id"], "locker_id": locker["id"],
                                    "supervisor": "Prueba aislada", "reason": "Validar ejecutable",
                                    "channel": "otro"},
                      {"employee:" + employee["id"]: employee["version"], "locker:" + locker["id"]: locker["version"]})
        result = client.post("/commands", json=cut).json()
        assert result["status"] == "confirmada", result
        cut_id = result["target_id"]
        held = next(item for item in client.get("/snapshot").json()["lockers"] if item["id"] == locker["id"])
        assert held["condition"] == "mantenimiento"
        assert held["condition_after_cut"] == locker["condition"]
        def cut_step(action, payload):
            item = next(c for c in client.get("/snapshot").json()["cut_requests"] if c["id"] == cut_id)
            command = request(action, dict(payload, id=cut_id), {"cut_request:" + cut_id: item["version"]})
            result = client.post("/commands", json=command).json()
            assert result["status"] == "confirmada", result
        cut_step("cut.assign", {"assignee": "Seguridad de prueba"})
        image = QImage(100, 60, QImage.Format.Format_RGB32)
        image.fill(0xFF336699)
        buffer = QBuffer()
        buffer.open(QIODevice.OpenModeFlag.WriteOnly)
        assert image.save(buffer, "JPG")
        data = bytes(buffer.data())
        cut_step("cut.evidence", {"kind": "identidad", "filename": "PRUEBA-FICTICIA.jpg",
                                  "photo": base64.b64encode(data).decode()})
        evidence = next(e for e in client.get("/snapshot").json()["cut_evidence"] if e["request_id"] == cut_id)
        assert client.get("/cuts/evidence/" + evidence["id"]).content == data
        assert client.get("/cuts/" + cut_id + "/history").status_code == 200
        cut_step("cut.complete", {"identity_verified": True,
            "performed_at": datetime.now(timezone.utc).isoformat(), "result": "Corte con una fotografía opcional."})
        restored = next(item for item in client.get("/snapshot").json()["lockers"] if item["id"] == locker["id"])
        assert restored["condition"] == locker["condition"]
        assert restored["condition_after_cut"] is None
        assert restored["version"] == locker["version"] + 2
        locker = restored
        assert snapshot["features"]["locker_padlock"]
        update = request("locker.update", {"id": locker["id"], "number": locker["number"],
            "condition": locker["condition"], "notes": locker["notes"], "has_padlock": True},
            {"locker:" + locker["id"]: locker["version"]})
        result = client.post("/commands", json=update).json()
        assert result["status"] == "confirmada", result
        locker = next(e for e in client.get("/snapshot").json()["lockers"] if e["id"] == locker["id"])
        assert locker["has_padlock"] is True
        departure = request(
            "employee.deactivate",
            {
                "employee_id": employee["id"],
                "assignment_id": assignment["id"],
                "departure_type": "fin_contrato",
                "reason": "Prueba aislada del ejecutable",
            },
            {"employee:" + employee["id"]: employee["version"], "locker:" + locker["id"]: locker["version"]},
        )
        result = client.post("/commands", json=departure).json()
        assert result["status"] == "confirmada"
        assert client.post("/commands", json=departure).json() == result
        snapshot = client.get("/snapshot").json()
        assert not snapshot["employees"][0]["active"]
        notices = [n for n in snapshot["notifications"] if n["command_id"] == departure["id"]]
        assert len(notices) == 1 and notices[0]["recipient"] == "hr@example.com"
        assert notices[0]["status"] == "simulado"
        assert snapshot["features"]["audit_date_range"]
        local_day = datetime.fromisoformat(snapshot["at"]).astimezone(ZoneInfo("America/Costa_Rica")).date().isoformat()
        dated = client.get("/audit", params={"date_from": local_day, "date_to": local_day})
        assert dated.status_code == 200
        assert any(event["command_id"] == departure["id"] for event in dated.json())
        assert client.get("/audit", params={"date_from": "2000-01-01", "date_to": "2000-01-01"}).json() == []
        print("PASS: executable interface, server, authentication, padlock cuts, original JPEG evidence, case history, atomic departure and unique simulated HR notice.")
        print("PASS: packaged history date filter with Costa Rica calendar dates.")
        print("Preview profile: " + str(profile))
finally:
    process.terminate()
    process.wait(timeout=10)
