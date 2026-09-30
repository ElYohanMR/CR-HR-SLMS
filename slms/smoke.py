"""Smoke test for the packaged desktop, isolated by SLMS_HOME."""

import json
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFontDatabase
from fastapi.testclient import TestClient
from .api import create_app
from .config import home
from .database import engine_for, initialize
from .local import LocalStore
from .window import Window


def run(app):
    for font in ("segoeui.ttf", "segoeuib.ttf"):
        QFontDatabase.addApplicationFont("C:/Windows/Fonts/" + font)
    engine = engine_for("sqlite:///" + (home() / "smoke.sqlite3").as_posix())
    initialize(engine, "preview", "Preview-only-password-42", demo=True)
    with TestClient(create_app(engine, demo=True)) as client:
        session = client.post("/login", json={"username": "preview", "password": "Preview-only-password-42"}).json()
        client.headers["Authorization"] = "Bearer " + session["token"]
        snapshot = client.get("/snapshot").json()
    store = LocalStore(home() / "preview-client.sqlite3")
    store.put("snapshot", snapshot)
    Window.sync = lambda self: None
    window = Window({"url": "http://127.0.0.1:8765", "mode": "demo"}, session, store)
    window.show()
    window.synced({"state": "online", "snapshot": snapshot, "actor": session["actor"], "changes": []})
    QApplication.processEvents()
    window.grab().save(str(home() / "resumen.png"))
    window.nav.setCurrentRow(1)
    window.map.fit()
    QApplication.processEvents()
    window.grab().save(str(home() / "mapa.png"))
    window.nav.setCurrentRow(3)
    QApplication.processEvents()
    window.grab().save(str(home() / "inventario.png"))
    assert window.inventory.rowCount() == 16
    assert window.employees.rowCount() == 1
    window.close()
    engine.dispose()
    (home() / "self-test.json").write_text(
        json.dumps({"ok": True, "lockers": 16, "screenshots": ["resumen.png", "mapa.png", "inventario.png"]}),
        encoding="utf-8",
    )
