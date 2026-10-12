import copy

import pytest
from PySide6.QtCore import QPointF
from PySide6.QtWidgets import QDialog, QDialogButtonBox, QPushButton, QApplication

from slms.forms import Form
from slms.local import LocalStore
from slms.preferences import normalize_preferences, DEFAULTS
from slms.settings_dialog import SettingsDialog
from slms.window import Window


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


def test_options_button_opens_window_and_cancel_on_write_failure(window, monkeypatch):
    opened = []
    monkeypatch.setattr(SettingsDialog, "exec", lambda d: opened.append(d.windowTitle()))
    window.options_button.click()
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
