import base64
import copy
from PySide6.QtCore import Qt, QPointF, Signal, QVariantAnimation, QEasingCurve
from PySide6.QtGui import (
    QPixmap,
    QPen,
    QColor,
    QBrush,
    QPolygonF,
    QFont,
    QPainter,
    QPainterPath,
    QUndoStack,
    QUndoCommand,
    QKeySequence,
)
from PySide6.QtWidgets import (
    QGraphicsView,
    QGraphicsScene,
    QGraphicsRectItem,
    QGraphicsEllipseItem,
    QGraphicsPolygonItem,
    QGraphicsItem,
    QGraphicsSimpleTextItem,
    QFrame,
    QVBoxLayout,
    QLabel,
    QPushButton,
)


# Fixed map-space width: zoom scales the whole map, never the stored geometry.
# Nearby or newly created blocks must not shrink existing labels on refresh.
BLOCK_SIZE = 14 / 5


def block_status(lockers, occupied):
    total = len(lockers)
    assigned = sum(item["id"] in occupied for item in lockers)
    available = sum(item["condition"] == "utilizable" and item["id"] not in occupied for item in lockers)
    if available:
        return available, assigned, "#187842", "Con espacios disponibles"
    if total and assigned == total:
        return available, assigned, "#c42b32", "Bloque completamente asignado"
    return available, assigned, "#946200", "Sin disponibles · requiere revisión"


class SearchHalo(QGraphicsRectItem):
    """Paint-only decoration: it must never obscure another item's hit shape."""

    def shape(self):
        return QPainterPath()

    def contains(self, point):
        return False


class MoveItem(QUndoCommand):
    def __init__(self, item, before, after):
        super().__init__("movimiento de bloque" if isinstance(item, BlockItem) else "movimiento de contorno")
        self.item, self.before, self.after = item, QPointF(before), QPointF(after)

    def undo(self):
        self.item.setPos(self.before)

    def redo(self):
        self.item.setPos(self.after)


class BlockItem(QGraphicsRectItem):
    def __init__(self, block, color, status, size, view):
        super().__init__(-size / 2, -size / 2, size, size)
        self.data, self.view = block, view
        self.setBrush(QColor({"#187842": "#e5f5eb", "#c42b32": "#ffe6e7"}.get(color, "#fff0cb")))
        pen = QPen(QColor(color), 1.5)
        pen.setCosmetic(True)
        self.setPen(pen)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges)
        self.setPos(view.to_scene([block["x"], block["y"]]))
        self.setRotation(block["rotation"])
        self.caption = QGraphicsSimpleTextItem(block["label"], self)
        self.caption.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
        font = QFont("Segoe UI")
        # Shape text at a normal font size, then scale its geometry. Sub-point
        # fonts round glyph widths on Windows and lose digits at high zoom.
        font.setPointSizeF(9)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        font.setBold(True)
        self.caption.setFont(font)
        self.caption.setBrush(QColor(color))
        bounds = self.caption.boundingRect()
        scale = min(size * 0.9 / max(bounds.width(), 1), size * 0.72 / max(bounds.height(), 1))
        self.caption.setScale(scale)
        self.caption.setPos(-bounds.width() * scale / 2, -bounds.height() * scale / 2)
        self.setToolTip(
            f"{block['label']} · {status}\nAcerca el mapa para leer etiquetas próximas. Clic para consultar."
        )
        self.setZValue(5)
        self.halo = SearchHalo(self.rect().adjusted(-size * 0.3, -size * 0.3, size * 0.3, size * 0.3), self)
        halo_pen = QPen(QColor("#1685ff"), 3)
        halo_pen.setCosmetic(True)
        self.halo.setPen(halo_pen)
        self.halo.setBrush(Qt.BrushStyle.NoBrush)
        self.halo.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
        self.halo.hide()
        self.drag_start = None

    def shape(self):
        # Qt's default rect shape expands a cosmetic 1.5-pixel pen by 1.5
        # *scene units*. At close zoom that invisible area steals neighbour
        # clicks. Use the label geometry; Qt applies rotation and view zoom.
        path = QPainterPath()
        path.addRect(self.rect())
        return path

    def contains(self, point):
        return self.rect().contains(point)

    def mousePressEvent(self, event):
        # QGraphicsView can nominate a neighbour touched by the mouse pixel's
        # rectangle. Let Qt try the next item unless the actual point is inside.
        if not self.contains(event.pos()):
            event.ignore()
            return
        if event.button() == Qt.MouseButton.LeftButton:
            self.view.stop_highlight()
            self.drag_start = QPointF(self.pos()) if self.view.editing else None
        if not self.view.editing and event.button() == Qt.MouseButton.LeftButton:
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        if event.button() == Qt.MouseButton.LeftButton and self.drag_start is not None:
            self.view.record_move(self, self.drag_start)
            self.drag_start = None
        if not self.view.editing and event.button() == Qt.MouseButton.LeftButton:
            self.view.show_card(self.data["id"])

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionChange and self.scene():
            return QPointF(max(0, min(1000, value.x())), max(0, min(self.view.map_height, value.y())))
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged and self.scene():
            position = tuple(self.view.from_scene(self.pos()))
            original = (round(self.data["x"], 2), round(self.data["y"], 2))
            if position == original:
                self.view.dirty.pop(self.data["id"], None)
            else:
                self.view.dirty[self.data["id"]] = position
        return super().itemChange(change, value)


