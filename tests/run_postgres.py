"""Run the suite on an isolated PostgreSQL cluster, never the user's database."""

import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import tempfile
from urllib.parse import quote


def main():
    binaries = Path(os.environ.get("PROGRAMFILES", "C:/Program Files")) / "PostgreSQL/18/bin"
    root = Path(tempfile.mkdtemp(prefix="slms-pg-tests-"))
    password = secrets.token_urlsafe(30)
    password_file = root / "password.txt"
    password_file.write_text(password, encoding="utf-8")
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)

    def run(args):
        with open(root / "commands.log", "ab") as log:
            result = subprocess.run(args, stdout=log, stderr=log, creationflags=flags, timeout=90)
        if result.returncode:
            raise RuntimeError("Falló una herramienta de PostgreSQL. Revisa " + str(root / "commands.log"))

    started = False
    try:
        run(
            [
                str(binaries / "initdb.exe"),
                "-D",
                str(root / "data"),
                "-U",
                "slms_test",
                "--auth=scram-sha-256",
                "--pwfile",
                str(password_file),
                "--encoding=UTF8",
                "--locale=C",
            ]
        )
        run(
            [
                str(binaries / "pg_ctl.exe"),
                "-D",
                str(root / "data"),
                "-l",
                str(root / "postgres.log"),
                "-o",
                f"-h 127.0.0.1 -p {port}",
                "-w",
                "start",
            ]
        )
        started = True
        env = dict(
            os.environ, SLMS_TEST_POSTGRES=f"postgresql+psycopg://slms_test:{quote(password)}@127.0.0.1:{port}/postgres"
        )
        result = subprocess.run([sys.executable, "-m", "pytest", "-q", "--disable-warnings", "--maxfail=3"], env=env)
        return result.returncode
    finally:
        if started:
            run([str(binaries / "pg_ctl.exe"), "-D", str(root / "data"), "-w", "stop", "-m", "fast"])
        password_file.unlink(missing_ok=True)


if __name__ == "__main__":
    sys.exit(main())
