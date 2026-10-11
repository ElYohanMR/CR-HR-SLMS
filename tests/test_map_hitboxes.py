import math

import pytest
from PySide6.QtCore import QPoint, QPointF, Qt
from PySide6.QtGui import QContextMenuEvent, QMouseEvent
from PySide6.QtWidgets import QApplication

from slms.mapview import MapView


def dense_map(qtbot, angle=10, zoom=20):
    view = MapView()
    qtbot.addWidget(view)
    view.resize(900, 650)
    view.show()
    radians = math.radians(angle)
    data = {
        "plans": [{"id": "plan", "polygons": []}],
        "blocks": [
            dict(id="first", label="N01", plan_id="plan", x=500, y=500, rotation=angle),
            dict(
                id="next",
                label="N02",
                plan_id="plan",
                x=500 - 3 * math.sin(radians),
                y=500 + 3 * math.cos(radians),
                rotation=angle,
            ),
        ],
    }
    view.render(data, "plan")
    view.scale(zoom, zoom)
    view.centerOn(500, 500)
    return view


def context_at(view, point):
    seen = []
    view.contextRequested.connect(lambda *args: seen.append(args))
    event = QContextMenuEvent(QContextMenuEvent.Reason.Mouse, point, view.viewport().mapToGlobal(point))
    QApplication.sendEvent(view.viewport(), event)
    return seen[-1][0]


@pytest.mark.parametrize("angle", [0, 10, 11, 45, 90, -10])
@pytest.mark.parametrize("zoom", [8, 20, 32])
def test_visible_edge_belongs_to_clicked_label(qtbot, angle, zoom):
    view = dense_map(qtbot, angle, zoom)
    first = view.block_items[0]
    point = view.mapFromScene(first.mapToScene(QPointF(0, 1.2)))
    assert first.rect().contains(first.mapFromScene(view.mapToScene(point)))
    assert context_at(view, point) == "first"
    qtbot.mouseClick(view.viewport(), Qt.MouseButton.LeftButton, pos=point)
    assert view.selected_block == "first"
    assert not view.dirty


def test_halo_and_invisible_pen_do_not_capture_empty_space(qtbot):
    view = dense_map(qtbot, 11)
    first = view.block_items[0]
    view.start_highlight("first")
    view.paint_highlight(1)
    # Outside the painted rectangle, but within the default cosmetic pen shape
    # and the blue search halo. Neither decoration is a block target.
    point = view.mapFromScene(first.mapToScene(QPointF(-1.65, 0)))
    assert context_at(view, point) == ""
    qtbot.mouseClick(view.viewport(), Qt.MouseButton.LeftButton, pos=point)
    assert view.selected_block is None
    assert view.highlighted_block == "first"


def test_highlighted_neighbour_does_not_steal_click_or_drag(qtbot):
    view = dense_map(qtbot)
    first, neighbour = view.block_items
    view.start_highlight("next")
    view.paint_highlight(1)
    point = view.mapFromScene(first.mapToScene(QPointF(0, 1.2)))
    assert context_at(view, point) == "first"
    view.set_editing(True)
    before = QPointF(neighbour.pos())
    qtbot.mousePress(view.viewport(), Qt.MouseButton.LeftButton, pos=point)
    destination = point + QPoint(35, 10)
    move = QMouseEvent(
        QMouseEvent.Type.MouseMove,
        QPointF(destination),
        QPointF(view.viewport().mapToGlobal(destination)),
        Qt.MouseButton.NoButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    QApplication.sendEvent(view.viewport(), move)
    qtbot.mouseRelease(view.viewport(), Qt.MouseButton.LeftButton, pos=destination)
    assert neighbour.pos() == before
    assert set(view.dirty) == {"first"}
    assert view.highlighted_block is None


def test_rotated_bounding_box_corner_is_background(qtbot):
    view = dense_map(qtbot, 45)
    first = view.block_items[0]
    # Inside the axis-aligned bounding box, outside the rotated label.
    point = view.mapFromScene(first.pos() + QPointF(1.7, 1.7))
    assert not first.rect().contains(first.mapFromScene(view.mapToScene(point)))
    assert context_at(view, point) == ""


def test_mouse_pixel_touching_neighbour_must_check_exact_position(qtbot):
    view = dense_map(qtbot, 10, 8)
    view.resize(1100, 750)
    first, neighbour = view.block_items
    first.setPos(659.51, 686.52 * 2478 / 3956)
    neighbour.setPos(659.01, 690.87 * 2478 / 3956)
    view.dirty.clear()
    view.centerOn(first)
    QApplication.processEvents()
    point = view.mapFromScene(first.mapToScene(QPointF(0, 1.2)))
    assert first.contains(first.mapFromScene(view.mapToScene(point)))
    assert not neighbour.contains(neighbour.mapFromScene(view.mapToScene(point)))
    qtbot.mouseClick(view.viewport(), Qt.MouseButton.LeftButton, pos=point)
    assert view.selected_block == "first"
