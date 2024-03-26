from PySide6.QtWidgets import QGraphicsRectItem, QGraphicsTextItem, QMenu, QGraphicsSceneMouseEvent
from PySide6.QtGui import QBrush, QColor, QPen, QCursor
from PySide6.QtCore import Qt, QRectF

from .code_editor import CodeEditorDialog

class TemporalUnitBlock(QGraphicsRectItem):
    def __init__(self, x, y, width, height, track_height, parent=None):
        super().__init__(x, y, width, height, parent)
        self.setBrush(QBrush(QColor(200, 200, 200)))  # Light grey fill
        self.setPen(QPen(QColor(169, 169, 169)))      # Dark grey boundary
        self.setFlag(QGraphicsRectItem.ItemIsMovable)
        self.setFlag(QGraphicsRectItem.ItemIsSelectable)  # Enable selection
        self.track_height = track_height
        # self.script = None
        self.data_dict = {}

    def mousePressEvent(self, event):
        if event.button() == Qt.RightButton:
            self.showContextMenu(event.screenPos())
        super().mousePressEvent(event)

    def showContextMenu(self, position):
        contextMenu = QMenu()
        option1Action = contextMenu.addAction("Option 1")
        option2Action = contextMenu.addAction("Option 2")
        # Execute the context menu at the current cursor position
        selectedAction = contextMenu.exec(QCursor.pos())
        # Handle the actions accordingly here

    def mouseMoveEvent(self, event):
        super().mouseMoveEvent(event)
        y_position = self.y() #round(self.y() / self.track_height) * self.track_height
        self.setY(y_position)
