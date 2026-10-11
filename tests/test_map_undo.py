import copy

from PySide6.QtCore import QPoint, QPointF, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QApplication

from slms.mapview import MapView


def drag(qtbot, view, item, delta):
    start = view.mapFromScene(item.pos())
    qtbot.mousePress(view.viewport(), Qt.MouseButton.LeftButton, pos=start)
    end = start + delta
    for position in (start + delta / 2, end):
        event = QMouseEvent(
            QMouseEvent.Type.MouseMove,
            QPointF(position),
            QPointF(view.viewport().mapToGlobal(position)),
            Qt.MouseButton.NoButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )
        QApplication.sendEvent(view.viewport(), event)
    qtbot.mouseRelease(view.viewport(), Qt.MouseButton.LeftButton, pos=end)


def test_undo_redo_drag_and_new_branch_keep_only_unsaved_positions(qtbot):
    view = MapView()
    qtbot.addWidget(view)
    view.resize(900, 650)
    view.show()
    snapshot = {
        "plans": [{"id": "p", "polygons": []}],
        "blocks": [dict(id="b", plan_id="p", label="E01", x=500, y=500, rotation=11)],
    }
    original = copy.deepcopy(snapshot)
    view.render(snapshot, "p")
    view.scale(20, 20)
    view.centerOn(500, 500)
    view.set_editing(True)
    item = view.block_items[0]
    before = QPointF(item.pos())
    drag(qtbot, view, item, QPoint(40, 20))
    after = QPointF(item.pos())
    assert after != before
    assert view.moves.count() == 1  # One drag, not one command per mouse move.
    assert view.undo_action.isEnabled() and not view.redo_action.isEnabled()
    view.activateWindow()
    view.setFocus()
    QApplication.processEvents()
    qtbot.keyClick(view, Qt.Key.Key_Z, Qt.KeyboardModifier.ControlModifier)
    assert item.pos() == before and not view.dirty
    assert view.redo_action.isEnabled()
    view.redo_action.trigger()
    assert item.pos() == after and set(view.dirty) == {"b"}
    view.undo_action.trigger()
    drag(qtbot, view, item, QPoint(-40, 30))
    assert not view.redo_action.isEnabled()
    assert snapshot == original
    view.set_editing(False)  # Save/end session must not permit undo of submitted commands.
    assert not view.undo_action.isEnabled() and not view.redo_action.isEnabled()
    view.render(snapshot, "p")
    view.set_editing(True)
    assert not view.moves.canUndo() and not view.dirty


def test_contour_drag_undo_and_refresh_release_old_items(qtbot):
    view = MapView()
    qtbot.addWidget(view)
    view.resize(900, 650)
    view.show()
    snapshot = {
        "plans": [
            {"id": "p", "polygons": [{"building_id": "building", "points": [[500, 500], [550, 500], [550, 550]]}]}
        ]
    }
    view.render(snapshot, "p")
    view.scale(5, 5)
    view.centerOn(500, 500)
    view.set_editing(True)
    original = copy.deepcopy(view.shapes)
    drag(qtbot, view, view.vertices[0], QPoint(50, 25))
    assert view.shapes != original
    changed = copy.deepcopy(view.shapes)
    view.undo_action.trigger()
    assert view.shapes == original
    view.redo_action.trigger()
    assert view.shapes == changed
    assert snapshot["plans"][0]["polygons"] == original
    view.render(snapshot, "p")
    view.undo_action.trigger()
    assert view.shapes == original and view.moves.count() == 0
