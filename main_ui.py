import sys
from PySide6.QtWidgets import QApplication
from qfluentwidgets import MessageBoxBase, BodyLabel, PlainTextEdit
from qfluentwidgets.components import VBoxLayout

from src.ui.main_window import MainWindow


class ErrMessageBox(MessageBoxBase):
    def __init__(self, err_info: str, parent=None):
        super().__init__(parent)
        layout = VBoxLayout(parent)
        title = BodyLabel(text=self.tr("关键错误"))
        messagebox = PlainTextEdit()
        messagebox.setPlainText(err_info)
        messagebox.setReadOnly(True)
        messagebox.setMinimumWidth(580)
        layout.addWidget(title)
        layout.addWidget(messagebox)

        self.viewLayout.addLayout(layout)
        self.cancelButton.setHidden(True)
        self.widget.setMinimumWidth(600)


def main():
    app = QApplication(sys.argv)

    w = MainWindow()
    w.show()

    def handler(exc_type, exc_value, exc_traceback):
        import traceback
        err_info = "".join(traceback.format_exception(
            exc_type, exc_value, exc_traceback))

        m = ErrMessageBox(err_info, w)
        m.exec()
    sys.excepthook = handler
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
