import os
import uuid
import pytest
from sqlalchemy import text
from fastapi.testclient import TestClient
from slms.database import engine_for, initialize
from slms.api import create_app

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture
def system(tmp_path, monkeypatch):
    monkeypatch.setenv("SLMS_HOME", str(tmp_path / "local"))
    pg = os.environ.get("SLMS_TEST_POSTGRES")
    engine = engine_for(pg or "sqlite:///" + (tmp_path / "server.sqlite3").as_posix())
    schema = None
    if pg:
        schema = "test_" + uuid.uuid4().hex
        with engine.begin() as conn:
            conn.execute(text(f'CREATE SCHEMA "{schema}"'))
        from sqlalchemy import event

        @event.listens_for(engine, "checkout")
        def select_schema(connection, *args):
            old = connection.autocommit
            connection.autocommit = True
            with connection.cursor() as cursor:
                cursor.execute(f'SET search_path TO "{schema}"')
            connection.autocommit = old

    initialize(engine, "admin", "A-test-password-42", demo=True)
    with TestClient(create_app(engine, demo=True)) as client:
        session = client.post("/login", json={"username": "admin", "password": "A-test-password-42"}).json()
        client.headers["Authorization"] = "Bearer " + session["token"]
        yield engine, client, session
    engine.dispose()
    if schema:
        cleanup = engine_for(pg)
        with cleanup.begin() as conn:
            conn.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        cleanup.dispose()


def cmd(action, payload, versions=None):
    from slms.models import now

    return {
        "id": str(uuid.uuid4()),
        "device_id": "test-pc",
        "client_at": now(),
        "action": action,
        "payload": payload,
        "versions": versions or {},
    }


def version(kind, item):
    return {kind + ":" + item["id"]: item["version"]}
