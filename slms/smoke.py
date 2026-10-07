"""Smoke test for the packaged desktop, isolated by SLMS_HOME."""

import json
import uuid
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFontDatabase
from fastapi.testclient import TestClient
from .api import create_app
from .config import home
from .database import engine_for, initialize
from .local import LocalStore
from .window import Window
from .models import now


def run(app):
    for font in ("segoeui.ttf", "segoeuib.ttf"):
        QFontDatabase.addApplicationFont("C:/Windows/Fonts/" + font)
    # Reproduce a dark OS palette before applying the app's explicit light theme.
    from PySide6.QtGui import QColor, QPalette
    from .theme import apply_theme
    from .setup import setup_form
    from .forms import Form

    dark = QPalette()
    dark.setColor(QPalette.ColorRole.WindowText, QColor("white"))
    dark.setColor(QPalette.ColorRole.Text, QColor("white"))
    dark.setColor(QPalette.ColorRole.Window, QColor("#222222"))
    app.setPalette(dark)
    apply_theme(app)
    wizard = setup_form()
    wizard.setMaximumHeight(1000)
    wizard.resize(740, wizard.sizeHint().height())
    wizard.show()
    QApplication.processEvents()
    wizard.grab().save(str(home() / "configuracion.png"))
    wizard.close()
    signin = Form(
        "Iniciar sesión",
        [("username", "Usuario", "line"), ("password", "Contraseña", "password")],
        description="Utiliza tu cuenta individual de Samtec Lockers.",
        accept_label="Entrar",
    )
    signin.show()
    QApplication.processEvents()
    signin.grab().save(str(home() / "acceso.png"))
    signin.close()
    engine = engine_for("sqlite:///" + (home() / "smoke.sqlite3").as_posix())
    initialize(engine, "preview", "Preview-only-password-42", demo=True)
    with TestClient(create_app(engine, demo=True)) as client:
        session = client.post("/login", json={"username": "preview", "password": "Preview-only-password-42"}).json()
        client.headers["Authorization"] = "Bearer " + session["token"]
        snapshot = client.get("/snapshot").json()
        if not any(a["ended_at"] is None for a in snapshot["assignments"]):
            employee, locker = snapshot["employees"][0], snapshot["lockers"][0]
            result = client.post(
                "/commands",
                json={
                    "id": str(uuid.uuid4()),
                    "device_id": "preview",
                    "client_at": now(),
                    "action": "assignment.assign",
                    "payload": {"employee_id": employee["id"], "locker_id": locker["id"], "reason": "Ejemplo ficticio"},
                    "versions": {
                        "employee:" + employee["id"]: employee["version"],
                        "locker:" + locker["id"]: locker["version"],
                    },
                },
            )
            assert result.json()["status"] == "confirmada"
            snapshot = client.get("/snapshot").json()
        from .inventory_io import export_rows, write_inventory, read_inventory, prepare_import

        exported = home() / "inventory-roundtrip.xlsx"
        write_inventory(exported, export_rows(snapshot))
        imported = read_inventory(exported)
        assert prepare_import(imported, snapshot) == ([], {})
        for row in imported:
            row["x"] = str(float(row["x"]) + 1)
        operations, versions = prepare_import(imported, snapshot)
        request = {
            "id": str(uuid.uuid4()),
            "device_id": "preview",
            "client_at": now(),
            "action": "inventory.import",
            "payload": {"operations": operations},
            "versions": versions,
        }
        result = client.post("/commands", json=request).json()
        assert result["status"] == "confirmada"
        assert client.post("/commands", json=request).json() == result
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
    window.map.show_card(snapshot["blocks"][0]["id"])
    QApplication.processEvents()
    window.grab().save(str(home() / "mapa-consulta.png"))
    window.map.hide_card()
    window.map_search.setText(snapshot["lockers"][0]["number"])
    window.search_map()
    window.map.pulse.setCurrentTime(1000)
    QApplication.processEvents()
    window.grab().save(str(home() / "mapa-busqueda.png"))
    window.map.stop_highlight()
    window.nav.setCurrentRow(3)
    QApplication.processEvents()
    window.grab().save(str(home() / "inventario.png"))
    assert window.inventory.rowCount() == 16
    assert window.employees.rowCount() == 1
    window.nav.setCurrentRow(2)
    window.employees.selectRow(0)
    QApplication.processEvents()
    window.grab().save(str(home() / "empleados.png"))
    original_exec = Form.exec

    def capture(form):
        names = {
            "Dar de baja y liberar": "baja",
            "Liberar casillero": "devolucion",
            "Avisos a Recursos Humanos": "avisos-hr",
        }
        form.setMaximumHeight(1000)
        form.resize(max(740, form.sizeHint().width()), form.sizeHint().height())
        form.show()
        QApplication.processEvents()
        form.grab().save(str(home() / (names[form.windowTitle()] + ".png")))
        form.close()
        return Form.DialogCode.Rejected

    try:
        Form.exec = capture
        window.deactivate_employee()
        window.employee_release()
        window.mail_settings_form()
    finally:
        Form.exec = original_exec
    window.populate_options()
    window.options_menu.show()
    QApplication.processEvents()
    window.options_menu.grab().save(str(home() / "opciones.png"))
    window.options_menu.hide()
    window.synced(
        {"state": "sesion", "message": "Sesión vencida. Inicia sesión para enviar las solicitudes guardadas."}
    )
    QApplication.processEvents()
    window.grab().save(str(home() / "sesion-vencida.png"))
    window.close()
    engine.dispose()
    (home() / "self-test.json").write_text(
        json.dumps(
            {
                "ok": True,
                "lockers": 16,
                "screenshots": [
                    "configuracion.png",
                    "acceso.png",
                    "resumen.png",
                    "mapa.png",
                    "inventario.png",
                    "empleados.png",
                    "baja.png",
                    "devolucion.png",
                    "avisos-hr.png",
                ],
            }
        ),
        encoding="utf-8",
    )
