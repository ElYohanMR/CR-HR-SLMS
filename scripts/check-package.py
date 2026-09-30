"""Validate the executable's server in an isolated local profile."""

import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import httpx

binary = Path(sys.argv[1]).resolve()
profile = Path(tempfile.mkdtemp(prefix="slms-package-check-"))
env = dict(os.environ, SLMS_HOME=str(profile), QT_QPA_PLATFORM="offscreen")
flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
subprocess.run([str(binary), "--self-test"], env=env, check=True, timeout=40, creationflags=flags)
assert (profile / "self-test.json").exists()
os.environ["SLMS_HOME"] = str(profile)
from slms.config import save_private

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
        print("PASS: executable interface, encrypted configuration, server, authentication and inventory.")
finally:
    process.terminate()
    process.wait(timeout=10)
