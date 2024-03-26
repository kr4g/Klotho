from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QPainter, QColor, QPen, QPalette

class Ruler(QWidget):
    
    def __init__(self, orientation, parent=None):
        super().__init__(parent)
        self.orientation = orientation
        if self.orientation in ["top", "bottom"]:
            self.setMinimumHeight(20)
        else:
            self.setMinimumWidth(20)
        self.setBackgroundRole(QPalette.Base)
        self.setAutoFillBackground(True)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(event.rect(), QColor("#323232"))  # Ruler background

        tic_pen = QPen(QColor("#ffffff"), 1)
        painter.setPen(tic_pen)

        tic_interval = 15
        tic_length = 10

        if self.orientation in ["top", "bottom"]:
            for i in range(0, self.width(), tic_interval):
                if self.orientation == "top":
                    painter.drawLine(i, self.height(), i, self.height() - tic_length)
                elif self.orientation == "bottom":
                    painter.drawLine(i, 0, i, tic_length)
        else:
            for i in range(0, self.height(), tic_interval):
                if self.orientation == "left":
                    painter.drawLine(self.width() - tic_length, i, self.width(), i)
                elif self.orientation == "right":
                    painter.drawLine(0, i, tic_length, i)
