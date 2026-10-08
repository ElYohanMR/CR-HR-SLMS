import copy

import pytest
from PySide6.QtCore import Qt, QPoint, QTimer
from PySide6.QtGui import QContextMenuEvent
from PySide6.QtWidgets import QApplication, QDialog, QGridLayout, QMenu, QPushButton, QTableWidget

from slms.forms import Form
from slms.local import LocalStore
from slms.window import Window


@pytest.fixture
def window(qtbot, system, tmp_path, monkeypatch):
    _, client, session = system
    monkeypatch.setattr(Window, "sync", lambda self: None)
    store = LocalStore(tmp_path / "context.sqlite3")
    store.put("snapshot", client.get("/snapshot").json())
    result = Window({"url": "http://127.0.0.1:8765", "mode": "demo"}, session, store)
    qtbot.addWidget(result)
    result.show()
    return result


def action(menu, title):
    return next(a for a in menu.actions() if a.text() == title)


def test_clicked_record_survives_sort_and_refresh(window, monkeypatch):
    table = window.inventory
    table.sortItems(0, Qt.SortOrder.DescendingOrder)
    table.selectRow(0)
    clicked = table.item(5, 0).data(Qt.ItemDataRole.UserRole)
    seen = []
    monkeypatch.setattr(window, "locker_dialog", seen.append)
    menu = window.table_menu(table, 5, 1)
    assert window.selected(table) == clicked
    table.sortItems(0, Qt.SortOrder.AscendingOrder)
    window.refresh()
    table.selectRow(0)
    action(menu, "Abrir / editar casillero").trigger()
    assert seen == [clicked]
    assert window.selected(table) == clicked
    action(menu, "Copiar fila").trigger()
    assert window.lookup("lockers", clicked)["number"] in QApplication.clipboard().text()


def test_missing_record_does_not_target_another_row(window, monkeypatch):
    seen, warnings = [], []
    monkeypatch.setattr(window, "locker_dialog", seen.append)
    monkeypatch.setattr("slms.contextmenus.info", lambda *args: warnings.append(args[-1]))
    menu = window.table_menu(window.inventory, 0, 0)
    window.locker_search.setText("DEMO-016")
    action(menu, "Abrir / editar casillero").trigger()
    assert not seen and warnings


def test_table_context_event_opens_menu_on_clicked_row(window, monkeypatch, qtbot):
    window.nav.setCurrentRow(3)
    qtbot.wait(20)
    table = window.inventory
    table.selectRow(0)
    clicked = table.item(3, 0).data(Qt.ItemDataRole.UserRole)
    menus = []

    def close_popup():
        menu = QApplication.activePopupWidget()
        if isinstance(menu, QMenu):
            menus.append([a.text() for a in menu.actions()])
            menu.close()

    QTimer.singleShot(0, close_popup)
    point = table.visualItemRect(table.item(3, 1)).center()
    event = QContextMenuEvent(QContextMenuEvent.Reason.Mouse, point, table.viewport().mapToGlobal(point))
    QApplication.sendEvent(table.viewport(), event)
    assert window.selected(table) == clicked
    assert len(menus) == 1 and "Eliminar casillero" in menus[0]


def test_all_tables_have_context_actions_and_viewer_permissions(window):
    for table in window.findChildren(QTableWidget):
        assert table.contextMenuPolicy() == Qt.ContextMenuPolicy.CustomContextMenu
        if table.rowCount():
            assert action(window.table_menu(table, 0, 0), "Copiar valor").isEnabled()
    window.session["actor"]["role"] = "viewer"
    menu = window.table_menu(window.inventory, 0, 0)
    for title in ("Editar bloque", "Eliminar casillero", "Eliminar bloque completo", "Asignar casillero"):
        assert not action(menu, title).isEnabled()
    assert action(menu, "Ver casilleros del bloque").isEnabled()
    block = window.data["blocks"][0]
    assert not action(window.map_menu(block["id"], [20, 30]), "Eliminar bloque").isEnabled()
    assert not action(window.map_menu("", [20, 30]), "Nuevo bloque aquí").isEnabled()


