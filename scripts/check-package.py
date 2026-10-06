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
import httpx
from slms.config import save_private

binary = Path(sys.argv[1]).resolve()
profile = Path(tempfile.mkdtemp(prefix="slms-package-check-"))
env = dict(os.environ, SLMS_HOME=str(profile), QT_QPA_PLATFORM="offscreen")
flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
subprocess.run([str(binary), "--self-test"], env=env, check=True, timeout=40, creationflags=flags)
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
        print("PASS: executable interface, server, authentication, atomic departure and unique simulated HR notice.")
        print("Preview profile: " + str(profile))
finally:
    process.terminate()
    process.wait(timeout=10)
