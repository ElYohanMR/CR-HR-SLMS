import copy

import pytest
from PySide6.QtCore import QPointF
from PySide6.QtWidgets import QDialog, QDialogButtonBox, QPushButton, QApplication

from slms.forms import Form
from slms.local import LocalStore
from slms.preferences import normalize_preferences, DEFAULTS
from slms.settings_dialog import SettingsDialog
from slms.window import Window
from slms.numbering import DIRECTIONS, HORIZONTAL, VERTICAL
from test_numbering import LAYOUTS


@pytest.fixture
def window(qtbot, system, tmp_path, monkeypatch):
    _, client, session = system
    monkeypatch.setattr(Window, "sync", lambda self: None)
    store = LocalStore(tmp_path / "settings.sqlite3")
    store.put("snapshot", client.get("/snapshot").json())
    result = Window({"url": "http://127.0.0.1:8765", "mode": "demo"}, session, store)
    qtbot.addWidget(result)
    result.show()
    return result


def test_bad_saved_preferences_fall_back_without_sharing_defaults():
    prefs = normalize_preferences(
        {
            "ui_scale": 999,
            "satellite": "false",
            "block": {"rotation": float("nan"), "rows": 0, "side": "unknown", "count": 900},
            "employee": [],
        }
    )
    assert prefs == DEFAULTS
    prefs["block"]["rotation"] = 12
    assert DEFAULTS["block"]["rotation"] == 10


def test_sync_interval_applies_cancels_and_is_per_account(window, qtbot):
    assert window.timer.interval() == 10000
    d = SettingsDialog(window.preferences, window.data["buildings"], window.save_preferences, window)
    qtbot.addWidget(d)
    d.widgets["sync_seconds"].setValue(45)
    d.apply_button.click()
    assert window.timer.interval() == 45000 and window.timer.isActive()
    d.widgets["sync_seconds"].setValue(60)
    d.reject()
    window.load_preferences()
    assert window.preferences["sync_seconds"] == 45
    assert window.timer.interval() == 45000
    window.session["actor"]["id"] = "another-account"
    window.load_preferences()
    window.apply_preferences()
    assert window.preferences["sync_seconds"] == 10 and window.timer.interval() == 10000
    for invalid in (0, -1, 4, 301, True, "30", None):
        assert normalize_preferences({"sync_seconds": invalid})["sync_seconds"] == 10


def test_apply_cancel_restore_and_per_account_persistence(window, qtbot):
    def dialog():
        result = SettingsDialog(window.preferences, window.data["buildings"], window.save_preferences, window)
        qtbot.addWidget(result)
        return result

    d = dialog()
    assert not d.apply_button.isEnabled()
    d.widgets["block.rotation"].setValue(12)
    d.reject()
    assert window.preferences["block"]["rotation"] == 10
    d = dialog()
    d.widgets["block.rotation"].setValue(11)
    d.widgets["employee.shift"].setText("T3")
    d.apply_button.click()
    d.widgets["block.rotation"].setValue(18)
    d.reject()
    window.load_preferences()
    assert window.preferences["block"]["rotation"] == 11
    assert window.preferences["employee"]["shift"] == "T3"
    d = dialog()
    restore = next(b for b in d.findChildren(QPushButton) if b.text() == "Restaurar valores iniciales")
    restore.click()
    assert d.values() == DEFAULTS
    assert window.preferences["block"]["rotation"] == 11  # Not applied yet.
    d.buttons.button(QDialogButtonBox.StandardButton.Ok).click()
    window.load_preferences()
    assert window.preferences == DEFAULTS
    window.save_preferences({**DEFAULTS, "employee": {"shift": "T1"}})
    original_actor = window.session["actor"]["id"]
    window.session["actor"]["id"] = "another-account"
    window.load_preferences()
    assert window.preferences == DEFAULTS
    window.session["actor"]["id"] = original_actor
    window.load_preferences()
    assert window.preferences["employee"]["shift"] == "T1"
    assert not window.store.queue(original_actor)


