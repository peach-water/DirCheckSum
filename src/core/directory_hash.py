
import json
import os
import queue
import time
from concurrent.futures import ThreadPoolExecutor, wait
from dataclasses import dataclass

from src.constant import FILE_CHANGED, FILE_LOST, FILE_NEW_ADD
from src.hasher import calculateHash
from src.utils.logger import getLogger

MAX_THREAD = 10

G_DirectoryHash = None


def getDirectoryHasher():
    global G_DirectoryHash
    if G_DirectoryHash is None:
        G_DirectoryHash = DirectoryHasher()
    return G_DirectoryHash


@dataclass
class FileState:
    file_path: str
    old_hash: str
    new_hash: str
    state: int

    def __lt__(self, other: FileState):
        if self.state == other.state:
            return self.file_path < other.file_path
        return self.state < other.state


class DirectoryHasher:
    """
    计算给定目录下所有文件的哈希值
    以json格式保存每个文件的哈希值
    """

    def __init__(self):
        self.pool = ThreadPoolExecutor(max_workers=MAX_THREAD)  # 执行线程池
        self.directory = None  # 目录位置
        self.result = {}  # 哈希计算结果
        self.logger = getLogger("directoryHasher")
        self.hash_algorithm = "sha256"  # 使用哈希算法
        self.error_list: list[FileState] = []  # 记录出错的文件

    def close(self):
        """
        安全关闭
        """
        self.pool.shutdown()

    def shutdown(self):
        """
        立即关闭
        """
        self.pool.shutdown(wait=False, cancel_futures=True)

    def setDirectory(self, path: str):
        self.directory = path
        self.logger.info(f"set directory: {path}")

    def setHashAlgorithm(self, hash_algorithm: str):
        try:
            calculateHash(None, hash_algorithm)
        except FileNotFoundError:
            pass
        except NotImplementedError as e:
            raise NotImplementedError(e)
        self.logger.info(f"set hash algorithm: {hash_algorithm}")
        self.hash_algorithm = hash_algorithm

    def saveToFile(self):
        if len(self.result) == 0:
            return
        with open(os.path.join(self.directory, "checksum.json"), "w") as f:
            data = {
                "hash": self.hash_algorithm,
                "data": self.result
            }
            f.write(json.dumps(data, indent=4))

    def loadFromFile(self) -> dict:
        file_path = os.path.join(self.directory, "checksum.json")
        if not os.path.exists(file_path):
            err = f"checksum.json not founded in {self.directory}"
            self.logger.warning(err)
            raise FileNotFoundError(err)

        with open(os.path.join(self.directory, "checksum.json"), "r") as f:
            res = "".join(f.readlines())
            try:
                res = json.loads(res)
            except json.JSONDecodeError as e:
                res = None
                err = f"{file_path} json file has some mistakes"
                self.logger.warning(err)
                raise e
        self.logger.info("加载校验和文件成功")
        return res

    def verify(self) -> bool:
        """
        读取目录下的哈希计算结果，验证目录完整性
        """
        self.error_list.clear()
        hash_from_file = self.loadFromFile().get("data")
        keys_from_file = set(hash_from_file.keys())
        keys_from_compute = set(self.result.keys())
        for key in hash_from_file.keys():
            if key in keys_from_compute:
                if self.result[key] != hash_from_file[key]:
                    file_status = FileState(
                        key, hash_from_file[key], self.result[key], FILE_CHANGED)
                    self.error_list.append(file_status)
                keys_from_compute.discard(key)
                keys_from_file.discard(key)
        for key in keys_from_file:
            file_status = FileState(key, hash_from_file[key], None, FILE_LOST)
            self.error_list.append(file_status)
        for key in keys_from_compute:
            file_status = FileState(key, None, self.result[key], FILE_NEW_ADD)
            self.error_list.append(file_status)
        self.error_list.sort()
        return len(self.error_list) == 0

    def getErrorListReport(self) -> list[str]:
        """
        依据错误记录生成文件对比报告
        """
        res = []
        for s in self.error_list:
            if s.state == FILE_LOST:
                res.append("FILE LSOT: " + s.file_path)
            elif s.state == FILE_CHANGED:
                res.append("FILE CHANGED: " + s.file_path)
            elif s.state == FILE_NEW_ADD:
                res.append("FILE NEW ADD: " + s.file_path)
        return res

    def getHashListReport(self) -> list[list[str]]:
        """
        返回hash计算结果，返回值是一个两列的list列表。
        如果没有结果，返回None
        """
        if len(self.result) == 0:
            return None
        res = []
        for key, val in self.result.items():
            row = []
            row.append(key)
            row.append(val)
            res.append(row)
        return res

    def _computeHash(self):
        if self.directory is None:
            self.logger.warning(f"Path is not set")
            raise FileNotFoundError(f"Path is not set")
        if not os.path.exists(self.directory):
            self.logger.warning(f"Path {self.directory} not exist")
            raise FileNotFoundError(f"Path {self.directory} not exist")
        if not os.path.isdir(self.directory):
            self.logger.warning(f"Path {self.directory} is not directory")
            raise FileNotFoundError(f"Path {self.directory} is not directory")

        tasks = queue.Queue()
        for root, dirs, files in os.walk(self.directory):
            for file_name in files:
                if file_name == "checksum.json":
                    continue
                tasks.put(os.path.join(root, file_name))

        worker_pool = {}
        while not tasks.empty() or len(worker_pool) > 0:
            workding_thread = sum(
                1 for val in worker_pool.values() if val.running())
            if workding_thread <= MAX_THREAD:
                try:
                    while workding_thread <= MAX_THREAD:
                        task = tasks.get_nowait()
                        worker = self.pool.submit(
                            calculateHash,
                            task
                        )
                        worker_pool[task.replace(self.directory, ".")] = worker
                        workding_thread += 1
                except queue.Empty:
                    pass

            if len(worker_pool) > 0:
                remove_keys = set()
                for key, val in worker_pool.items():
                    if not val.running():
                        self.result[key] = val.result()
                        remove_keys.add(key)
                        self.logger.info(f"计算完成: {key}")
                for key in remove_keys:
                    worker_pool.pop(key)
                if len(remove_keys) == 0:
                    time.sleep(0.1)