def test_context_specific_employee_queue_admin_actions(window, monkeypatch):
    called = []
    monkeypatch.setattr(
        window, "employee_form", lambda edit=False: called.append((edit, window.selected(window.employees)))
    )
    employee = window.data["employees"][0]
    action(window.table_menu(window.employees, 0, 0), "Editar empleado").trigger()
    assert called == [(True, employee["id"])]
    task = window.store.enqueue(window.session["actor"]["id"], "block.delete", {"id": "test"}, {})
    window.refresh_queue()
    assert not action(window.table_menu(window.queue_table, 0, 0), "Reintentar solicitud").isEnabled()
    window.store.result(task, "error_temporal", "Sin conexión", attempt=True)
    window.refresh_queue()
    assert action(window.table_menu(window.queue_table, 0, 0), "Reintentar solicitud").isEnabled()
    assert action(window.table_menu(window.admin_table, 0, 0), "Editar cuenta / permisos").isEnabled()


def test_map_context_hit_testing_at_zoom_and_pan(window, qtbot):
    view = window.map
    window.nav.setCurrentRow(1)
    view.fit()
    view.scale(2, 2)
    block = view.block_items[0]
    view.centerOn(block)
    qtbot.wait(20)
    seen = []
    view.contextRequested.disconnect(window.show_map_menu)
    view.contextRequested.connect(lambda *args: seen.append(args))

    def right_click(point):
        event = QContextMenuEvent(QContextMenuEvent.Reason.Mouse, point, view.viewport().mapToGlobal(point))
        QApplication.sendEvent(view.viewport(), event)

    right_click(view.mapFromScene(block.pos()))
    assert seen[-1][0] == block.data["id"]
    empty = view.mapFromScene(block.pos()) + QPoint(90, 35)
    expected = view.from_scene(view.mapToScene(empty))
    right_click(empty)
    assert seen[-1][0] == ""
    assert seen[-1][1] == expected
    assert not view.dirty


def test_new_block_here_uses_captured_position_and_plan(window, monkeypatch):
    captured = []
    position = [123.45, 678.9]
    plan_id = window.map.plan["id"]
    monkeypatch.setattr(window, "submit", lambda *args: captured.append(args))

    def accept(form):
        assert form.values()["x"] == position[0]
        assert form.values()["y"] == position[1]
        assert form.values()["plan_id"] == plan_id
        form.widgets["start"].setText("1105")
        return QDialog.DialogCode.Accepted

    monkeypatch.setattr(Form, "exec", accept)
    action(window.map_menu("", position), "Nuevo bloque aquí").trigger()
    assert captured[0][0] == "block.create"
    payload = captured[0][1]
    assert (payload["rows"], payload["columns"]) == (4, 3)
    assert payload["numbers"] == [str(i) for i in range(1105, 1117)]
    assert (payload["x"], payload["y"], payload["plan_id"]) == (*position, plan_id)


def test_map_block_edit_and_delete_use_clicked_block(window, monkeypatch):
    block = window.data["blocks"][0]
    calls = []
    monkeypatch.setattr(window, "block_form", lambda value: calls.append(("edit", value["id"])))
    monkeypatch.setattr(window, "delete_inventory", lambda kind, value: calls.append((kind, value["id"])))
    menu = window.map_menu(block["id"], [10, 20])
    action(menu, "Editar bloque").trigger()
    action(menu, "Eliminar bloque").trigger()
    assert calls == [("edit", block["id"]), ("block", block["id"])]


@pytest.mark.parametrize("columns", [3, 4])
def test_block_grid_right_to_left_preserves_record_identity(window, monkeypatch, columns):
    block = window.data["blocks"][0]
    block["columns"] = columns
    window.data["lockers"] = window.data["lockers"][: columns * 4]
    for index, locker in enumerate(window.data["lockers"]):
        locker["row"], locker["column"] = divmod(index, columns)
    original = copy.deepcopy(window.data)
    seen = []

    def inspect(dialog):
        grid = dialog.findChild(QGridLayout)
        lockers = [x for x in window.data["lockers"] if x["block_id"] == block["id"]]
        for locker in lockers:
            button = grid.itemAtPosition(locker["row"], block["columns"] - 1 - locker["column"]).widget()
            assert isinstance(button, QPushButton)
            assert button.text().split("\n")[0] == locker["number"]
        grid.itemAtPosition(0, block["columns"] - 1).widget().click()
        return QDialog.DialogCode.Rejected

    monkeypatch.setattr(QDialog, "exec", inspect)
    monkeypatch.setattr(window, "locker_dialog", seen.append)
    window.open_block(block["id"])
    assert seen == [next(x["id"] for x in window.data["lockers"] if x["row"] == x["column"] == 0)]
    assert window.data == original