def test_block_autofill_can_be_overridden_and_edit_keeps_existing_values(window, monkeypatch):
    prefs = copy.deepcopy(DEFAULTS)
    prefs["block"].update(rotation=10, rows=4, columns=3, side="E", prefix="E", building_id="gone")
    window.save_preferences(prefs)
    submitted = []
    monkeypatch.setattr(window, "submit", lambda *args: submitted.append(args))

    def create(form):
        assert form.values()["rotation"] == 10
        assert (form.values()["rows"], form.values()["columns"], form.values()["side"]) == (4, 3, "E")
        assert (form.values()["x"], form.values()["y"]) == (321, 654)
        assert form.values()["building_id"] in {b["id"] for b in window.data["buildings"]}
        form.widgets["rotation"].setValue(12)
        form.widgets["start"].setText("6000")
        return QDialog.DialogCode.Accepted

    monkeypatch.setattr(Form, "exec", create)
    window.block_form(position=[321, 654])
    assert submitted[0][1]["rotation"] == 12
    assert window.preferences["block"]["rotation"] == 10
    existing = window.data["blocks"][0]
    original = copy.deepcopy(existing)

    def edit(form):
        assert form.values()["rotation"] == existing["rotation"]
        return QDialog.DialogCode.Rejected

    monkeypatch.setattr(Form, "exec", edit)
    window.block_form(existing)
    assert existing == original and len(submitted) == 1


def test_row_uses_same_defaults_and_user_rotation_override(window, monkeypatch):
    prefs = copy.deepcopy(DEFAULTS)
    prefs["block"].update(count=40, rotation=10, side="E", prefix="TEST")
    window.save_preferences(prefs)
    sent = []
    monkeypatch.setattr(window, "submit", lambda *args: sent.append(args))

    def create(form):
        assert form.values()["count"] == 40
        assert form.values()["rotation"] == 10
        assert form.values()["prefix"] == "TEST"
        form.widgets["count"].setValue(2)
        form.widgets["rotation"].setValue(12)
        form.widgets["first_number"].setText("6000")
        return QDialog.DialogCode.Accepted

    monkeypatch.setattr(Form, "exec", create)
    monkeypatch.setattr(QDialog, "exec", lambda self: QDialog.DialogCode.Accepted)
    window.create_block_row([400, 400], [500, 500])
    operations = sent[0][1]["operations"]
    assert len(operations) == 2 and all(op["payload"]["rotation"] == 12 for op in operations)
    assert window.preferences["block"]["rotation"] == 10


def test_employee_defaults_never_overwrite_existing_or_unique_fields(window, monkeypatch):
    prefs = copy.deepcopy(DEFAULTS)
    prefs["employee"].update(department="CR QXX", shift="T3", notes="Ejemplo")
    window.save_preferences(prefs)
    sent = []
    monkeypatch.setattr(window, "submit", lambda *args: sent.append(args))

    def create(form):
        assert form.values()["department"] == "CR QXX" and form.values()["shift"] == "T3"
        assert all(form.values()[key] == "" for key in ("employee_number", "first_name", "surname", "email"))
        form.widgets["shift"].setText("T2")
        return QDialog.DialogCode.Accepted

    monkeypatch.setattr(Form, "exec", create)
    window.employee_form()
    assert sent[0][1]["shift"] == "T2" and window.preferences["employee"]["shift"] == "T3"
    employee = window.data["employees"][0]

    def edit(form):
        assert form.values()["department"] == employee["department"]
        assert form.values()["shift"] == employee["shift"]
        return QDialog.DialogCode.Rejected

    monkeypatch.setattr(Form, "exec", edit)
    window.employee_form(True, employee["id"])


def test_map_view_toggle_preserves_aspect_zoom_pending_moves_and_undo(window):
    view = window.map
    before = copy.deepcopy(window.data)
    view.scale(2, 2)
    view.set_editing(True)
    item = view.block_items[0]
    start = QPointF(item.pos())
    item.setPos(start + QPointF(3, 2))
    view.record_move(item, start)
    height, transform, dirty = view.map_height, view.transform(), dict(view.dirty)
    bounds = item.rect()
    for scale, satellite in ((125, False), (150, True), (90, False), (100, True)):
        prefs = copy.deepcopy(window.preferences)
        prefs.update(satellite=satellite, ui_scale=scale)
        window.save_preferences(prefs)
        QApplication.processEvents()
        assert view.map_height == height and view.transform() == transform
        assert view.background_item.isVisible() == satellite
        assert view.dirty == dirty and item.rect() == bounds
        assert view.moves.canUndo()
        assert window.inventory.verticalHeader().defaultSectionSize() == round(30 * scale / 100)
    view.undo_action.trigger()
    assert not view.dirty and item.pos() == start
    assert window.data == before
    view.set_satellite(False)
    view.render(window.data, view.plan["id"])
    assert not view.background_item.isVisible() and view.map_height == height


def test_actions_menu_opens_settings_and_cancel_on_write_failure(window, monkeypatch):
    opened = []
    monkeypatch.setattr(SettingsDialog, "exec", lambda d: opened.append(d.windowTitle()))
    window.populate_options()
    next(a for a in window.options_menu.actions() if a.text() == "Opciones de la aplicación…").trigger()
    assert opened == ["Opciones de Samtec Lockers"]
    messages = []
    monkeypatch.setattr("slms.settings_dialog.QMessageBox.warning", lambda *args: messages.append(args))

    def fail(values):
        raise OSError("test write failure")

    d = SettingsDialog(window.preferences, [], fail, window)
    d.widgets["block.rotation"].setValue(11)
    assert d.apply() is False and messages
    assert d.committed["block"]["rotation"] == 10
    assert d.apply_button.isEnabled()


