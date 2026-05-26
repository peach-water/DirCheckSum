import os
import queue
import time
from PySide6.QtCore import Qt, QThread, Signal
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
    InfoBar,
)
from qfluentwidgets.components import (
    BodyLabel,
    CommandBar,
    InfoBarPosition,
    LineEdit,
    PrimaryPushButton,
    PushButton,
    RoundMenu,
    TableWidget,
    TransparentDropDownPushButton,
)
from src.hasher import calculateHash
from typing import Optional

from src.constant import HASH_ALGORITHM
from src.core.directory_hash import DirectoryHasher
from src.utils.logger import getLogger
from src.utils.platform_util import open_folder

WAITING = 1
RUNNING = 2
COMPLETE = 3
FAILED = 4

class TaskThread(QThread):
    file_path: str
    statu: int
    error_message: str
    hash_algorithm: str
    result: str
    def __init__(self, path, hash_algorithm):
        super().__init__()
        self.file_path = path
        self.hash_algorithm = hash_algorithm
        self.statu = WAITING
    
    def run(self):
        try:
            self.statu = RUNNING
            self.result = calculateHash(self.file_path, self.hash_algorithm)
            self.statu = COMPLETE
        except Exception as e:
            self.statu = FAILED
            self.error_message = str(e)

class QDirectoryHasher(QThread, DirectoryHasher):
    process = Signal(int)
    completed = Signal(str)
    failed = Signal(str, str) # 传递出错信息
    
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.is_running = True # 运行中
        self.total_task: int = 0 # 文件总数
        self.completed_task: int = 0 # 完成任务总数
        self.tasks = queue.Queue() # 记录需要计算哈希值的文件
        self.max_concurrent_thread: int = 10 # 最大并发
        self.working_task: dict[str, TaskThread] = {} # 当前正在执行任务

    def _computeHash(self):
        """
        默认在前端已经设置好所有参数才能执行，但防止意外
        """
        self.result.clear()
        self.total_task = 0
        self.completed_task = 0
        self.tasks = queue.Queue()
        self.working_task.clear()
        self.is_running = True
        if self.directory is None:
            self.logger.warning("QDH directory setting is None")
            return
        if not os.path.exists(self.directory):
            self.logger.error(f"QDH Path {self.directory} is not exist")
            return
        if not os.path.isdir(self.directory):
            self.logger.warning(f"QDH Path {self.directory} is not a directory")
        
        for root, dirs, files in os.walk(self.directory):
            for file_name in files:
                if file_name == f"{self.hash_algorithm}.json":
                    continue
                file_path = os.path.join(root, file_name)
                self.total_task += 1
                self.tasks.put(file_path)
        self.start()
    
    def run(self):
        while self.is_running:
            running_thread = sum(
                1 for th in self.working_task.values() if th.statu == RUNNING
            )
            if not self.tasks.empty():
                self.process.emit(self.completed_task)
            else:
                self.completed.emit("完成")
            if running_thread < self.max_concurrent_thread:
                try:
                    while running_thread < self.max_concurrent_thread:
                        task = self.tasks.get_nowait()
                        th = TaskThread(task, self.hash_algorithm)
                        self.working_task[task] = th
                        th.start()
                        running_thread += 1
                except queue.Empty:
                    pass

            if len(self.working_task) > 0:
                remove_keys = set()
                for key, val in self.working_task.items():
                    if val.statu == RUNNING or val.statu == WAITING:
                        continue
                    elif val.statu == COMPLETE:
                        self.result[key.replace(self.directory, ".")] = val.result
                    elif val.statu == FAILED:
                        self.failed.emit(key.replace(self.directory, "."), val.error_message)
                    remove_keys.add(key)
                    self.completed_task += 1

                for key in remove_keys:
                    self.working_task.pop(key)
            time.sleep(0.1)
    
    def close(self):
        # TODO
        self.is_running = False
        for key, val in self.working_task.items():
            thread = val.currentThread()
            thread.terminate()


class HomeInterface(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        # 设置对象名称和样式
        self.setObjectName("HomeInterface")
        self.setStyleSheet("""HomeInterface{background: black}""")

        self.logger = getLogger("homeInterface")
        self.data = []

        self.dirHasher = QDirectoryHasher(parent)
        self.dirHasher.completed.connect(self.updateTable)
        self.dirHasher.process.connect(self._showprocess)

        self._initUi()

    def _initUi(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setObjectName("main_layout")
        self.main_layout.setSpacing(20)

        self._setupTopLayout()
        self._setupSecondLayout()
        self._setupTableLayout()

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

        # 设置开始按钮
        top_layout.addStretch()
        self.start_button = PrimaryPushButton(
            self.tr("开始"), self, icon=FluentIcon.PLAY)
        self.start_button.setFixedHeight(34)
        self.start_button.clicked.connect(self.startCompute)
        top_layout.addWidget(self.start_button)

        self.main_layout.addLayout(top_layout)

    def _setupSecondLayout(self):
        # 创建第二行的目录设置
        sec_layout = QHBoxLayout()
        sec_layout.setSpacing(15)
        sec_label = BodyLabel(self.tr("计算目录"), self)
        self.sec_input = LineEdit(self)
        self.sec_input.setPlaceholderText(self.tr("请选择一个特定目录"))
        self.sec_input.editingFinished.connect(
            lambda: self._updateDirectory(self.sec_input.displayText()))
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
        self.tri_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Interactive)
        # 设置列宽
        self.tri_table.setColumnWidth(0, 180)
        self.tri_table.setColumnWidth(1, 380)
        # 设置表格不可编辑
        self.tri_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        tri_layout.addWidget(self.tri_table)
        self.main_layout.addLayout(tri_layout)

    def _updateDirectory(self, path):
        """点击按钮和修改输入框后自动更新"""
        self.dirHasher.setDirectory(path)
        InfoBar.success(
            "成功",
            "目录更新成功",
            position=InfoBarPosition.TOP,
            parent=self
        )

    def _showprocess(self, process_num:int) :
        """
        展示当前进度，未来改成进度条
        """
        # TODO
        InfoBar.info(
            "完成数量",
            str(process_num) + "/" + str(self.dirHasher.total_task),
            duration=500,
            position=InfoBarPosition.BOTTOM_RIGHT,
            parent=self
        )

    def openDirectoryFolder(self):
        home_path = os.path.abspath(os.path.join("."))
        file_name = QFileDialog.getExistingDirectory(self, "设置目录", home_path)
        if file_name == "":
            return

        self.sec_input.setText(file_name)
        self._updateDirectory(file_name)

    def startCompute(self):
        """开始按钮功能"""
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
        self.dirHasher._computeHash()

    def closeEvent(self, event):
        self.dirHasher.close()
        return super().closeEvent(event)

    def updateTable(self):
        """更新表格数据"""
        self.data = self.dirHasher.getHashListReport()
        table = self.data
        if table is None:
            return
        
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

        self.tri_table.setRowCount(len(table))
        for i, row in enumerate(table):
            for j, value in enumerate(row):
                item = QTableWidgetItem(value)
                self.tri_table.setItem(i, j, item)
