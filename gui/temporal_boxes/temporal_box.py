from PySide6.QtWidgets import QGraphicsRectItem, QMenu
from PySide6.QtGui import QBrush, QColor, QPen, QCursor
from PySide6.QtCore import Qt

class TemporalBox(QGraphicsRectItem):
    def __init__(self, x, y, width=100, height=50, parent=None):
        super().__init__(x, y, width, height, parent)
        self.setBrush(QBrush(QColor(100, 200, 255)))  
        self.setPen(QPen(QColor(80, 169, 200)))      
        self.setFlag(QGraphicsRectItem.ItemIsMovable)
        self.setFlag(QGraphicsRectItem.ItemIsSelectable)
        self.materials = {}

    def mouseMoveEvent(self, event):
        super().mouseMoveEvent(event)
        y_position = self.y()
        self.setY(y_position)

    def mousePressEvent(self, event):
        if event.button() == Qt.RightButton:
            self.showContextMenu(event.screenPos())
        super().mousePressEvent(event)
    
    def mouseDoubleClickEvent(self, event):
        # Open TemporalBoxEditor
        
        super().mouseDoubleClickEvent(event)

    def showContextMenu(self, position):
        contextMenu = QMenu()
        option1Action = contextMenu.addAction("Edit")
        option1Action = contextMenu.addAction("Evaluate")
        option1Action = contextMenu.addAction("Lock")
        option2Action = contextMenu.addAction("Import Material")
        option2Action = contextMenu.addAction("Import Note List")
        option2Action = contextMenu.addAction("Delete")
        # Execute the context menu at the current cursor position
        selectedAction = contextMenu.exec(QCursor.pos())
        # Handle the actions accordingly here

