import json
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
    FluentIcon,
    InfoBar,
)
from qfluentwidgets.components import (
    BodyLabel,
    CommandBar,
    InfoBarPosition,
    LineEdit,
    MessageBox,
    PrimaryPushButton,
    ProgressBar,
    PushButton,
    TableWidget,
)

from src.constant import FILE_STATUS
from src.utils.entity import QDirectoryHasher
from src.utils.logger import getLogger
from src.utils.platform_util import open_folder


class VerifyInterface(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)

        # 设置对象名称和样式
        self.setObjectName("VerifyInterface")

        self.logger = getLogger("verifyInterface")

        self.dirHasher = QDirectoryHasher()
        self.dirHasher.completed.connect(self._updateTable)
        self.dirHasher.process.connect(self._showProcess)

        self._initUi()

    def _initUi(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setSpacing(20)

        self._setupTopLayout()
        self._setupSecondLayout()
        self._setupTableLayout()
        self._setupBottomLayout()

    def _setupTopLayout(self):
        """创建功能菜单"""
        return
        top_layout = QHBoxLayout()
        top_layout.setSpacing(15)
        command_bar = CommandBar()
        command_bar.setToolButtonStyle(Qt.ToolButtonStyle())
        top_layout.addWidget(command_bar, 1)

        self.main_layout.addLayout(top_layout)

    def _setupSecondLayout(self):
        """第二行目录设置"""
        sec_layout = QHBoxLayout()
        sec_layout.setSpacing(15)
        sec_label = BodyLabel(self.tr("校验目录"), self)
        self.sec_input = LineEdit(self)
        self.sec_input.setPlaceholderText(self.tr("请选择校验目录"))
        self.sec_input.editingFinished.connect(
            lambda: self._updateDirectory(self.sec_input.displayText()))

        sec_button = PushButton(self.tr("浏览"))
        sec_button.setFixedHeight(34)
        sec_button.clicked.connect(self.openDirectoryFolder)

        # 开始按钮、终止按钮
        cancel_button = PrimaryPushButton(
            self.tr("终止"), self, icon=FluentIcon.DELETE
        )
        cancel_button.setFixedHeight(34)
        cancel_button.clicked.connect(self._cancelCompute)
        self.start_button = PrimaryPushButton(
            self.tr("开始"), self, icon=FluentIcon.PLAY
        )
        self.start_button.setFixedHeight(34)
        self.start_button.clicked.connect(self._startCompute)

        sec_layout.addWidget(sec_label)
        sec_layout.addWidget(self.sec_input)
        sec_layout.addWidget(sec_button)
        sec_layout.addWidget(cancel_button)
        sec_layout.addWidget(self.start_button)
        self.main_layout.addLayout(sec_layout)

    def _setupTableLayout(self):
        """创建表格视图"""
        tri_layout = QHBoxLayout()
        tri_layout.setSpacing(70)
        self.tri_table = TableWidget(self)
        self.tri_table.setColumnCount(4)
        self.tri_table.setHorizontalHeaderLabels(
            ["错误状态", "文件名", "原hash值", "新hash值",])
        self.tri_table.setBorderVisible(True)
        self.tri_table.setBorderRadius(12)
        self.tri_table.verticalHeader().setDefaultSectionSize(40)
        self.tri_table.setMinimumWidth(300)
        # 设置固定列宽，允许手动调整宽度
        self.tri_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Interactive
        )
        # 设置列宽
        self.tri_table.setColumnWidth(0, 80)
        self.tri_table.setColumnWidth(1, 120)
        self.tri_table.setColumnWidth(2, 200)
        self.tri_table.setColumnWidth(3, 200)
        # 设置表格不可编辑
        self.tri_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        # 表格双击事件
        self.tri_table.doubleClicked.connect(self.tableDoubleClicked)
        # 工具提示
        self.tri_table.setToolTip("双击行可以打开对应目录")

        tri_layout.addWidget(self.tri_table)
        self.main_layout.addLayout(tri_layout)

    def _setupBottomLayout(self):
        """设置底边进度条"""
        bot_layout = QHBoxLayout()
        self.process_bar = ProgressBar()
        self.process_bar.setRange(0, 100)
        self.process_bar.setFixedHeight(18)
        self.process_bar.setValue(0)
        self.process_bar.setHidden(True)
        bot_layout.addWidget(self.process_bar)
        self.main_layout.addLayout(bot_layout)

    def openDirectoryFolder(self):
        """浏览按钮功能实现"""
        home_path = os.getcwd()
        file_name = QFileDialog.getExistingDirectory(self, "设置目录", home_path)
        if file_name == "":
            return

        self.sec_input.setText(file_name)
        self._updateDirectory(file_name)

    def setHashAlgorithm(self, hash_algorithm):
        """设定校验用哈希算法"""
        try:
            self.dirHasher.setHashAlgorithm(hash_algorithm)
            InfoBar.success(
                "成功",
                f"当前校验和算法为 {hash_algorithm}",
                duration=2000,
                position=InfoBarPosition.TOP,
                parent=self
            )
        except NotImplementedError:
            InfoBar.error(
                "错误",
                f"不支持校验和算法 {hash_algorithm}",
                duration=3000,
                position=InfoBarPosition.TOP,
                parent=self
            )

    def _startCompute(self):
        """开始按钮的功能"""
        if self.sec_input.displayText() == "":
            InfoBar.warning(
                "警告",
                "未指定目录",
                duration=2000,
                position=InfoBarPosition.TOP,
                parent=self
            )
            return
        path = self.sec_input.displayText()
        if not os.path.exists(path):
            InfoBar.warning(
                "警告",
                "目录不存在，检查输入",
                duration=2000,
                position=InfoBarPosition.TOP,
                parent=self
            )
            return
        if not os.path.isdir(path):
            InfoBar.warning(
                "警告",
                "目标并非目录",
                duration=2000,
                position=InfoBarPosition.TOP,
                parent=self
            )
            return
        try:
            res = self.dirHasher.loadFromFile()
            self.dirHasher.setHashAlgorithm(res.get("hash"))
        except FileNotFoundError:
            InfoBar.error(
                "错误",
                "checksum.json 不存在",
                duration=3000,
                position=InfoBarPosition.TOP,
                parent=self
            )
            return
        except json.JSONDecodeError:
            InfoBar.error(
                "错误",
                "checksum.json 不完整",
                duration=3000,
                position=InfoBarPosition.TOP,
                parent=self
            )
            return
        self.dirHasher._computeHash()

    def _cancelCompute(self):
        """取消当前计算任务"""
        if self.dirHasher.isRunning():
            self.dirHasher.stop()
            self.process_bar.setHidden(True)

    def tableDoubleClicked(self, index):
        """双击表格，打开选中行对应目录"""
        row = index.row()
        file_path = self.tri_table.item(row, 1).text()
        file_path_dir = os.path.dirname(file_path)
        file_path_dir = os.path.join(self.dirHasher.directory, file_path_dir)
        file_path_dir = os.path.abspath(file_path_dir)
        if not os.path.exists(file_path_dir):
            InfoBar.error(
                "错误",
                f"目录 {file_path_dir} 不存在",
                duration=3000,
                position=InfoBarPosition.TOP,
                parent=self
            )
            return
        open_folder(file_path_dir)

    def closeEvent(self, event):
        self.dirHasher.close()
        return super().closeEvent(event)

    def _updateDirectory(self, path: str):
        """点击浏览按钮和修改输入框后自动更新"""
        self.dirHasher.setDirectory(path)
        InfoBar.success(
            "成功",
            "目录更新成功",
            position=InfoBarPosition.TOP,
            parent=self
        )

    def _updateTable(self):
        """更新表格数据"""
        self.dirHasher.verify()
        data = self.dirHasher.error_list
        if data is None:
            return

        everything_is_ok = len(data) == 0
        if everything_is_ok:
            m = MessageBox(
                "通知",
                "所有文件通过校验检查",
                parent=self
            )
            m.cancelButton.setHidden(True)
            # m.exec() 会让qtbot.waitSignal卡住
            m.show()
        else:
            m = MessageBox(
                "通知",
                f"{len(data)} 个文件存在错误，已列在表格中",
                parent=self
            )
            m.cancelButton.setHidden(True)
            m.show()

        self.tri_table.setRowCount(len(data))
        for i, s in enumerate(data):
            self.tri_table.setItem(i, 0,
                                   QTableWidgetItem(FILE_STATUS[s.state]))
            self.tri_table.setItem(i, 1, QTableWidgetItem(s.file_path))
            self.tri_table.setItem(i, 2, QTableWidgetItem(
                s.old_hash if s.old_hash is not None else "-"))
            self.tri_table.setItem(i, 3, QTableWidgetItem(
                s.new_hash if s.new_hash is not None else "-"))

    def _showProcess(self, process_num: int):
        """展示当前进度"""
        self.process_bar.setHidden(False)
        percent = int(process_num / max(self.dirHasher.total_task, 1) * 100)
        self.process_bar.setValue(percent)
        if process_num == self.dirHasher.total_task:
            InfoBar.info(
                "通知",
                "计算完成，正在比较",
                position=InfoBarPosition.TOP_RIGHT,
                parent=self
            )
            self.process_bar.setHidden(True)
