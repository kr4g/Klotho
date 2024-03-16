# background_grid.py

from PySide6.QtWidgets import QGraphicsItem
from PySide6.QtGui import QPainter, QPen, QColor
from PySide6.QtCore import QRectF

class BackgroundGrid(QGraphicsItem):
    def __init__(self, width, height, lane_height, parent=None):
        super().__init__(parent)
        self.width = width
        self.height = height
        self.lane_height = lane_height
        self.grid_color = QColor(192, 192, 192, 128)  # Light grey color with some transparency

    def boundingRect(self):
        return QRectF(0, 0, self.width, self.height)

    def paint(self, painter, option, widget=None):
        pen = QPen(self.grid_color)
        pen.setWidth(0)  # Fine lines
        painter.setPen(pen)

        # vertical lines
        for x in range(0, self.width, 20):  # Assuming tic interval is 20
            painter.drawLine(x, 0, x, self.height)

        # horizontal lines
        for y in range(0, self.height, self.lane_height):
            painter.drawLine(0, y, self.width, y)

    def setWidth(self, new_width):
        self.width = new_width
        self.update()

    def setHeight(self, new_height):
        self.height = new_height
        self.update()
