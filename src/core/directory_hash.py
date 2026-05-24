
import json
import os
from concurrent.futures import ThreadPoolExecutor, wait
from dataclasses import dataclass

from src.hasher import calculateHash
from src.utils.logger import getLogger

FILE_LOST = 1  # 对比哈希计算结果发现文件缺失
FILE_CHANGED = 2  # 发现文件有变化
FILE_NEW_ADD = 3  # 发现有新文件加入


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
        self.pool = ThreadPoolExecutor()  # 执行线程池
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

    def setHashAlgorithm(self, hash_algorithm: str):
        try:
            calculateHash(None, hash_algorithm)
        except FileNotFoundError:
            pass
        except NotImplementedError as e:
            raise NotImplementedError(e)
        self.hash_algorithm = hash_algorithm

    def saveToFile(self):
        with open(os.path.join(self.directory, f"{self.hash_algorithm}.json"), "w") as f:
            f.write(json.dumps(self.result, indent=4))

    def loadFromFile(self) -> dict:
        file_path = os.path.join(self.directory, f"{self.hash_algorithm}.json")
        if not os.path.exists(file_path):
            err = f"{self.hash_algorithm}.json not founded in {self.directory}"
            self.logger.warning(err)
            raise FileNotFoundError(err)

        with open(os.path.join(self.directory, f"{self.hash_algorithm}.json"), "r") as f:
            res = "".join(f.readlines())
            try:
                res = json.loads(res)
            except json.JSONDecodeError as e:
                res = None
                err = f"{file_path} json file has some mistakes"
                self.logger.warning(err)
                raise e
        return res

    def verify(self) -> bool:
        """
        读取目录下的哈希计算结果，验证目录完整性
        """
        self.error_list.clear()
        hash_from_file = self.loadFromFile()
        keys_from_file = set(hash_from_file.keys())
        self._computeHash()
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

        worker_pool = {}
        for root, dirs, files in os.walk(self.directory):
            for file_name in files:
                if file_name == f"{self.hash_algorithm}.json":
                    # 跳过记录当前hash算法hash值的文件
                    continue
                file_path = os.path.join(root, file_name)
                worker = self.pool.submit(calculateHash, file_path)
                worker_pool[file_path.replace(self.directory, ".")] = worker
        wait(worker_pool.values())

        for key, value in worker_pool.items():
            self.result[key] = value.result()
