import sys
import subprocess
import tempfile
import os
from PySide6.QtWidgets import QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget, QDialog, QPlainTextEdit
from PySide6.QtGui import QSyntaxHighlighter, QTextCharFormat, QColor, QFont, QKeyEvent
from PySide6.QtCore import QRegularExpression, Qt

class PythonSyntaxHighlighter(QSyntaxHighlighter):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.highlightRules = []

        keywordFormat = QTextCharFormat()
        keywordFormat.setForeground(QColor("blue"))
        keywordFormat.setFontWeight(QFont.Bold)
        keywords = [
            "\\bdef\\b", "\\bclass\\b", "\\bif\\b", "\\belif\\b", "\\belse\\b",
            "\\bwhile\\b", "\\bfor\\b", "\\btry\\b", "\\bexcept\\b", "\\bfinally\\b",
            "\\bwith\\b", "\\bas\\b", "\\breturn\\b", "\\byield\\b", "\\bimport\\b",
            "\\bfrom\\b", "\\bpass\\b", "\\bbreak\\b", "\\bcontinue\\b", "\\band\\b",
            "\\bor\\b", "\\bnot\\b", "\\bis\\b", "\\blambda\\b", "\\bassert\\b",
            "\\bglobal\\b", "\\bnonlocal\\b", "\\bTrue\\b", "\\bFalse\\b", "\\bNone\\b"
        ]
        for word in keywords:
            self.highlightRules.append((QRegularExpression(word), keywordFormat))

        self.commentFormat = QTextCharFormat()
        self.commentFormat.setForeground(QColor("red"))
        self.highlightRules.append((QRegularExpression("#[^\n]*"), self.commentFormat))

    def highlightBlock(self, text):
        for pattern, format in self.highlightRules:
            expression = QRegularExpression(pattern)
            matchIterator = expression.globalMatch(text)
            while matchIterator.hasNext():
                match = matchIterator.next()
                self.setFormat(match.capturedStart(), match.capturedLength(), format)
        self.setCurrentBlockState(0)

class EnhancedCodeEditor(QPlainTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.highlighter = PythonSyntaxHighlighter(self.document())

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key_Tab:
            self.insertPlainText("    ")  # Insert four spaces for tab
            return
        elif event.key() in [Qt.Key_Return, Qt.Key_Enter]:
            cursor = self.textCursor()
            current_line_text = cursor.block().text()
            indent_count = len(current_line_text) - len(current_line_text.lstrip(' '))
            super().keyPressEvent(event)  # Let the parent class handle the actual Return press event

            # Check if the current line ends with a colon
            if current_line_text.rstrip().endswith(":"):
                indent_count += 4  # Add an extra level of indentation for new blocks
                
            self.insertPlainText(' ' * indent_count)  # Insert the calculated amount of indentation
            return
        super().keyPressEvent(event)

class CodeEditorDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Python Code Editor")
        self.code_editor = EnhancedCodeEditor(self)
        self.code_editor.setPlainText("# Write your Python code here.\ndef custom_function():\n    return {'key': 'value'}\n\nprint(custom_function())")
        self.run_button = QPushButton("Run and Close", self)
        self.run_button.clicked.connect(self.run_code)
        
        layout = QVBoxLayout()
        layout.addWidget(self.code_editor)
        layout.addWidget(self.run_button)
        self.setLayout(layout)
    
    def run_code(self):
        code = self.code_editor.toPlainText()
        with tempfile.NamedTemporaryFile('w', delete=False, suffix='.py') as tmp_file:
            tmp_file.write(code)
            tmp_path = tmp_file.name

        try:
            output = subprocess.check_output(['python', tmp_path], text=True)
            print("Script Output:", output)
        except subprocess.CalledProcessError as e:
            print("Error executing script:", e.output)
        
        os.unlink(tmp_path)  # Clean up the temporary file
        self.accept()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Enhanced Python Code Editor Example")
        self.open_editor_button = QPushButton("Open Editor")
        self.open_editor_button.clicked.connect(self.open_editor)
        
        self.setCentralWidget(self.open_editor_button)
    
    def open_editor(self):
        dialog = CodeEditorDialog(self)
        dialog.exec()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
