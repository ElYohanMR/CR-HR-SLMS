from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QTableWidget
from slms.mapview import MapView, block_status
from slms.window import Window
from slms.local import LocalStore


def test_map_colors():
    lockers = [{"id": str(i), "condition": "utilizable"} for i in range(12)]
    assert block_status(lockers, set())[2] == "#187842"
    assert block_status(lockers, {str(i) for i in range(12)})[2] == "#c42b32"
    lockers[-1]["condition"] = "pendiente"
    assert block_status(lockers, {str(i) for i in range(11)})[2] == "#946200"


def test_forty_blocks_aspect_drag_and_single_click(qtbot, system):
    _, client, _ = system
    data = client.get("/snapshot").json()
    model = data["blocks"][0]
    data["blocks"] = [dict(model, id=f"dense-{i}", label=f"E{i:02}", x=700, y=300 + i * 10) for i in range(40)]
    view = MapView()
    qtbot.addWidget(view)
    view.resize(1100, 700)
    view.show()
    view.render(data, "campus")
    view.fit()
    assert abs(view.map_height - 1000 * 2478 / 3956) < 0.01
    assert len(view.block_items) == 40
    for a, b in zip(view.block_items, view.block_items[1:]):
        assert not a.sceneBoundingRect().intersects(b.sceneBoundingRect())
    block = view.block_items[5]
    qtbot.mouseClick(view.viewport(), Qt.MouseButton.LeftButton, pos=view.mapFromScene(block.pos()))
    assert view.selected_block == block.data["id"]
    assert view.card.isVisible()
    assert "0/0 disponibles" in view.card_status.text()
    with qtbot.waitSignal(view.assignmentsOpened) as signal:
        qtbot.mouseClick(view.assignments_button, Qt.MouseButton.LeftButton)
    assert signal.args == [block.data["id"]]
    view.set_editing(True)
    assert not view.card.isVisible()
    block.setPos(view.to_scene([800, 900]))
    assert view.dirty[block.data["id"]] == (800, 900)
    vertex = view.vertices[0]
    vertex.setPos(view.to_scene([350, 200]))
    assert view.shapes[0]["points"][0] == [350, 200]


def test_assignment_list_shows_only_current_block(qtbot, system, tmp_path, monkeypatch):
    _, client, session = system
    data = client.get("/snapshot").json()
    employee = data["employees"][0]
    employee.update(employee_number="007", first_name="Ana", surname="Mora", second_surname="Solís")
    data["assignments"] = [
        dict(id="current", employee_id=employee["id"], locker_id=data["lockers"][0]["id"], ended_at=None),
        dict(id="old", employee_id=employee["id"], locker_id=data["lockers"][1]["id"], ended_at="2026-01-01"),
    ]
    store = LocalStore(tmp_path / "consult.sqlite3")
    store.put("snapshot", data)
    monkeypatch.setattr(Window, "sync", lambda self: None)
    window = Window({"url": "http://localhost"}, session, store)
    qtbot.addWidget(window)

    def inspect(dialog):
        table = dialog.findChild(QTableWidget)
        assert table.rowCount() == 1
        assert [table.item(0, c).text() for c in range(1, 5)] == ["007", "Ana", "Mora", "Solís"]
        return QDialog.DialogCode.Rejected

    monkeypatch.setattr(QDialog, "exec", inspect)
    window.block_assignments(data["blocks"][0]["id"])
    window.close()
