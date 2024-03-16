from PySide6.QtWidgets import QMenu, QPushButton, QWidget, QVBoxLayout, QApplication
from PySide6.QtCore import Qt
from PySide6.QtGui import QMouseEvent

class MaterialBlock(QPushButton):
    def __init__(self, material_name, parent=None):
        super().__init__(material_name, parent)
    
    def contextMenuEvent(self, event):
        contextMenu = QMenu(self)
        # Add options to the context menu as needed
        option1Action = contextMenu.addAction("Option 1")
        option2Action = contextMenu.addAction("Option 2")

        action = contextMenu.exec(self.mapToGlobal(event.pos()))
        
        # Handle actions based on what the user selected
        if action == option1Action:
            print("Option 1 was selected")
        elif action == option2Action:
            print("Option 2 was selected")


class MaterialsPalette(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Materials Palette")
        self.setGeometry(100, 100, 400, 300)
        self.layout = QVBoxLayout(self)
        self.layout.setAlignment(Qt.AlignTop)
        self.material_blocks = []
        self.layout.addStretch(1)

    def mouseDoubleClickEvent(self, event: QMouseEvent):
        self.layout.removeItem(self.layout.itemAt(self.layout.count() - 1))
        
        new_block_name = f'Material {len(self.material_blocks) + 1}'
        new_block = MaterialBlock(new_block_name, self)
        self.layout.addWidget(new_block)
        self.material_blocks.append(new_block)
        
        self.layout.addStretch(1)

if __name__ == "__main__":
    app = QApplication([])
    palette = MaterialsPalette()
    palette.show()
    app.exec()
