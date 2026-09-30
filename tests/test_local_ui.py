from slms.local import LocalStore
from slms.window import Window, csv_safe
from slms.config import save_private, read_private


def test_queue_persists_encrypted_and_separates_actors(tmp_path):
    path = tmp_path / "queue.sqlite3"
    store = LocalStore(path)
    id = store.enqueue("actor-one", "employee.create", {"first_name": "SensitiveEmployeeName"}, {})
    reopened = LocalStore(path)
    assert reopened.queue("actor-one")[0]["id"] == id
    assert reopened.queue("actor-two") == []
    with reopened.connect() as db:
        content = db.execute("SELECT command FROM queue").fetchone()[0]
        assert b"SensitiveEmployeeName" not in content
    reopened.result(id, "error_temporal", "Retry", attempt=True)
    reopened.retry(id, "actor-two")
    assert reopened.queue("actor-one")[0]["status"] == "error_temporal"
    reopened.retry(id, "actor-one")
    assert reopened.queue("actor-one")[0]["status"] == "pendiente"


def test_private_configuration_and_csv(system):
    save_private("test-config.dat", {"password": "NeverPlaintext"})
    assert read_private("test-config.dat")["password"] == "NeverPlaintext"
    from slms.config import home

    assert b"NeverPlaintext" not in (home() / "test-config.dat").read_bytes()
    assert csv_safe("=SUM(A1:A2)").startswith("'")
    assert csv_safe("1234") == "1234"


def test_window_map_and_inventory(qtbot, system, tmp_path, monkeypatch):
    from PySide6.QtGui import QFontDatabase

    QFontDatabase.addApplicationFont("C:/Windows/Fonts/segoeui.ttf")
    QFontDatabase.addApplicationFont("C:/Windows/Fonts/segoeuib.ttf")
    _, client, session = system
    monkeypatch.setattr(Window, "sync", lambda self: None)
    store = LocalStore(tmp_path / "ui.sqlite3")
    store.put("snapshot", client.get("/snapshot").json())
    window = Window({"url": "http://127.0.0.1:8765", "mode": "demo"}, session, store)
    qtbot.addWidget(window)
    window.show()
    qtbot.wait(100)
    assert window.inventory.rowCount() == 16
    assert window.employees.rowCount() == 1
    assert len(window.map.block_items) == 1
    window.edit_map.setChecked(True)
    window.toggle_map()
    block = window.map.block_items[0]
    block.setPos(222, 333)
    assert window.map.dirty["demo-block"] == (222, 333)
    window.employee_search.setText("does not exist")
    assert window.employees.rowCount() == 0
    window.inventory_filter.setCurrentIndex(3)
    assert window.inventory.rowCount() == 0
    window.nav.setCurrentRow(1)
    window.map.fit()
    qtbot.wait(50)
    window.grab().save(str(tmp_path / "map.png"))
    window.close()
