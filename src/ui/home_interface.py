import os
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QTableWidget,
    QTableWidgetItem,
    QWidget,
    QVBoxLayout,
)
from qfluentwidgets import (
    Action,
    FluentIcon,
)
from qfluentwidgets.components import (
    BodyLabel,
    CommandBar,
    LineEdit,
    PrimaryPushButton,
    PushButton,
    RoundMenu,
    TableWidget,
    TransparentDropDownPushButton,
)

from src.constant import HASH_ALGORITHM
from src.utils.logger import getLogger
from src.utils.platform_util import open_folder


class HomeInterface(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        # 设置对象名称和样式
        self.setObjectName("HomeInterface")
        self.setStyleSheet("""HomeInterface{background: black}""")

        self.logger = getLogger("homeInterface")
        self.data = [["R1C1R1C1R1C1R1C1R1C1R1C1R1C1R1C1R1C1R1C1R1C1R1C1R1C1R1C1R1C1R1C1R1C1R1C1", "R1C2R1C2R1C2R1C2R1C2R1C2R1C2R1C2"],
            ["R2C1", "R2C2"]]

        self._initUi()

    def _initUi(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setObjectName("main_layout")
        self.main_layout.setSpacing(20)

        self._setupTopLayout()
        self._setupSecondLayout()
        self._setupTableLayout()
        self.updateTable()

    def _setupTopLayout(self):
        # 创建一个水平布局
        top_layout = QHBoxLayout()
        top_layout.setSpacing(15)
        self.command_bar = CommandBar()
        self.command_bar.setToolButtonStyle(
            Qt.ToolButtonStyle()
        )
        top_layout.addWidget(self.command_bar, 1)

        # 设置校验和算法
        self.layout_button = TransparentDropDownPushButton(
            self.tr("校验和算法"), self, FluentIcon.LAYOUT
        )
        self.layout_button.setFixedHeight(34)
        self.layout_button.setMinimumWidth(125)
        self.layout_menu = RoundMenu(parent=self)
        for layout in HASH_ALGORITHM:
            action = Action(text=layout)
            # action.triggered.connect()
            self.layout_menu.addAction(action)
        self.layout_button.setMenu(self.layout_menu)
        self.command_bar.addWidget(self.layout_button)

        # 设置目录
        self.command_bar.addAction(
            Action(FluentIcon.FOLDER, text="", triggered=None)
        )

        # 设置开始按钮
        self.start_button = PrimaryPushButton(
            self.tr("开始"), self, icon=FluentIcon.PLAY)
        self.start_button.setFixedHeight(34)
        self.command_bar.addWidget(self.start_button)

        self.main_layout.addLayout(top_layout)

    def _setupSecondLayout(self):
        # 创建第二行的目录设置
        sec_layout = QHBoxLayout()
        sec_layout.setSpacing(15)
        sec_label = BodyLabel(self.tr("计算目录"), self)
        self.sec_input = LineEdit(self)
        self.sec_input.setPlaceholderText(self.tr("请选择一个特定目录"))
        sec_button = PushButton(self.tr("浏览"))
        sec_button.clicked.connect(self.openDirectoryFolder)

        sec_layout.addWidget(sec_label)
        sec_layout.addWidget(self.sec_input)
        sec_layout.addWidget(sec_button)
        self.main_layout.addLayout(sec_layout)

    def _setupTableLayout(self):
        # 创建第三行的表格视图
        tri_layout = QHBoxLayout()
        tri_layout.setSpacing(70)
        self.tri_table = TableWidget(self)
        self.tri_table.setColumnCount(2)
        self.tri_table.setHorizontalHeaderLabels(["文件名", "hash值"])
        self.tri_table.setBorderVisible(True)
        self.tri_table.setBorderRadius(12)
        self.tri_table.verticalHeader().setDefaultSectionSize(40)
        self.tri_table.setMinimumHeight(300)
        # 设置自动调整列宽，但设置后无法手动更改，暂时设定为可交互
        self.tri_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        # 设置列宽
        self.tri_table.setColumnWidth(0, 180)
        self.tri_table.setColumnWidth(1, 380)
        # 设置表格不可编辑
        self.tri_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        tri_layout.addWidget(self.tri_table)
        self.main_layout.addLayout(tri_layout)

    def openDirectoryFolder(self):
        home_path = os.path.abspath(os.path.join("."))
        file_name = QFileDialog.getExistingDirectory(self, "设置目录", home_path)
        if file_name == "":
            return

        self.sec_input.setText(file_name)

    def closeEvent(self, event):
        return super().closeEvent(event)

    def updateTable(self):
        """更新表格数据"""
        table = self.data
        if len(table) == 0:
            self.logger.warning(f"table row = 0, not valid")
            return
        for i, row in enumerate(table):
            if type(row) != list:
                self.logger.warning(f"table row {i} is not a list")
                return
            elif len(row) != 2:
                self.logger.warning(f"table row {i} len {len(row)} != 2")
                return

        self.tri_table.clearContents()
        for i, row in enumerate(table):
            self.tri_table.insertRow(i)
            for j, value in enumerate(row):
                item = QTableWidgetItem(value)
                self.tri_table.setItem(i, j, item)
