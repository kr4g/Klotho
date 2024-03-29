from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QPainter, QColor, QPen, QPalette, QMouseEvent
from PySide6.QtCore import Signal

class Ruler(QWidget):
    scaleChanged = Signal(int)

    def __init__(self, orientation, parent=None):
        super().__init__(parent)
        self.orientation = orientation
        self.ticInterval = 15
        self.isDragging = False
        if self.orientation in ["top", "bottom"]:
            self.setMinimumHeight(20)
        else:
            self.setMinimumWidth(20)
        self.setBackgroundRole(QPalette.Base)
        self.setAutoFillBackground(True)

    def adjustTicInterval(self, newInterval):
        self.ticInterval = newInterval
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(event.rect(), QColor("#323232"))
        tic_pen = QPen(QColor("#ffffff"), 1)
        painter.setPen(tic_pen)
        
        if self.orientation in ["top", "bottom"]:
            self.drawHorizontalRuler(painter)
        else:
            self.drawVerticalRuler(painter)
    
    def drawVerticalRuler(self, painter):
        for i in range(0, self.height(), self.ticInterval):
            if self.orientation == "left":
                painter.drawLine(self.width() - 10, i, self.width(), i)
            elif self.orientation == "right":
                painter.drawLine(0, i, 10, i)

    def drawHorizontalRuler(self, painter):
        largeTic, mediumTic, smallTic = 20, 15, 10
        intervalCount = 0

        subTicCount = max(1, min(10, self.ticInterval // 10))
        
        while intervalCount * self.ticInterval < self.width():
            ticLength = smallTic
            if intervalCount % 10 == 0:
                ticLength = mediumTic
                if intervalCount % 100 == 0:
                    ticLength = largeTic

            yStart = self.height() - ticLength if self.orientation == "top" else 0
            yEnd = self.height() if self.orientation == "top" else ticLength

            # primary tic
            painter.drawLine(intervalCount * self.ticInterval,
                             yStart,
                             intervalCount * self.ticInterval,
                             yEnd)
            
            # sub-tics
            if self.ticInterval > 20:
                for subTic in range(1, subTicCount):
                    subTicPos = intervalCount * self.ticInterval + (subTic * self.ticInterval // subTicCount)
                    subTicLength = smallTic // 2  # sub-tic length
                    ySubStart = self.height() - subTicLength if self.orientation == "top" else 0
                    ySubEnd = self.height() if self.orientation == "top" else subTicLength
                    painter.drawLine(subTicPos, ySubStart, subTicPos, ySubEnd)

            intervalCount += 1

    def mousePressEvent(self, event: QMouseEvent):
        if self.orientation in ["top", "bottom"]:
            self.isDragging = True
            self.dragStartY = event.pos().y()

    def mouseMoveEvent(self, event: QMouseEvent):
        if self.isDragging:
            deltaY = event.pos().y() - self.dragStartY
            if abs(deltaY) > 2:  # sensitivity
                newScale = max(5, min(30, self.ticInterval + deltaY // 5))
                self.scaleChanged.emit(newScale)
                self.ticInterval = newScale
                self.dragStartY = event.pos().y()
                self.update()

    def mouseReleaseEvent(self, event: QMouseEvent):
        self.isDragging = False
