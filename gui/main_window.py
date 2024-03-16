import sys
from PySide6.QtWidgets import QGraphicsTextItem, QApplication, QMainWindow, QGraphicsView, QGraphicsScene, QVBoxLayout, QWidget
from PySide6.QtGui import QPainter, QColor, QPen
from PySide6.QtCore import Qt

from .temporal_unit_block import TemporalUnitBlock

class RulerWidget(QWidget):
    def __init__(self, orientation, parent=None):
        super().__init__(parent)
        self.orientation = orientation
        self.setMinimumHeight(20)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(event.rect(), QColor("#323232"))  # Ruler color

        # tic marks
        tic_pen = QPen(QColor("#ffffff"), 1)
        painter.setPen(tic_pen)

        tic_interval = 20
        tic_length = 10

        # Draw ruler tics
        label_margin = 30  # label margin
        for i in range(label_margin, self.width(), tic_interval):
            if self.orientation == "top":
                painter.drawLine(i, self.height(), i, self.height() - tic_length)
            else:
                painter.drawLine(i, 0, i, tic_length)

class MaquetteMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.lane_height = 60
        self.next_lane_number = 1
        self.num_tracks = 0
        self.track_labels = {}  

    def initUI(self):
        self.setWindowTitle("Maquette")
        self.setGeometry(100, 100, 800, 600)  # initial window size

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        self.top_ruler = RulerWidget("top")
        self.bottom_ruler = RulerWidget("bottom")

        self.graphicsView = QGraphicsView()
        self.graphicsView.setStyleSheet("background-color: #323232;")
        self.scene = QGraphicsScene()
        self.graphicsView.setScene(self.scene)

        layout.addWidget(self.top_ruler)
        layout.addWidget(self.graphicsView, 1)
        layout.addWidget(self.bottom_ruler)
        
        self.scene.setSceneRect(0, 0, 2000, 2000)
    
    def mouseDoubleClickEvent(self, event):
        mouse_position = self.graphicsView.mapToScene(event.position().toPoint())        
        
        y_position = self.num_tracks * self.lane_height
        
        new_block_width = 100
        new_block_height = self.lane_height - 5
        new_block = TemporalUnitBlock(mouse_position.x(), y_position, new_block_width, new_block_height, self.lane_height)

        self.scene.addItem(new_block)
        
        track_number = self.num_tracks + 1
        if track_number not in self.track_labels:
            track_label = QGraphicsTextItem(str(track_number))
            track_label.setDefaultTextColor(Qt.white)
            track_label.setPos(-30, y_position)  # Adjust x as needed to position labels in the margin
            self.scene.addItem(track_label)
            self.track_labels[track_number] = track_label
        
        self.num_tracks += 1

    def addBlock(self, position):
        scene_position = self.graphicsView.mapToScene(position)

        block_width = 100 
        block_height = 50
        
        block = TemporalUnitBlock(block_width, block_height)
        block.setPos(scene_position.x(), scene_position.y() - block_height / 2)
        self.scene.addItem(block)

    def resizeEvent(self, event):
        self.scene.setSceneRect(0, 0, self.graphicsView.viewport().width(), self.graphicsView.viewport().height())
        super().resizeEvent(event)
        for track_number, label in self.track_labels.items():
            label.setPos(-30, (track_number - 1) * self.lane_height)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MaquetteMainWindow()
    window.show()
    sys.exit(app.exec())