def test_numbering_options_dependency_persistence_cancel_restore(window, qtbot):
    d = SettingsDialog(window.preferences, window.data["buildings"], window.save_preferences, window)
    qtbot.addWidget(d)
    first, second = d.widgets["block.numbering_first"], d.widgets["block.numbering_second"]
    assert first.count() == 4 and second.count() == 2
    for _, direction in DIRECTIONS:
        first.setCurrentIndex(first.findData(direction))
        compatible = VERTICAL if direction in HORIZONTAL else HORIZONTAL
        assert {second.itemData(i) for i in range(second.count())} == compatible
        for step in compatible:
            second.setCurrentIndex(second.findData(step))
            assert d.apply()
            window.load_preferences()
            assert window.preferences["block"]["numbering_first"] == direction
            assert window.preferences["block"]["numbering_second"] == step
            reopened = SettingsDialog(window.preferences, [], window.save_preferences, window)
            qtbot.addWidget(reopened)
            assert reopened.values() == d.values()
            assert not reopened.apply_button.isEnabled()
            reopened.reject()
    committed = copy.deepcopy(window.preferences)
    d.fill(DEFAULTS)
    assert d.values() == DEFAULTS and d.apply_button.isEnabled()
    d.reject()
    window.load_preferences()
    assert window.preferences == committed


@pytest.mark.parametrize("first,second,expected", LAYOUTS)
def test_new_block_uses_saved_numbering(window, monkeypatch, first, second, expected):
    prefs = copy.deepcopy(DEFAULTS)
    prefs["block"].update(rows=2, columns=3, numbering_first=first, numbering_second=second)
    window.save_preferences(prefs)
    sent = []
    monkeypatch.setattr(window, "submit", lambda *args: sent.append(args))

    def create(form):
        assert form.values()["numbering_first"] == first
        assert form.values()["numbering_second"] == second
        assert form.widgets["numbering_second"].count() == 2
        form.widgets["start"].setText("1")
        return QDialog.DialogCode.Accepted

    monkeypatch.setattr(Form, "exec", create)
    window.block_form()
    assert sent[0][1]["numbers"] == [str(n) for row in expected for n in reversed(row)]
    assert "numbering_first" not in sent[0][1]  # Wire format remains compatible.


def test_numbering_overrides_on_individual_block_and_row(window, monkeypatch):
    sent = []
    monkeypatch.setattr(window, "submit", lambda *args: sent.append(args))

    def create(form):
        first, second = form.widgets["numbering_first"], form.widgets["numbering_second"]
        first.setCurrentIndex(first.findData("top_to_bottom"))
        assert {second.itemData(i) for i in range(second.count())} == HORIZONTAL
        second.setCurrentIndex(second.findData("left_to_right"))
        form.widgets["rows"].setValue(2)
        form.widgets["columns"].setValue(3)
        if "numbers" in form.widgets:
            form.widgets["numbers"].setPlainText("001, A, 5, B, 003, Z")
        else:
            form.widgets["first_number"].setText("6000")
            form.widgets["count"].setValue(2)
        return QDialog.DialogCode.Accepted

    monkeypatch.setattr(Form, "exec", create)
    monkeypatch.setattr(QDialog, "exec", lambda self: QDialog.DialogCode.Accepted)
    window.block_form()
    assert sent[0][1]["numbers"] == ["003", "5", "001", "Z", "B", "A"]
    window.create_block_row([400, 400], [500, 500])
    operations = sent[1][1]["operations"]
    assert operations[0]["payload"]["numbers"] == ["6004", "6002", "6000", "6005", "6003", "6001"]
    assert operations[1]["payload"]["numbers"] == ["6010", "6008", "6006", "6011", "6009", "6007"]
    assert window.preferences == DEFAULTS


def test_legacy_and_incompatible_numbering_preferences():
    assert normalize_preferences({"block": {"rows": 4, "columns": 3}}) == DEFAULTS
    assert normalize_preferences({"block": {"numbering_first": "bad", "numbering_second": []}}) == DEFAULTS
    result = normalize_preferences({"block": {"numbering_first": "bottom_to_top", "numbering_second": "top_to_bottom"}})
    assert result["block"]["numbering_first"] == "bottom_to_top"
    assert result["block"]["numbering_second"] in HORIZONTAL
