
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QGuiApplication
from qfluentwidgets import FluentIcon, FluentWindow

from src.ui.home_interface import HomeInterface

class MainWindow(FluentWindow):
    def __init__(self):
        super().__init__()
        self.initWindow()

        self.homeInterface = HomeInterface(self)
        self.addSubInterface(self.homeInterface, FluentIcon.HOME, self.tr("主页"))

    def initWindow(self):
        """初始化窗口"""
        self.resize(800, 600)
        self.setMinimumWidth(400)
        self.setMinimumHeight(300)
        self.setWindowTitle("哈希校验器")

        # 设置窗口居中
        desktop = QGuiApplication.primaryScreen().geometry()
        w, h = desktop.width(), desktop.height()
        self.move(w // 2 - self.width() // 2, h // 2 - self.height() // 2)

        self.show()
        QApplication.processEvents()

    def resizeEvent(self, e):
        return super().resizeEvent(e)

    def closeEvent(self, e):
        super().closeEvent(e)
        QApplication.quit()

    