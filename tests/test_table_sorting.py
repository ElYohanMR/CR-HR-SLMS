import pytest
from PySide6.QtCore import QPoint, Qt
from PySide6.QtWidgets import QTableWidget, QVBoxLayout, QWidget

from slms.local import LocalStore
from slms.window import Window


@pytest.fixture
def table(qtbot):
    host = QWidget()
    qtbot.addWidget(host)
    table = Window.table(None, QVBoxLayout(host), ["ID empleado", "Nombre", "Fecha / hora"])
    host.resize(750, 400)
    host.show()
    yield table


def texts(table, column=0):
    return [table.item(row, column).text() for row in range(table.rowCount())]


def test_header_clicks_toggle_and_keep_whole_records(table, qtbot):
    rows = [("ten", ["10", "Diez", "02/01/2026 09:00:00"]),
            ("two", ["002", "Dos", "31/12/2025 23:00:00"]),
            ("one", ["1", "Uno", "01/02/2026 08:00:00"])]
    Window.fill(None, table, rows)
    assert texts(table) == ["10", "002", "1"]
    table.selectRow(0)
    header = table.horizontalHeader()
    point = QPoint(header.sectionViewportPosition(0) + 35, header.height() // 2)
    qtbot.mouseClick(header.viewport(), Qt.MouseButton.LeftButton, pos=point)
    assert header.sortIndicatorOrder() == Qt.SortOrder.AscendingOrder
    assert header.isSortIndicatorShown()
    assert texts(table) == ["1", "002", "10"]
    assert Window.selected(None, table) == "ten"
    qtbot.mouseClick(header.viewport(), Qt.MouseButton.LeftButton, pos=point)
    assert header.sortIndicatorOrder() == Qt.SortOrder.DescendingOrder
    assert texts(table) == ["10", "002", "1"]
    # A refresh inserts a record ahead of the selected one and reorders source rows.
    Window.fill(None, table, rows[::-1] + [("twenty", ["20", "Veinte", "01/01/2027 00:00:00"])])
    assert texts(table) == ["20", "10", "002", "1"]
    assert texts(table, 1) == ["Veinte", "Diez", "Dos", "Uno"]
    assert Window.selected(None, table) == "ten"
    for row in range(table.rowCount()):
        assert len({table.item(row, col).data(Qt.ItemDataRole.UserRole) for col in range(3)}) == 1
    # Filtering out the selected record must not select a different employee.
    Window.fill(None, table, [rows[1]])
    assert Window.selected(None, table) is None
    assert not table.selectedItems()


@pytest.mark.parametrize("header,values,expected", [
    ("ID", ["100000000000000000001", "10", "2", "0001", "100000000000000000000"],
     ["0001", "2", "10", "100000000000000000000", "100000000000000000001"]),
    ("Ubicación", ["E1-N10-100", "E1-N2-12", "E1-N2-2"], ["E1-N2-2", "E1-N2-12", "E1-N10-100"]),
    ("Fila / columna", ["10 / 1", "2 / 10", "2 / 2"], ["2 / 2", "2 / 10", "10 / 1"]),
    ("X", ["10.2", "-2", "0", "2.3", "2.12"], ["-2", "0", "2.12", "2.3", "10.2"]),
    ("Nombre", ["Zoe", "ñora", "Álvaro", "ana", "nora"], ["Álvaro", "ana", "nora", "ñora", "Zoe"]),
    ("Fecha / hora", ["01/02/2026 09:00:00", "31/12/2025 23:00:00", "02/01/2026 08:00:00", "—"],
     ["—", "31/12/2025 23:00:00", "02/01/2026 08:00:00", "01/02/2026 09:00:00"]),
])
def test_meaningful_order(table, header, values, expected):
    table.horizontalHeaderItem(0).setText(header)
    Window.fill(None, table, [(str(i), [value, "", ""]) for i, value in enumerate(values)])
    table.sortItems(0, Qt.SortOrder.AscendingOrder)
    assert texts(table) == expected
    table.sortItems(0, Qt.SortOrder.DescendingOrder)
    assert texts(table) == expected[::-1]


def test_all_main_tables_sort_and_refresh_preserves_order(qtbot, system, tmp_path, monkeypatch):
    _, client, session = system
    monkeypatch.setattr(Window, "sync", lambda self: None)
    store = LocalStore(tmp_path / "sorting.sqlite3")
    store.put("snapshot", client.get("/snapshot").json())
    window = Window({"url": "http://127.0.0.1:8765", "mode": "demo"}, session, store)
    qtbot.addWidget(window)
    tables = window.findChildren(QTableWidget)
    assert len(tables) == 6
    for table in tables:
        assert table.isSortingEnabled()
        assert table.horizontalHeader().sectionsClickable()
    window.inventory.sortItems(0, Qt.SortOrder.DescendingOrder)
    original = texts(window.inventory)
    window.inventory.selectRow(3)
    selected = window.selected(window.inventory)
    window.refresh()
    assert texts(window.inventory) == original
    assert window.selected(window.inventory) == selected
    assert window.lookup("lockers", selected)["number"] == window.inventory.item(window.inventory.currentRow(), 0).text()
