import base64
import copy
from PySide6.QtCore import Qt, QPointF, Signal
from PySide6.QtGui import QPixmap, QPen, QColor, QBrush, QPolygonF, QFont
from PySide6.QtWidgets import (
    QGraphicsView,
    QGraphicsScene,
    QGraphicsRectItem,
    QGraphicsEllipseItem,
    QGraphicsPolygonItem,
    QGraphicsItem,
)


class BlockItem(QGraphicsRectItem):
    def __init__(self, block, available, total, callback, changed):
        super().__init__(0, 0, 64, 32)
        self.data = block
        self.callback, self.changed = callback, changed
        self.setBrush(QColor("#087f8c" if available else "#44546b"))
        self.setPen(QPen(QColor("#ffffff"), 1.5))
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges)
        self.setPos(block["x"], block["y"])
        self.setRotation(block["rotation"])
        self.setTransformOriginPoint(32, 16)
        from PySide6.QtWidgets import QGraphicsSimpleTextItem

        self.caption = QGraphicsSimpleTextItem(f"{block['label']}\n{available}/{total} libres", self)
        self.caption.setBrush(QColor("white"))
        self.caption.setFont(QFont("Segoe UI", 6))
        self.caption.setPos(4, 2)
        self.setToolTip(f"{block['label']} · doble clic para abrir")
        self.setZValue(5)

    def mouseDoubleClickEvent(self, event):
        self.callback(self.data["id"])
        event.accept()

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionChange and self.scene():
            return QPointF(max(0, min(936, value.x())), max(0, min(968, value.y())))
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged and self.scene():
            self.changed(self.data["id"], self.pos())
        return super().itemChange(change, value)


class Vertex(QGraphicsEllipseItem):
    def __init__(self, point, callback):
        super().__init__(-5, -5, 10, 10)
        self.callback = callback
        self.setPos(*point)
        self.setBrush(QColor("#ffffff"))
        self.setPen(QPen(QColor("#cf3d49"), 2))
        self.setFlags(
            QGraphicsItem.GraphicsItemFlag.ItemIsMovable | QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges
        )
        self.setZValue(10)

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionChange:
            return QPointF(max(0, min(1000, value.x())), max(0, min(1000, value.y())))
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged and self.scene():
            self.callback(self.pos())
        return super().itemChange(change, value)


class MapView(QGraphicsView):
    blockOpened = Signal(str)

    def __init__(self):
        super().__init__()
        self.setScene(QGraphicsScene(self))
        self.setSceneRect(0, 0, 1000, 1000)
        from PySide6.QtGui import QPainter

        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setBackgroundBrush(QColor("#e9eef3"))
        self.editing = False
        self.dirty = {}
        self.shapes = []
        self.block_items = []
        self.vertices = []
        self.plan = None

    def render(self, snapshot, plan_id):
        self.scene().clear()
        self.dirty = {}
        self.block_items = []
        self.vertices = []
        self.plan = next((p for p in snapshot.get("plans", []) if p["id"] == plan_id), None)
        if not self.plan:
            return
        if self.plan.get("background"):
            pix = QPixmap()
            pix.loadFromData(base64.b64decode(self.plan["background"]))
            if not pix.isNull():
                item = self.scene().addPixmap(pix)
                from PySide6.QtGui import QTransform

                item.setTransform(QTransform.fromScale(1000 / pix.width(), 1000 / pix.height()))
                item.setOpacity(0.86)
        self.shapes = copy.deepcopy(self.plan["polygons"])
        buildings = {b["id"]: b for b in snapshot.get("buildings", [])}
        for shape in self.shapes:
            polygon = QGraphicsPolygonItem(QPolygonF([QPointF(*p) for p in shape["points"]]))
            polygon.setPen(QPen(QColor("#e64d57"), 3))
            polygon.setBrush(QBrush(QColor(227, 67, 78, 20)))
            polygon.setZValue(1)
            self.scene().addItem(polygon)
            title = self.scene().addText(
                buildings.get(shape["building_id"], {}).get("code", "Edificio"),
                QFont("Segoe UI", 14, QFont.Weight.Bold),
            )
            title.setDefaultTextColor(QColor("#9c1d29"))
            title.setPos(polygon.boundingRect().center())
            title.setZValue(2)
            for index, point in enumerate(shape["points"]):

                def move(pos, s=shape, i=index, p=polygon):
                    s["points"][i] = [round(pos.x(), 2), round(pos.y(), 2)]
                    p.setPolygon(QPolygonF([QPointF(*point) for point in s["points"]]))

                vertex = Vertex(point, move)
                self.scene().addItem(vertex)
                self.vertices.append(vertex)
        occupied = {a["locker_id"] for a in snapshot.get("assignments", []) if a["ended_at"] is None}
        for block in snapshot.get("blocks", []):
            if block["plan_id"] != plan_id:
                continue
            lockers = [locker for locker in snapshot["lockers"] if locker["block_id"] == block["id"]]
            available = sum(locker["condition"] == "utilizable" and locker["id"] not in occupied for locker in lockers)
            item = BlockItem(
                block,
                available,
                len(lockers),
                self.blockOpened.emit,
                lambda id, pos: self.dirty.update({id: (round(pos.x(), 2), round(pos.y(), 2))}),
            )
            self.scene().addItem(item)
            self.block_items.append(item)
        self.set_editing(self.editing)

    def set_editing(self, value):
        self.editing = value
        for item in self.block_items:
            item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, value)
        for vertex in self.vertices:
            vertex.setVisible(value)

    def fit(self):
        self.fitInView(self.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

    def wheelEvent(self, event):
        factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
        if 0.15 < self.transform().m11() * factor < 8:
            self.scale(factor, factor)
        event.accept()
