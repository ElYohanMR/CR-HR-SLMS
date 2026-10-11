"""Packaged map interaction check with synthetic, closely spaced labels."""

import copy
import math

from PySide6.QtCore import QPoint, QPointF, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QApplication

from .config import home


def capture_map(window):
    view = window.map
    window.nav.setCurrentRow(1)
    snapshot = copy.deepcopy(window.data)
    base = snapshot["blocks"][0]
    plan_id = base["plan_id"]
    view.render(snapshot, plan_id)
    snapshot["blocks"] = [
        dict(
            base,
            id=f"preview-{i}",
            label=f"N{i + 1:02}",
            x=650 - i * 3 * math.sin(math.radians(10)),
            y=510 + i * 3 * math.cos(math.radians(10)) * 1000 / view.map_height,
            rotation=10,
        )
        for i in range(5)
    ]
    snapshot["lockers"] = [
        dict(id=f"preview-{i}-{j}", block_id=f"preview-{i}", condition="pendiente_verificacion")
        for i in range(5)
        for j in range(12)
    ]
    snapshot["assignments"] = []
    view.render(snapshot, plan_id)
    view.resetTransform()
    view.scale(20, 20)
    first = view.block_items[0]
    view.centerOn(first)
    QApplication.processEvents()
    point = view.mapFromScene(first.mapToScene(QPointF(0, 1.2)))

    def mouse(kind, pos, button, buttons):
        event = QMouseEvent(
            kind,
            QPointF(pos),
            QPointF(view.viewport().mapToGlobal(pos)),
            button,
            buttons,
            Qt.KeyboardModifier.NoModifier,
        )
        QApplication.sendEvent(view.viewport(), event)

    mouse(QMouseEvent.Type.MouseButtonPress, point, Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton)
    mouse(QMouseEvent.Type.MouseButtonRelease, point, Qt.MouseButton.LeftButton, Qt.MouseButton.NoButton)
    assert view.selected_block == first.data["id"]
    view.set_editing(True)
    window.edit_map.setChecked(True)
    window.consult_map.setChecked(False)
    before = QPointF(first.pos())
    mouse(QMouseEvent.Type.MouseButtonPress, point, Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton)
    end = point + QPoint(40, 20)
    mouse(QMouseEvent.Type.MouseMove, end, Qt.MouseButton.NoButton, Qt.MouseButton.LeftButton)
    mouse(QMouseEvent.Type.MouseButtonRelease, end, Qt.MouseButton.LeftButton, Qt.MouseButton.NoButton)
    after = QPointF(first.pos())
    assert after != before and view.moves.count() == 1
    view.undo_action.trigger()
    assert first.pos() == before and not view.dirty
    view.redo_action.trigger()
    assert first.pos() == after
    menu = window.map_menu("", [0, 0])
    menu.popup(view.viewport().mapToGlobal(view.viewport().rect().center() + QPoint(90, -30)))
    QApplication.processEvents()
    window.grab().save(str(home() / "mapa-deshacer.png"))
    menu.grab().save(str(home() / "mapa-deshacer-menu.png"))
    menu.close()
    menu.deleteLater()
    view.set_editing(False)
    window.edit_map.setChecked(False)
    window.consult_map.setChecked(True)
    view.render(window.data, window.plan_combo.currentData())
    view.fit()
