import sys
from PySide6.QtWidgets import QPushButton, QApplication, QMainWindow, QGraphicsView, QGraphicsScene, QVBoxLayout, QWidget
from PySide6.QtCore import Qt

from .temporal_unit_block import TemporalUnitBlock
from .ruler import Ruler
# from .grid import BackgroundGrid
from .materials_palette import MaterialsPalette

class MaquetteMainWindow(QMainWindow):
    def __init__(self, *args, **kwargs):
        super(MaquetteMainWindow, self).__init__(*args, **kwargs)
        self.lane_height = 60
        self.next_lane_number = 1
        self.num_tracks = 0
        self.initUI()

    def initUI(self):
        self.setWindowTitle("Maquette")
        self.setGeometry(100, 100, 800, 600)  # initial window size

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        self.showMaterialsBtn = QPushButton("Show Materials")
        self.showMaterialsBtn.clicked.connect(self.toggleMaterialsPalette)
        layout.addWidget(self.showMaterialsBtn)

        self.top_ruler = Ruler("top")
        self.bottom_ruler = Ruler("bottom")

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
        y_click_position = mouse_position.y()
        lane_height = self.lane_height
        lane_y_upper_boundary = (int(y_click_position // lane_height) * lane_height)
        
        # Create and add a new block to the scene
        new_block_width = 100
        new_block_height = lane_height - 5
        new_block_x_position = mouse_position.x() - (new_block_width / 2)
        new_block = TemporalUnitBlock(new_block_x_position, lane_y_upper_boundary, new_block_width, new_block_height, lane_height)
        self.scene.addItem(new_block)

    def addBlock(self, position):
        scene_position = self.graphicsView.mapToScene(position)

        block_width = 100 
        block_height = 50
        
        block = TemporalUnitBlock(block_width, block_height)
        block.setPos(scene_position.x(), scene_position.y() - block_height / 2)
        self.scene.addItem(block)

    def resizeEvent(self, event):
        self.scene.setSceneRect(0, 0, self.graphicsView.viewport().width(), self.graphicsView.viewport().height())
        super(MaquetteMainWindow, self).resizeEvent(event)
    
    def toggleMaterialsPalette(self):
        if not hasattr(self, 'materialsPalette'):
            self.materialsPalette = MaterialsPalette()
        if self.materialsPalette.isVisible():
            self.materialsPalette.hide()
            self.showMaterialsBtn.setText("Show Materials")
        else:
            self.materialsPalette.show()
            self.showMaterialsBtn.setText("Hide Materials")


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MaquetteMainWindow()
    window.show()
    sys.exit(app.exec())
