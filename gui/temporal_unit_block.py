# File: temporal_unit_block.py
from PySide6.QtWidgets import QGraphicsRectItem, QGraphicsTextItem
from PySide6.QtGui import QBrush, QColor, QPen
from PySide6.QtCore import Qt, QRectF


class TemporalUnitBlock(QGraphicsRectItem):
    def __init__(self, x, y, width, height, track_height, parent=None):
        super().__init__(x, y, width, height, parent)
        self.setBrush(QBrush(QColor(200, 200, 200)))  # Light grey fill
        self.setPen(QPen(QColor(169, 169, 169)))      # Dark grey boundary
        self.setFlag(QGraphicsRectItem.ItemIsMovable)
        self.track_height = track_height

    def mouseReleaseEvent(self, event):
        y_position = round(self.pos().y() / self.track_height) * self.track_height
        self.setY(y_position)
        super().mouseReleaseEvent(event)

    def mouseMoveEvent(self, event):
        super().mouseMoveEvent(event)
        if self.y() < 0:
            self.setY(0)
        else:
            y_position = round(self.y() / self.track_height) * self.track_height
            self.setY(max(y_position, 0))  # Ensures we don't go above track 1
