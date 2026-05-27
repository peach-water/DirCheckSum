import json
import os
import queue
import time
from functools import partial
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
    ProgressBar,
    PushButton,
    RoundMenu,
    TableWidget,
    TransparentDropDownPushButton,
)
from src.hasher import calculateHash

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
    
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.is_running = True # 运行中
        self.total_task: int = 0 # 文件总数
        self.completed_task: int = 0 # 完成任务总数
        self.tasks = queue.Queue() # 记录需要计算哈希值的文件
        self.max_concurrent_thread: int = 10 # 最大并发
        self.working_task: dict[str, TaskThread] = {} # 当前正在执行任务
        self.logger = getLogger("QDirectoryHasher")

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
                self.process.emit(self.total_task)
                self.completed.emit("完成")
                self.is_running = False
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
    
    def saveToFile(self, path: str = None):
        """保存文件"""
        if path is None:
            return super().saveToFile()

        if not os.path.exists(path):
            os.makedirs(path)

        with open(os.path.join(self.directory, f"{self.hash_algorithm}.json"), "w") as f:
            f.write(json.dumps(self.result, indent=4))

    def stop(self):
        self.is_running = False

    def close(self):
        # TODO 会让主线程退出，调用主QObject的close了
        self.is_running = False
        self.working_task.clear()
        self.tasks = queue.Queue()


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
        self._setupBottomLayout()

    def _setupTopLayout(self):
        # 创建一个水平布局
        top_layout = QHBoxLayout()
        top_layout.setSpacing(15)
        self.command_bar = CommandBar()
        self.command_bar.setToolButtonStyle(
            Qt.ToolButtonStyle()
        )
        top_layout.addWidget(self.command_bar, 1)

        # 设置校验和算法按钮
        layout_button = TransparentDropDownPushButton(
            self.tr("校验和算法"), self, FluentIcon.LAYOUT
        )
        layout_button.setFixedHeight(34)
        layout_button.setMinimumWidth(125)
        layout_button.setToolTip("默认 sha256")
        layout_menu = RoundMenu(parent=self)
        actions = []
        for alg in HASH_ALGORITHM:
            action = Action(text=alg)
            # 使用偏函数固定第二个参数
            action.triggered.connect(partial(self.setHashAlgorithm, alg))
            actions.append(action)
        layout_menu.addActions(actions)
        layout_button.setMenu(layout_menu)
        self.command_bar.addWidget(layout_button)

        # 设置保存按钮
        save_button = PushButton(
            self.tr("保存"), self, FluentIcon.SAVE
        )
        save_button.setFixedHeight(34)
        save_button.clicked.connect(self.saveHashResult)
        self.command_bar.addWidget(save_button)

        # 设置开始、终止按钮
        top_layout.addStretch()
        self.cancel_button = PrimaryPushButton(
            self.tr("终止"), self, icon=FluentIcon.DELETE
        )
        self.cancel_button.clicked.connect(self.cancelCompute)
        top_layout.addWidget(self.cancel_button)
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
        self.tri_table.setColumnWidth(0, 200)
        self.tri_table.setColumnWidth(1, 380)
        # 设置表格不可编辑
        self.tri_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        # 处理表格双击事件
        self.tri_table.doubleClicked.connect(self.tableDoubleClicked)
        # 增加工具提示
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
        展示当前进度
        """
        self.process_bar.setHidden(False)
        percent = int(process_num / self.dirHasher.total_task * 100)
        self.process_bar.setValue(percent)
        if process_num == self.dirHasher.total_task:
            InfoBar.success(
                "通知",
                "计算完成",
                position=InfoBarPosition.TOP_RIGHT,
                parent=self
            )
            self.process_bar.setHidden(True)

    def openDirectoryFolder(self):
        """浏览按钮功能实现"""
        home_path = os.path.abspath(os.path.join("."))
        file_name = QFileDialog.getExistingDirectory(self, "设置目录", home_path)
        if file_name == "":
            return

        self.sec_input.setText(file_name)
        self._updateDirectory(file_name)

    def saveHashResult(self):
        """保存按钮功能实现"""
        if self.dirHasher.getHashListReport() is None:
            InfoBar.info(
                "提示",
                "没有需要保存的结果",
                duration=3000,
                position=InfoBarPosition.TOP,
                parent=self
            )
            return
        home_path = self.dirHasher.directory
        if home_path is None or not os.path.exists(home_path):
            home_path = os.path.abspath(os.path.join("."))
        file_name = QFileDialog.getExistingDirectory(self, "选择保存位置", home_path)
        if file_name == "":
            return
        
        try:
            self.dirHasher.saveToFile(file_name)
            InfoBar.success(
                "成功",
                f"已保存到 {self.dirHasher.directory}",
                duration=2000,
                parent=self,
                position=InfoBarPosition.TOP_RIGHT
            )
            self.logger.info(f"保存至 {self.dirHasher.directory}")
        except Exception as e:
            self.logger.error(f"保存错误：{e}")
            InfoBar.error(
                "错误",
                f"保存出现错误: {e}",
                duration=3000,
                position=InfoBarPosition.TOP,
                parent=self
            )

    def setHashAlgorithm(self, hash_algorithm):
        """设定当前哈希校验和算法"""
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
                f"校验和算法 {hash_algorithm} 不支持",
                duration=3000,
                position=InfoBarPosition.TOP,
                parent=self
            )

    def cancelCompute(self):
        """取消当前计算任务，终止按钮功能"""
        if self.dirHasher.isRunning():
            self.dirHasher.stop()
            self.process_bar.setHidden(True)

    def startCompute(self):
        """开始当前计算任务，开始按钮功能"""
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

    def tableDoubleClicked(self, index):
        """处理表格双击事件，打开对应行所在目录"""
        row = index.row()
        file_path = self.tri_table.item(row, 0).text()
        file_path_dir = os.path.dirname(file_path)
        file_path_dir = os.path.join(self.dirHasher.directory, file_path_dir)
        open_folder(file_path_dir)

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
