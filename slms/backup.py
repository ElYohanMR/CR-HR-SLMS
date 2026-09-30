from datetime import datetime
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
from .config import home


def create_backup(engine):
    folder = home() / "backups"
    folder.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    url = engine.url
    if engine.dialect.name == "sqlite":
        dest = folder / f"samtec-{stamp}.sqlite3"
        with sqlite3.connect(url.database) as source, sqlite3.connect(dest) as target:
            source.backup(target)
        return dest
    binary = shutil.which("pg_dump") or str(
        Path(os.environ.get("PROGRAMFILES", "C:/Program Files")) / "PostgreSQL/18/bin/pg_dump.exe"
    )
    dest = folder / f"samtec-{stamp}.dump"
    env = dict(os.environ, PGPASSWORD=url.password or "")
    try:
        subprocess.run(
            [
                binary,
                "--host",
                url.host or "127.0.0.1",
                "--port",
                str(url.port or 5432),
                "--username",
                url.username,
                "--dbname",
                url.database,
                "--format=custom",
                "--no-owner",
                "--file",
                str(dest),
            ],
            env=env,
            check=True,
            timeout=120,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except Exception:
        dest.unlink(missing_ok=True)
        raise
    return dest
