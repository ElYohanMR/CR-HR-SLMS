import json
import httpx
from sqlalchemy import select, func
from sqlalchemy.orm import sessionmaker
from slms.local import LocalStore
from slms.sync import SyncWorker
from slms.models import Assignment
from conftest import version


def test_connection_lost_after_commit_replays_once(system, tmp_path, monkeypatch):
    engine, backend, session = system
    data = backend.get("/snapshot").json()
    employee = data["employees"][0]
    locker = data["lockers"][0]
    store = LocalStore(tmp_path / "lost-response.sqlite3")
    id = store.enqueue(
        session["actor"]["id"],
        "assignment.assign",
        {"employee_id": employee["id"], "locker_id": locker["id"], "reason": "Entrega"},
        version("employee", employee) | version("locker", locker),
    )
    calls = []

    def transport(request):
        if request.url.path == "/commands":
            command = json.loads(request.content)
            calls.append(command["id"])
            response = backend.post("/commands", json=command)
            if len(calls) == 1:
                raise httpx.ReadTimeout("Response lost", request=request)
        else:
            response = backend.get(request.url.path)
        return httpx.Response(response.status_code, json=response.json())

    original = httpx.Client
    monkeypatch.setattr(
        "slms.sync.httpx.Client", lambda **kwargs: original(transport=httpx.MockTransport(transport), **kwargs)
    )
    worker = SyncWorker(store, "http://test", session)
    worker.run()
    assert store.queue(session["actor"]["id"])[0]["status"] == "pendiente"
    store = LocalStore(tmp_path / "lost-response.sqlite3")
    store.retry(id, session["actor"]["id"])
    SyncWorker(store, "http://test", session).run()
    assert calls == [id, id]
    assert store.queue(session["actor"]["id"])[0]["status"] == "confirmada"
    with sessionmaker(engine)() as db:
        assert db.scalar(select(func.count()).select_from(Assignment)) == 1


def test_expired_session_marks_login_required_and_separates_installations(system, tmp_path, monkeypatch):
    _, _, session = system
    store = LocalStore(tmp_path / "expired.sqlite3")
    store.enqueue(session["actor"]["id"], "employee.create", {"first_name": "Not sent"}, {})
    original = httpx.Client
    calls = []

    def transport(request):
        calls.append(request.url.path)
        return httpx.Response(401, json={"detail": "Expired"})

    monkeypatch.setattr(
        "slms.sync.httpx.Client", lambda **kwargs: original(transport=httpx.MockTransport(transport), **kwargs)
    )
    SyncWorker(store, "http://test", session).run()
    assert calls == ["/me"]
    assert store.queue(session["actor"]["id"])[0]["status"] == "requiere_sesion"
    first = LocalStore(installation="server-one")
    second = LocalStore(installation="server-two")
    first.enqueue("actor", "employee.create", {}, {})
    assert second.queue("actor") == []


def test_failed_dependency_not_sent(system, tmp_path, monkeypatch):
    _, backend, session = system
    store = LocalStore(tmp_path / "dependent.sqlite3")
    first = store.enqueue(session["actor"]["id"], "employee.create", {}, {})
    store.result(first, "rechazada", "Invalid")
    store.enqueue(session["actor"]["id"], "assignment.assign", {}, {}, dependency=first)
    original = httpx.Client
    calls = []

    def transport(request):
        calls.append(request.url.path)
        response = backend.get(request.url.path)
        return httpx.Response(response.status_code, json=response.json())

    monkeypatch.setattr(
        "slms.sync.httpx.Client", lambda **kwargs: original(transport=httpx.MockTransport(transport), **kwargs)
    )
    SyncWorker(store, "http://test", session).run()
    assert "/commands" not in calls
