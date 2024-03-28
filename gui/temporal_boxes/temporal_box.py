from PySide6.QtWidgets import QGraphicsRectItem, QMenu, QGraphicsItem
from PySide6.QtGui import QBrush, QColor, QPen, QCursor, QKeyEvent
from PySide6.QtCore import Qt, QRectF

class TemporalBox(QGraphicsRectItem):
    def __init__(self, x, y, width=100, height=50, parent=None):
        super().__init__(x, y, width, height, parent)
        self.setBrush(QBrush(QColor(100, 200, 255)))
        self.setPen(QPen(QColor(80, 169, 200)))
        self.setFlag(QGraphicsItem.ItemIsMovable)
        self.setFlag(QGraphicsItem.ItemIsSelectable)
        self.setFlag(QGraphicsItem.ItemIsFocusable)
        self.setAcceptHoverEvents(True)
        self.materials = {}
        self.edgeMargin = 5.0  # detect resizing
        self.resizing = False
        self.resizeDirection = None

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() in (Qt.Key_Delete, Qt.Key_Backspace):
            self.deleteItem()
            event.accept()
        else:
            super().keyPressEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.RightButton:
            self.showContextMenu(event.screenPos())
        pos = event.pos()
        rect = self.rect()
        if QRectF(rect.left(), rect.top(), self.edgeMargin, rect.height()).contains(pos) or QRectF(rect.right() - self.edgeMargin, rect.top(), self.edgeMargin, rect.height()).contains(pos):
            self.resizing = True
            self.resizeDirection = 'horizontal'
        elif QRectF(rect.left(), rect.top(), rect.width(), self.edgeMargin).contains(pos) or QRectF(rect.left(), rect.bottom() - self.edgeMargin, rect.width(), self.edgeMargin).contains(pos):
            self.resizing = True
            self.resizeDirection = 'vertical'
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.resizing:
            newRect = QRectF(self.rect())
            pos = event.pos()
            if self.resizeDirection == 'horizontal':
                if pos.x() < newRect.center().x(): # left
                    newRect.setLeft(pos.x())
                else:
                    newRect.setRight(pos.x())
            elif self.resizeDirection == 'vertical':
                if pos.y() < newRect.center().y(): # top
                    newRect.setTop(pos.y())
                else:
                    newRect.setBottom(pos.y())
            self.setRect(newRect.normalized())
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self.resizing:
            self.resizing = False
            self.resizeDirection = None            
        else:
            super().mouseReleaseEvent(event)
    
    def hoverMoveEvent(self, event):
        pos = event.pos()
        rect = self.rect()
        if QRectF(rect.left(), rect.top(), self.edgeMargin, rect.height()).contains(pos):
            self.setCursor(QCursor(Qt.SizeHorCursor))
        elif QRectF(rect.right() - self.edgeMargin, rect.top(), self.edgeMargin, rect.height()).contains(pos):
            self.setCursor(QCursor(Qt.SizeHorCursor))
        elif QRectF(rect.left(), rect.top(), rect.width(), self.edgeMargin).contains(pos):
            self.setCursor(QCursor(Qt.SizeVerCursor))
        elif QRectF(rect.left(), rect.bottom() - self.edgeMargin, rect.width(), self.edgeMargin).contains(pos):
            self.setCursor(QCursor(Qt.SizeVerCursor))
        else:
            self.setCursor(QCursor(Qt.ArrowCursor))

        super().hoverMoveEvent(event)
    
    def showContextMenu(self, position):
        contextMenu = QMenu()
        contextMenu.addAction("Edit")
        contextMenu.addAction("Evaluate")
        contextMenu.addAction("Lock")
        contextMenu.addAction("Import Material")
        contextMenu.addAction("Import Note List")
        deleteAction = contextMenu.addAction("Delete")
        selectedAction = contextMenu.exec(QCursor.pos())
        
        if selectedAction == deleteAction:
            self.deleteItem()
    
    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemSelectedChange:
            if value:
                self.setBrush(QBrush(QColor("yellow")))
            else:
                self.setBrush(QBrush(QColor(100, 200, 255)))
        return super().itemChange(change, value)

    def adjustScale(self, newScaleFactor, oldScaleFactor):
        if oldScaleFactor == 0: return  # Avoid division by zero
        scaleFactorRatio = newScaleFactor / oldScaleFactor
        currentRect = self.rect()
        newLeft = currentRect.left() * scaleFactorRatio
        newWidth = currentRect.width() * scaleFactorRatio
        self.setRect(QRectF(newLeft, currentRect.y(), newWidth, currentRect.height()))
        self.update()

    def deleteItem(self):
        self.scene().removeItem(self)

