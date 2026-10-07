import base64
import copy
import math
from PySide6.QtCore import Qt, QPointF, Signal
from PySide6.QtGui import QPixmap, QPen, QColor, QBrush, QPolygonF, QFont, QPainter
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


def block_status(lockers, occupied):
    total = len(lockers)
    assigned = sum(item["id"] in occupied for item in lockers)
    available = sum(item["condition"] == "utilizable" and item["id"] not in occupied for item in lockers)
    if available:
        return available, assigned, "#187842", "Con espacios disponibles"
    if total and assigned == total:
        return available, assigned, "#c42b32", "Bloque completamente asignado"
    return available, assigned, "#946200", "Sin disponibles · requiere revisión"


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

    def mousePressEvent(self, event):
        if not self.view.editing and event.button() == Qt.MouseButton.LeftButton:
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        if not self.view.editing and event.button() == Qt.MouseButton.LeftButton:
            self.view.show_card(self.data["id"])

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionChange and self.scene():
            return QPointF(max(0, min(1000, value.x())), max(0, min(self.view.map_height, value.y())))
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged and self.scene():
            self.view.dirty[self.data["id"]] = tuple(self.view.from_scene(self.pos()))
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

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionChange:
            return QPointF(max(0, min(1000, value.x())), max(0, min(self.view.map_height, value.y())))
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged and self.scene():
            self.callback(self.pos())
        return super().itemChange(change, value)


class MapView(QGraphicsView):
    blockOpened = Signal(str)
    assignmentsOpened = Signal(str)

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
        self.dirty, self.shapes, self.block_items, self.vertices = {}, [], [], []
        self.plan = None
        self.selected_block = None
        self.details = {}
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
        selected = self.selected_block if self.plan and self.plan["id"] == plan_id else None
        self.hide_card()
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
            # Size in map units: dense rows remain separate and grow naturally when zooming.
            pos = self.to_scene([block["x"], block["y"]])
            distances = [
                math.hypot(pos.x() - other["x"], pos.y() - other["y"] * self.map_height / 1000)
                for other in blocks
                if other["id"] != block["id"]
            ]
            size = min(14, min(distances, default=100) * 0.6)
            size = max(1, size)
            item = BlockItem(block, color, status, size, self)
            self.scene().addItem(item)
            self.block_items.append(item)
        self.set_editing(self.editing)
        if selected:
            self.show_card(selected)

    def set_editing(self, value):
        self.editing = value
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
