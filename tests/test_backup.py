import os
from pathlib import Path
import sqlite3
import subprocess
import uuid
from sqlalchemy import text
from slms.database import engine_for
from slms.backup import create_backup


def test_backup_restores_data(system):
    engine, client, _ = system
    from test_cuts import assigned, attach, photo
    item = assigned(client)
    assert attach(client, item, "identidad", "red")["status"] == "confirmada"
    path = create_backup(engine)
    assert path.exists() and path.stat().st_size > 0
    if engine.dialect.name == "sqlite":
        with sqlite3.connect(path) as restored:
            assert restored.execute("SELECT COUNT(*) FROM lockers").fetchone()[0] == 16
            assert restored.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
            assert restored.execute("SELECT content FROM cut_evidence").fetchone()[0] == photo("red")
            assert restored.execute("SELECT status FROM cut_requests").fetchone()[0] == "en_proceso"
        return
    # This branch only runs in the isolated cluster started by run_postgres.py.
    assert os.environ.get("SLMS_TEST_POSTGRES")
    database = "restore_" + uuid.uuid4().hex
    root_engine = engine_for(os.environ["SLMS_TEST_POSTGRES"])
    with root_engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
        conn.execute(text(f'CREATE DATABASE "{database}"'))
    restored = None
    try:
        url = engine.url
        tool = Path(os.environ.get("PROGRAMFILES", "C:/Program Files")) / "PostgreSQL/18/bin/pg_restore.exe"
        subprocess.run(
            [
                str(tool),
                "-h",
                url.host,
                "-p",
                str(url.port),
                "-U",
                url.username,
                "-d",
                database,
                "--no-owner",
                "--exit-on-error",
                str(path),
            ],
            env=dict(os.environ, PGPASSWORD=url.password),
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            timeout=60,
        )
        restored = engine_for(url.set(database=database).render_as_string(hide_password=False))
        with restored.connect() as conn:
            schemas = (
                conn.execute(
                    text("SELECT schema_name FROM information_schema.schemata WHERE schema_name LIKE 'test_%'")
                )
                .scalars()
                .all()
            )
            assert len(schemas) == 1
            assert conn.execute(text(f'SELECT count(*) FROM "{schemas[0]}".lockers')).scalar() == 16
            assert bytes(conn.execute(text(f'SELECT content FROM "{schemas[0]}".cut_evidence')).scalar()) == photo("red")
            assert conn.execute(text(f'SELECT status FROM "{schemas[0]}".cut_requests')).scalar() == "en_proceso"
    finally:
        if restored:
            restored.dispose()
        with root_engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
            conn.execute(text(f'DROP DATABASE "{database}"'))
        root_engine.dispose()
