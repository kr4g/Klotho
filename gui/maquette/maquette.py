import sys
from PySide6.QtWidgets import QApplication, QMainWindow, QGraphicsView, QGraphicsScene, QWidget, QGridLayout
from PySide6.QtCore import Qt, QRectF

from ..temporal_boxes.temporal_box import TemporalBox
from ..ruler import Ruler

class MaquetteMainWindow(QMainWindow):
    def __init__(self, *args, **kwargs):
        super(MaquetteMainWindow, self).__init__(*args, **kwargs)
        self.setWindowTitle("Maquette")
        self.currentScaleFactor = 15
        self.initUI()
        self.resize(1400, 700)

    def initUI(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        grid_layout = QGridLayout(central_widget)

        self.graphicsView = QGraphicsView()
        self.graphicsView.setStyleSheet("background-color: #323232;")
        self.graphicsView.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.graphicsView.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)

        self.scene = QGraphicsScene()
        self.scene.setSceneRect(0, 0, 1400, 700)
        self.scene.changed.connect(self.updateSceneRect)
        self.graphicsView.setScene(self.scene)
        
        self.left_ruler = Ruler("left")
        self.right_ruler = Ruler("right")
        self.top_ruler = Ruler("top")
        self.bottom_ruler = Ruler("bottom")

        self.top_ruler.scaleChanged.connect(self.updateRulerScale)
        self.bottom_ruler.scaleChanged.connect(self.updateRulerScale)
        self.top_ruler.scaleChanged.connect(self.onScaleChanged)
        self.bottom_ruler.scaleChanged.connect(self.onScaleChanged)
        
        grid_layout.addWidget(self.top_ruler, 0, 1)
        grid_layout.addWidget(self.bottom_ruler, 2, 1)
        grid_layout.addWidget(self.left_ruler, 1, 0)
        grid_layout.addWidget(self.right_ruler, 1, 2)
        grid_layout.addWidget(self.graphicsView, 1, 1)

    def mouseDoubleClickEvent(self, event):
        mouse_position = self.graphicsView.mapToScene(event.position().toPoint())
        box_width = 100          
        box_height = 50  
        new_block_x_position = mouse_position.x() - box_width / 2
        new_block_y_position = mouse_position.y() - box_height / 2
        new_block = TemporalBox(x=new_block_x_position, y=new_block_y_position)
        self.scene.addItem(new_block)
        self.updateSceneRect()

    def resizeEvent(self, event):
        self.updateSceneRect()
        super(MaquetteMainWindow, self).resizeEvent(event)

    def updateSceneRect(self):
        # Expand the scene rect to include all items
        currentRect = self.scene.itemsBoundingRect()
        viewportRect = QRectF(0, 0, self.graphicsView.viewport().width(), self.graphicsView.viewport().height())
        newRect = currentRect.united(viewportRect)
        self.scene.setSceneRect(newRect)
    
    def updateRulerScale(self, newTicInterval):
        # Update the tic intervals of both rulers
        self.top_ruler.adjustTicInterval(newTicInterval)
        self.bottom_ruler.adjustTicInterval(newTicInterval)
    
    # Example of connecting scale change to TemporalBox instances
    def onScaleChanged(self, newScaleFactor):
        oldScaleFactor = self.currentScaleFactor
        self.currentScaleFactor = newScaleFactor  # Update the current scale factor
        for item in self.scene.items():
            if isinstance(item, TemporalBox):
                item.adjustScale(newScaleFactor, oldScaleFactor)



if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MaquetteMainWindow()
    window.show()
    sys.exit(app.exec())
