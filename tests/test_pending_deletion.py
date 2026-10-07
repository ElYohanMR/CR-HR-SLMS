import json
import httpx
from slms.local import LocalStore
from slms.sync import SyncWorker
from slms.setup import saved_session_valid
from slms.window import Window
from conftest import cmd, version


def test_expired_deletion_then_login_confirms_original_requests(system, tmp_path, monkeypatch):
    _, backend, session = system
    data = backend.get("/snapshot").json()
    block = data["blocks"][0]
    versions = version("block", block)
    for locker in data["lockers"]:
        versions.update(version("locker", locker))
    store = LocalStore(tmp_path / "delete.sqlite3")
    payload = {"id": block["id"], "reason": "Eliminar bloque de prueba"}
    first = store.enqueue(session["actor"]["id"], "block.delete", payload, versions)
    assert store.enqueue(session["actor"]["id"], "block.delete", payload, versions) == first
    expired = True
    posts = []
    original = httpx.Client

    def transport(request):
        if expired:
            return httpx.Response(401, json={"detail": "Expired"})
        if request.url.path == "/commands":
            command = json.loads(request.content)
            posts.append(command["id"])
            result = backend.post("/commands", json=command)
        else:
            result = backend.get(request.url.path)
        return httpx.Response(result.status_code, json=result.json())

    monkeypatch.setattr(
        "slms.sync.httpx.Client", lambda **kwargs: original(transport=httpx.MockTransport(transport), **kwargs)
    )
    SyncWorker(store, "http://test", session).run()
    task = store.queue(session["actor"]["id"])[0]
    assert task["status"] == "requiere_sesion" and task["attempts"] == 0 and not posts
    assert store.enqueue(session["actor"]["id"], "block.delete", payload, versions) == first
    expired = False
    SyncWorker(store, "http://test", session).run()
    assert posts == [first]
    assert store.queue(session["actor"]["id"])[0]["status"] == "confirmada"
    assert store.get("snapshot")["blocks"] == []
    history_count = len(store.get("snapshot")["audit"])
    # Old clients may have saved a second request before duplicate suppression.
    result = backend.post("/commands", json=cmd("block.delete", payload, versions)).json()
    assert result["status"] == "confirmada"
    assert len(backend.get("/snapshot").json()["audit"]) == history_count
    archived = backend.get("/snapshot").json()
    b = archived["archived_blocks"][0]
    restore_versions = version("block", b)
    for locker in archived["archived_lockers"]:
        restore_versions.update(version("locker", locker))
    assert (
        backend.post("/commands", json=cmd("block.restore", payload, restore_versions)).json()["status"] == "confirmada"
    )
    # A delayed old deletion cannot remove a restored block.
    assert backend.post("/commands", json=cmd("block.delete", payload, versions)).json()["status"] == "conflicto"


def test_saved_session_validation(monkeypatch):
    config = {"url": "http://test", "installation": "one"}
    session = {"token": "private", "installation": "one"}
    monkeypatch.setattr("slms.setup.httpx.get", lambda *args, **kw: httpx.Response(401))
    assert not saved_session_valid(config, session)
    monkeypatch.setattr("slms.setup.httpx.get", lambda *args, **kw: httpx.Response(200))
    assert saved_session_valid(config, session)
    assert not saved_session_valid(config, dict(session, installation="other"))

    def offline(*args, **kw):
        raise httpx.ConnectError("Offline")

    monkeypatch.setattr("slms.setup.httpx.get", offline)
    assert saved_session_valid(config, session)


def test_options_and_visible_session_recovery(qtbot, system, tmp_path, monkeypatch):
    _, backend, session = system
    store = LocalStore(tmp_path / "ui.sqlite3")
    store.put("snapshot", backend.get("/snapshot").json())
    monkeypatch.setattr(Window, "sync", lambda self: None)
    window = Window({"url": "http://test"}, session, store)
    qtbot.addWidget(window)
    window.show()
    window.populate_options()
    assert {"Mapa", "Inventario", "Empleados", "Conexión y solicitudes"}.issubset(
        {a.text() for a in window.options_menu.actions()}
    )
    window.synced({"state": "sesion", "message": "Inicia sesión"})
    assert window.session_button.isVisible()
    window.session["actor"]["role"] = "viewer"
    window.populate_options()
    inventory = next(a.menu() for a in window.options_menu.actions() if a.text() == "Inventario")
    assert not next(a for a in inventory.actions() if a.text() == "Eliminar bloque…").isEnabled()
    assert next(a for a in inventory.actions() if a.text() == "Exportar bloques y ubicaciones").isEnabled()
    window.close()
