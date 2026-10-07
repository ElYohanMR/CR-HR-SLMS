from PySide6.QtCore import Qt
from slms.window import Window
from slms.local import LocalStore
from slms.forms import Form


def test_enter_search_pulse_refresh_click_and_defaults(qtbot, system, tmp_path, monkeypatch):
    _, client, session = system
    data = client.get("/snapshot").json()
    store = LocalStore(tmp_path / "search.sqlite3")
    store.put("snapshot", data)
    monkeypatch.setattr(Window, "sync", lambda self: None)
    window = Window({"url": "http://localhost"}, session, store)
    qtbot.addWidget(window)
    window.show()
    window.nav.setCurrentRow(1)
    window.map.fit()
    item = window.map.block_items[0]
    assert item.rect().width() == 14 / 5
    color = item.pen().color()
    window.map_search.setText(data["lockers"][0]["number"])
    qtbot.keyClick(window.map_search, Qt.Key.Key_Return)
    assert window.map.highlighted_block == data["blocks"][0]["id"]
    assert window.map.pulse.duration() == 2000
    window.map.pulse.setCurrentTime(1000)
    assert item.halo.opacity() > 0.9
    assert item.pen().color() == color
    window.refresh()
    item = window.map.block_items[0]
    assert window.map.highlighted_block == data["blocks"][0]["id"]
    qtbot.mouseClick(window.map.viewport(), Qt.MouseButton.LeftButton, pos=window.map.mapFromScene(item.pos()))
    assert window.map.highlighted_block is None
    assert not item.halo.isVisible()
    assert window.map.card.isVisible()
    window.map_search.setText(data["blocks"][0]["label"].lower())
    qtbot.keyClick(window.map_search, Qt.Key.Key_Return)
    assert window.map.highlighted_block == data["blocks"][0]["id"]

    def inspect(form):
        assert form.values()["rows"] == 4 and form.values()["columns"] == 3
        assert form.widgets["rows"].isEnabled() and form.widgets["columns"].isEnabled()
        return Form.DialogCode.Rejected

    monkeypatch.setattr(Form, "exec", inspect)
    window.block_form()
    window.close()


def test_search_other_plan_and_ambiguous_code(qtbot, system, tmp_path, monkeypatch):
    _, client, session = system
    data = client.get("/snapshot").json()
    first = data["blocks"][0]
    second = dict(first, id="other-block", plan_id="inside", building_id="building-2")
    data["plans"].append(dict(data["plans"][0], id="inside", name="Interior", background="", polygons=[]))
    data["blocks"].append(second)
    data["lockers"].append(dict(data["lockers"][0], id="other-locker", block_id=second["id"], number="0007"))
    store = LocalStore(tmp_path / "multi.sqlite3")
    store.put("snapshot", data)
    monkeypatch.setattr(Window, "sync", lambda self: None)
    window = Window({"url": "http://localhost"}, session, store)
    qtbot.addWidget(window)
    window.map_search.setText("0007")
    window.search_map()
    assert window.plan_combo.currentData() == "inside"
    assert window.map.highlighted_block == second["id"]

    def choose(form):
        combo = form.widgets["id"]
        assert combo.count() == 2
        combo.setCurrentIndex(combo.findData(first["id"]))
        return Form.DialogCode.Accepted

    monkeypatch.setattr(Form, "exec", choose)
    window.map_search.setText(first["label"])
    window.search_map()
    assert window.map.highlighted_block == first["id"]
    assert window.plan_combo.currentData() == first["plan_id"]
    messages = []
    monkeypatch.setattr("slms.window.info", lambda parent, text: messages.append(text))
    window.map_search.setText("not-found")
    window.search_map()
    assert messages and window.map.highlighted_block is None
    window.close()
