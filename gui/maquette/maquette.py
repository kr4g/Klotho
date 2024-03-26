import sys
from PySide6.QtWidgets import QApplication, QMainWindow, QGraphicsView, QGraphicsScene, QWidget, QGridLayout

from ..temporal_boxes.temporal_box import TemporalBox
from ..ruler import Ruler

class MaquetteMainWindow(QMainWindow):
    def __init__(self, *args, **kwargs):
        super(MaquetteMainWindow, self).__init__(*args, **kwargs)
        self.setWindowTitle("Maquette")
        self.initUI()

    def initUI(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        grid_layout = QGridLayout(central_widget)

        self.graphicsView = QGraphicsView()
        self.graphicsView.setStyleSheet("background-color: #323232;")
        self.scene = QGraphicsScene()
        self.graphicsView.setScene(self.scene)
        
        self.left_ruler   = Ruler("left")
        self.right_ruler  = Ruler("right")
        self.top_ruler    = Ruler("top")
        self.bottom_ruler = Ruler("bottom")
        
        grid_layout.addWidget(self.top_ruler, 0, 1)
        grid_layout.addWidget(self.left_ruler, 1, 0)
        grid_layout.addWidget(self.graphicsView, 1, 1)
        grid_layout.addWidget(self.right_ruler, 1, 2)
        grid_layout.addWidget(self.bottom_ruler, 2, 1)

        grid_layout.setColumnStretch(1, 1)
        grid_layout.setRowStretch(1, 1)

        self.scene.setSceneRect(0, 0, 2000, 1000)  # Initial scene size        
    
    def mouseDoubleClickEvent(self, event):
        mouse_position = self.graphicsView.mapToScene(event.position().toPoint())
                
        new_block_x_position = mouse_position.x()
        new_block_y_position = mouse_position.y()
        new_block = TemporalBox(x=new_block_x_position, y=new_block_y_position)
        self.scene.addItem(new_block)

    def resizeEvent(self, event):
        self.scene.setSceneRect(0, 0, self.graphicsView.viewport().width(), self.graphicsView.viewport().height())
        super(MaquetteMainWindow, self).resizeEvent(event)
    

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MaquetteMainWindow()
    window.show()
    sys.exit(app.exec())
