# 常用的工具类
import json
import os
import queue
import time
from PySide6.QtCore import QThread, Signal

from src.core.directory_hash import DirectoryHasher
from src.hasher import calculateHash
from src.utils.logger import getLogger
from src.constant import TASK_FINISHED

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

    def __init__(self):
        super().__init__()
        self.statu = WAITING
        self.file_path = ""

    def setTask(self, path, hash_algorithm):
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
    process = Signal(int) # 发送已处理数量通知
    completed = Signal(str) # 发送任务完成通知
    process_info = Signal(str) # 发送单个文件计算结果用于实时更新UI

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.is_running = True  # 运行中
        self.total_task: int = 0  # 文件总数
        self.completed_task: int = 0  # 完成任务总数
        self.tasks = queue.Queue()  # 记录需要计算哈希值的文件
        self.max_concurrent_thread: int = 10  # 最大并发
        self.working_task: list[TaskThread] = []  # 当前正在执行任务
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
        for _ in range(self.max_concurrent_thread):
            self.working_task.append(TaskThread())
        self.is_running = True
        if self.directory is None:
            self.logger.warning("QDH directory setting is None")
            return
        if not os.path.exists(self.directory):
            self.logger.warning(f"QDH Path {self.directory} is not exist")
            return
        if not os.path.isdir(self.directory):
            self.logger.warning(
                f"QDH Path {self.directory} is not a directory")
        self.start()

    def run(self):
        for root, dirs, files in os.walk(self.directory):
            for file_name in files:
                if file_name == "checksum.json":
                    continue
                file_path = os.path.join(root, file_name)
                self.total_task += 1
                self.tasks.put(file_path)

        available_keys = queue.SimpleQueue()
        for id in range(self.max_concurrent_thread):
            available_keys.put(id)
        while self.is_running:
            running_thread = sum(
                1 for th in self.working_task if th.statu == RUNNING
            )
            if not self.tasks.empty() or running_thread > 0:
                self.process.emit(self.completed_task)
            else:
                self.process.emit(self.total_task)
                self.completed.emit(TASK_FINISHED)
                self.is_running = False

            try:
                while not available_keys.empty():
                    id = available_keys.get(False, 3)
                    task = self.tasks.get_nowait()
                    th = self.working_task[id]
                    th.setTask(task, self.hash_algorithm)
                    th.start()
            except queue.Empty:
                time.sleep(0.1)
                pass

            for id in range(len(self.working_task)):
                val = self.working_task[id]
                key = val.file_path
                if val.statu == RUNNING or val.statu == WAITING:
                    continue
                elif val.statu == COMPLETE:
                    self.result[os.path.relpath(
                        key, self.directory)] = val.result
                elif val.statu == FAILED:
                    self.failed.emit(os.path.relpath(
                        key, self.directory), val.error_message)
                    continue
                self.process_info.emit("|".join([key, val.result]))
                available_keys.put(id)
                self.completed_task += 1
            if available_keys.empty():
                time.sleep(0.1)

    def saveToFile(self, path: str = None):
        """保存文件"""
        if path is None:
            return super().saveToFile()

        if not os.path.exists(path):
            os.makedirs(path)

        with open(os.path.join(self.directory, "checksum.json"), "w") as f:
            data = {
                "hash": self.hash_algorithm,
                "data": self.result
            }
            f.write(json.dumps(data, indent=4))

    def stop(self):
        self.is_running = False

    def close(self):
        # TODO 会让主线程退出，调用主QObject的close了
        self.is_running = False
        self.working_task.clear()
        self.tasks = queue.Queue()
