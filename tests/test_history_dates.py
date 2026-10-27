import csv

import httpx
from PySide6.QtCore import QDate
from sqlalchemy.orm import Session

from slms.local import LocalStore
from slms.models import Audit
from slms.window import Window


def insert_events(engine, actor_id, entries):
    with Session(engine) as db:
        db.add_all([Audit(id=id, command_id=id, actor_id=actor_id, at=at,
                         action="locker.update", target_id="test-locker", before={},
                         after={"number": "1154"}, reason="Prueba") for id, at in entries])
        db.commit()


def test_dates_include_complete_costa_rica_days_and_validate(system):
    engine, client, session = system
    insert_events(engine, session["actor"]["id"], [
        ("before", "2026-10-24T05:59:59.999999+00:00"),
        ("start", "2026-10-24T06:00:00+00:00"),
        ("end", "2026-10-26T05:59:59.999999+00:00"),
        ("after", "2026-10-26T06:00:00+00:00"),
    ])
    params = {"date_from": "2026-10-24", "date_to": "2026-10-25"}
    assert [e["id"] for e in client.get("/audit", params=params).json()] == ["end", "start"]
    assert client.get("/audit", params=params | {"date_from": "2026-10-27"}).status_code == 400
    assert client.get("/audit", params={"date_from": "2026-10-24"}).status_code == 400
    assert client.get("/audit", params=params | {"date_from": "invalid"}).status_code == 422
    assert client.get("/audit", params={"before_id": "start"}).status_code == 400
    client.headers.pop("Authorization")
    assert client.get("/audit", params=params).status_code == 401


def test_cursor_handles_ties_and_new_events_between_pages(system):
    engine, client, session = system
    at = "2026-10-24T12:00:00+00:00"
    expected = [f"entry-{i:04}" for i in range(1002)]
    insert_events(engine, session["actor"]["id"], [(id, at) for id in expected])
    params = {"date_from": "2026-10-24", "date_to": "2026-10-24"}
    first = client.get("/audit", params=params).json()
    assert len(first) == 1000
    insert_events(engine, session["actor"]["id"], [("new", "2026-10-24T13:00:00+00:00")])
    second = client.get("/audit", params=params | {"before_at": first[-1]["at"], "before_id": first[-1]["id"]}).json()
    assert [x["id"] for x in first + second] == expected


def test_period_survives_sync_and_drives_detail_and_export(qtbot, system, tmp_path, monkeypatch):
    engine, backend, session = system
    insert_events(engine, session["actor"]["id"], [
        ("old", "2020-01-01T12:00:00+00:00"), ("new", "2026-10-25T12:00:00+00:00")])
    data = backend.get("/snapshot").json()
    data["audit"] = [x for x in data["audit"] if x["id"] == "new"]
    store = LocalStore(tmp_path / "history.sqlite3")
    store.put("snapshot", data)
    monkeypatch.setattr(Window, "sync", lambda self: None)
    w = Window({"url": "http://test"}, session, store)
    qtbot.addWidget(w)
    messages = []
    monkeypatch.setattr("slms.window.info", lambda parent, message: messages.append(message))
    monkeypatch.setattr("slms.window.httpx.get", lambda url, **kw: backend.get("/audit", params=kw["params"]))
    w.audit_from.setDate(QDate(2020, 1, 1))
    w.audit_to.setDate(QDate(2020, 1, 1))
    w.load_history_range()
    assert [x["id"] for x in w.history_events()] == ["old"]
    assert w.audit_table.rowCount() == 1
    assert not w.history_more.isEnabled()
    w.synced({"state": "online", "snapshot": data, "actor": session["actor"], "changes": []})
    assert [x["id"] for x in w.history_events()] == ["old"]
    seen = []
    monkeypatch.setattr("slms.audit_ui.show_audit_detail", lambda parent, event, title: seen.append(event["id"]))
    w.show_audit("old")
    w.show_audit("new")  # The summary retains its recent event while the history is filtered.
    assert seen == ["old", "new"]
    filename = tmp_path / "period.csv"
    monkeypatch.setattr("slms.window.QFileDialog.getSaveFileName", lambda *a: (str(filename), "CSV"))
    w.export("audit")
    with filename.open(encoding="utf-8-sig", newline="") as file:
        assert [row["id"] for row in csv.DictReader(file)] == ["old"]
    w.audit_from.setDate(QDate(2020, 1, 2))
    w.load_history_range()
    assert "Desde" in messages[-1]
    assert [x["id"] for x in w.history_events()] == ["old"]
    w.audit_from.setDate(QDate(2010, 1, 1))
    w.audit_to.setDate(QDate(2010, 1, 1))
    def offline(*a, **kw):
        raise httpx.ConnectError("offline")
    monkeypatch.setattr("slms.window.httpx.get", offline)
    w.load_history_range()
    assert [x["id"] for x in w.history_events()] == ["old"]
    w.reset_history_range()
    assert [x["id"] for x in w.history_events()] == ["new"]
    w.close()