class Vertex(QGraphicsEllipseItem):
    def __init__(self, point, callback, view):
        super().__init__(-4, -4, 8, 8)
        self.callback, self.view = callback, view
        self.setPos(view.to_scene(point))
        self.setBrush(QColor("white"))
        self.setPen(QPen(QColor("#cf3d49"), 2))
        self.setFlags(
            QGraphicsItem.GraphicsItemFlag.ItemIsMovable | QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges
        )
        self.setZValue(10)
        self.drag_start = None

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_start = QPointF(self.pos())
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        if event.button() == Qt.MouseButton.LeftButton and self.drag_start is not None:
            self.view.record_move(self, self.drag_start)
            self.drag_start = None

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionChange:
            return QPointF(max(0, min(1000, value.x())), max(0, min(self.view.map_height, value.y())))
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged and self.scene():
            self.callback(self.pos())
        return super().itemChange(change, value)


class MapView(QGraphicsView):
    blockOpened = Signal(str)
    assignmentsOpened = Signal(str)
    contextRequested = Signal(str, object, object)
    rowPicked = Signal(object, object)
    rowCancelled = Signal()

    def __init__(self):
        super().__init__()
        self.setScene(QGraphicsScene(self))
        self.map_height = 1000
        self.setSceneRect(0, 0, 1000, 1000)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setBackgroundBrush(QColor("#eeeeee"))
        self.editing = False
        self.picking_row = False
        self.row_start = None
        self.dirty, self.shapes, self.block_items, self.vertices = {}, [], [], []
        self.plan = None
        self.selected_block = None
        self.details = {}
        self.highlighted_block = None
        self.moves = QUndoStack(self)
        self.moves.setUndoLimit(100)
        self.undo_action = self.moves.createUndoAction(self, "Deshacer")
        self.redo_action = self.moves.createRedoAction(self, "Rehacer")
        for action, shortcut in (
            (self.undo_action, QKeySequence.StandardKey.Undo),
            (self.redo_action, QKeySequence.StandardKey.Redo),
        ):
            action.setShortcuts(QKeySequence.keyBindings(shortcut))
            action.setShortcutContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
            self.addAction(action)
        self.pulse = QVariantAnimation(self)
        self.pulse.setDuration(2000)
        self.pulse.setStartValue(0.12)
        self.pulse.setKeyValueAt(0.5, 1.0)
        self.pulse.setEndValue(0.12)
        self.pulse.setLoopCount(-1)
        self.pulse.setEasingCurve(QEasingCurve.Type.InOutSine)
        self.pulse.valueChanged.connect(self.paint_highlight)
        self.card = QFrame(self.viewport())
        self.card.setObjectName("blockCard")
        self.card.setStyleSheet("#blockCard { background: white; border: 2px solid #555; border-radius: 5px; }")
        self.card.setFixedWidth(300)
        layout = QVBoxLayout(self.card)
        self.card_title, self.card_status = QLabel(), QLabel()
        self.card_title.setWordWrap(True)
        self.card_status.setWordWrap(True)
        layout.addWidget(self.card_title)
        layout.addWidget(self.card_status)
        self.assignments_button = QPushButton("Ver asignaciones del bloque")
        self.assignments_button.clicked.connect(lambda: self.assignmentsOpened.emit(self.selected_block))
        layout.addWidget(self.assignments_button)
        open_button = QPushButton("Ver casilleros del bloque")
        open_button.clicked.connect(lambda: self.blockOpened.emit(self.selected_block))
        layout.addWidget(open_button)
        close_button = QPushButton("Cerrar detalle")
        close_button.clicked.connect(self.hide_card)
        layout.addWidget(close_button)
        self.card.hide()

    def to_scene(self, point):
        return QPointF(point[0], point[1] * self.map_height / 1000)

    def from_scene(self, point):
        return [round(point.x(), 2), round(point.y() * 1000 / self.map_height, 2)]

    def record_move(self, item, before):
        if self.editing and not self.picking_row and before != item.pos():
            self.moves.push(MoveItem(item, before, item.pos()))

    def block_at(self, point):
        # Respect paint stacking, but exclude captions, halos and cosmetic pen
        # padding. Checking local coordinates also handles rotated labels.
        for item in self.scene().items(
            point, Qt.ItemSelectionMode.IntersectsItemShape, Qt.SortOrder.DescendingOrder, self.transform()
        ):
            if isinstance(item, BlockItem) and item.contains(item.mapFromScene(point)):
                return item
        return None

    def contextMenuEvent(self, event):
        if self.picking_row:
            self.picking_row = False
            self.rowCancelled.emit()
            event.accept()
            return
        point = self.mapToScene(event.pos())
        if not self.plan or not self.sceneRect().contains(point):
            event.ignore()
            return
        item = self.block_at(point)
        self.contextRequested.emit(item.data["id"] if item else "", self.from_scene(point), event.globalPos())
        event.accept()

    def mousePressEvent(self, event):
        if self.picking_row and event.button() == Qt.MouseButton.LeftButton:
            point = self.mapToScene(event.position().toPoint())
            if self.sceneRect().contains(point):
                position = self.from_scene(point)
                if self.row_start is None:
                    self.row_start = position
                    self.setToolTip("Marca el final de la fila. Clic derecho para cancelar.")
                else:
                    start = self.row_start
                    self.picking_row = False
                    self.row_start = None
                    self.rowPicked.emit(start, position)
            event.accept()
            return
        super().mousePressEvent(event)

    def hide_card(self):
        self.selected_block = None
        self.card.hide()

    def show_card(self, block_id):
        if self.editing or block_id not in self.details:
            return
        self.selected_block = block_id
        block, available, assigned, total, color, status = self.details[block_id]
        self.card_title.setText("Bloque " + block["label"])
        self.card_status.setText(
            f"{status}\n{available}/{total} disponibles · {assigned} asignados\nSegún la última sincronización."
        )
        self.card.setStyleSheet(f"#blockCard {{ background: white; border: 2px solid {color}; border-radius: 5px; }}")
        self.card.adjustSize()
        self.card.move(max(4, self.viewport().width() - self.card.width() - 12), 12)
        self.card.show()
        self.card.raise_()

    def render(self, snapshot, plan_id):
        highlighted = self.highlighted_block if self.plan and self.plan["id"] == plan_id else None
        self.stop_highlight()
        selected = self.selected_block if self.plan and self.plan["id"] == plan_id else None
        self.hide_card()
        # Commands reference graphics items; release them before clearing scene.
        self.moves.clear()
        self.scene().clear()
        self.dirty, self.block_items, self.vertices, self.details, self.shapes = {}, [], [], {}, []
        self.plan = next((p for p in snapshot.get("plans", []) if p["id"] == plan_id), None)
        self.map_height = 1000
        if not self.plan:
            return
        if self.plan.get("background"):
            pix = QPixmap()
            pix.loadFromData(base64.b64decode(self.plan["background"]))
            if not pix.isNull():
                self.map_height = 1000 * pix.height() / pix.width()
                item = self.scene().addPixmap(pix)
                item.setScale(1000 / pix.width())
        self.setSceneRect(0, 0, 1000, self.map_height)
        self.shapes = copy.deepcopy(self.plan["polygons"])
        buildings = {b["id"]: b for b in snapshot.get("buildings", [])}
        for shape in self.shapes:
            polygon = QGraphicsPolygonItem(QPolygonF([self.to_scene(p) for p in shape["points"]]))
            pen = QPen(QColor("#e64d57"), 2)
            pen.setCosmetic(True)
            polygon.setPen(pen)
            polygon.setBrush(QBrush(QColor(227, 67, 78, 15)))
            polygon.setZValue(1)
            self.scene().addItem(polygon)
            title = self.scene().addText(
                buildings.get(shape["building_id"], {}).get("code", "Edificio"),
                QFont("Segoe UI", 12, QFont.Weight.Bold),
            )
            title.setDefaultTextColor(QColor("#9c1d29"))
            title.setPos(polygon.boundingRect().center())
            title.setZValue(2)
            for index, point in enumerate(shape["points"]):

                def move(pos, s=shape, i=index, p=polygon, t=title):
                    s["points"][i] = self.from_scene(pos)
                    p.setPolygon(QPolygonF([self.to_scene(point) for point in s["points"]]))
                    t.setPos(p.boundingRect().center())

                vertex = Vertex(point, move, self)
                self.scene().addItem(vertex)
                self.vertices.append(vertex)
        occupied = {a["locker_id"] for a in snapshot.get("assignments", []) if a["ended_at"] is None}
        blocks = [b for b in snapshot.get("blocks", []) if b["plan_id"] == plan_id]
        by_block = {}
        for locker in snapshot.get("lockers", []):
            by_block.setdefault(locker["block_id"], []).append(locker)
        for block in blocks:
            lockers = by_block.get(block["id"], [])
            available, assigned, color, status = block_status(lockers, occupied)
            self.details[block["id"]] = (block, available, assigned, len(lockers), color, status)
            item = BlockItem(block, color, status, BLOCK_SIZE, self)
            self.scene().addItem(item)
            self.block_items.append(item)
        self.set_editing(self.editing)
        if selected:
            self.show_card(selected)
        if highlighted:
            self.start_highlight(highlighted)

    def paint_highlight(self, opacity):
        for item in self.block_items:
            if item.data["id"] == self.highlighted_block:
                margin = 5 / max(self.transform().m11(), 0.01)
                item.halo.setRect(item.rect().adjusted(-margin, -margin, margin, margin))
                item.halo.setOpacity(float(opacity))

    def stop_highlight(self):
        self.pulse.stop()
        self.highlighted_block = None
        for item in self.block_items:
            item.halo.hide()
            item.setZValue(5)

    def start_highlight(self, block_id, focus=False):
        self.stop_highlight()
        item = next((item for item in self.block_items if item.data["id"] == block_id), None)
        if item is None:
            return
        self.highlighted_block = block_id
        item.halo.show()
        item.setZValue(20)
        self.pulse.start()
        if focus:
            self.hide_card()
            desired = max(self.transform().m11(), min(32, 24 / item.rect().width()))
            self.scale(desired / self.transform().m11(), desired / self.transform().m11())
            self.centerOn(item.pos())

    def set_editing(self, value):
        self.editing = value
        if not value:
            self.moves.clear()
        if value:
            self.hide_card()
        for item in self.block_items:
            item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, value)
        for vertex in self.vertices:
            vertex.setVisible(value)

    def fit(self):
        self.fitInView(self.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

    def wheelEvent(self, event):
        factor = 1.2 if event.angleDelta().y() > 0 else 1 / 1.2
        if 0.1 < self.transform().m11() * factor < 40:
            self.scale(factor, factor)
        event.accept()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.selected_block:
            self.show_card(self.selected_block)
