import copy

from PySide6.QtCore import QPoint, QPointF, Qt
from PySide6.QtGui import QWheelEvent
from PySide6.QtWidgets import QApplication

from slms.mapview import MapView


def test_creating_nearby_blocks_zoom_and_refresh_do_not_shrink_labels(qtbot, system):
    _, client, _ = system
    data = client.get("/snapshot").json()
    original = copy.deepcopy(data)
    view = MapView()
    qtbot.addWidget(view)
    view.resize(1100, 700)
    view.show()
    plan_id = data["blocks"][0]["plan_id"]
    view.render(data, plan_id)
    view.fit()
    initial_size = view.block_items[0].rect().width()
    initial_caption_scale = view.block_items[0].caption.scale()
    first = data["blocks"][0]
    # Simulate the server snapshot after creating a very close neighbour.
    data["blocks"].append(dict(first, id="new-neighbour", x=first["x"] + 1, label=first["label"]))
    view.render(data, plan_id)
    assert all(item.rect().width() == initial_size for item in view.block_items)
    assert all(item.caption.scale() == initial_caption_scale for item in view.block_items)
    for direction in (120, 120, -120, 120, -120):
        before = view.transform().m11()
        point = view.viewport().rect().center()
        event = QWheelEvent(
            QPointF(point),
            QPointF(view.viewport().mapToGlobal(point)),
            QPoint(),
            QPoint(0, direction),
            Qt.MouseButton.NoButton,
            Qt.KeyboardModifier.NoModifier,
            Qt.ScrollPhase.NoScrollPhase,
            False,
        )
        QApplication.sendEvent(view.viewport(), event)
        after = view.transform().m11()
        assert abs(after / before - (1.2 if direction > 0 else 1 / 1.2)) < 1e-8
        view.render(data, plan_id)
        assert view.transform().m11() == after
        for item in view.block_items:
            assert item.rect().width() == initial_size
            assert item.caption.scale() == initial_caption_scale
            assert abs(view.transform().mapRect(item.rect()).width() - initial_size * after) < 1e-8
    # Moving and confirming a neighbour at the same position must not resize either.
    view.set_editing(True)
    view.block_items[1].setPos(view.block_items[0].pos())
    data["blocks"][1].update(x=first["x"], y=first["y"])
    view.set_editing(False)
    view.render(data, plan_id)
    assert all(item.rect().width() == initial_size for item in view.block_items)
    # Removing the added block restores the snapshot, not a different label size.
    view.render(original, plan_id)
    assert view.block_items[0].rect().width() == initial_size
    assert data["blocks"][0] == original["blocks"][0]
