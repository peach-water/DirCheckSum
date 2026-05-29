import os
import pytest
import subprocess


from src.core.directory_hash import DirectoryHasher
from src.hasher import calculateHash, calculateDirHash

TEST_DIR = "./test/data/"


@pytest.fixture(autouse=True)
def file_dark_qss():
    return "./resources/themes/py_dracula_dark.qss"


class TestHasher:
    """
    测试哈希计算
    """

    def test_hasher(self, file_dark_qss):
        test_path = os.path.join(TEST_DIR, "dataForTest")
        res = calculateDirHash(test_path, "sha256")
        assert len(res) == 3
        for key in res.keys():
            assert calculateHash(os.path.join(test_path, key), "sha256") == res[key]

        with pytest.raises(NotImplementedError) as errinfo:
            hash = calculateHash(file_path=file_dark_qss, hashAlgorithm="cyc")
        assert "not implemented" in str(errinfo.value)

        with pytest.raises(FileNotFoundError) as errinfo:
            hash = calculateHash(file_path="cyc", hashAlgorithm="sha256")


class TestDirectoryHahser:
    """
    测试目录哈希计算
    """
    @pytest.fixture
    def setup(self):
        print("准备DirectoryHasher环境")
        self.DH = DirectoryHasher()
        yield
        del self.DH
        print("清除DirectoryHash环境")

    def test_function(self, setup):
        """
        测试主要功能
        """
        test_path = os.path.join(TEST_DIR, "dataForTest\\")
        self.DH.setDirectory(test_path)
        assert self.DH.directory == test_path

        self.DH._computeHash()
        res1 = calculateDirHash(test_path, "sha256")
        res2 = self.DH.result
        for key in res1.keys():
            assert key in res2
            assert res1[key] == res2[key]
        self.DH.saveToFile()
        res3 = self.DH.loadFromFile().get("data")
        for key in res2.keys():
            assert res2[key] == res3[key]
        # 计算空目录时不生成计算结果
        self.DH.result = {}
        test_path = os.path.join(TEST_DIR, "empty")
        if not os.path.exists(test_path):
            os.makedirs(test_path, exist_ok=True)
        self.DH.setDirectory(test_path)
        assert len(os.listdir(test_path)) == 0

    def test_verify(self, setup):
        test_path = os.path.join(TEST_DIR, "verify")
        self.DH.setDirectory(test_path)
        self.DH._computeHash()
        assert self.DH.verify() == False
        from src.constant import FILE_LOST, FILE_CHANGED, FILE_NEW_ADD
        error_list = self.DH.error_list
        assert len(error_list) == 4
        # 应该是前2条报文件缺失，第3条错误报文件变化，第4条报文件新增
        assert error_list[0].state == FILE_LOST
        assert error_list[1].state == FILE_LOST
        assert error_list[2].state == FILE_CHANGED
        assert error_list[3].state == FILE_NEW_ADD

    def test_exception(self, setup):
        """
        异常处理
        """
        # 使用未实现的哈希函数
        with pytest.raises(NotImplementedError):
            self.DH.setHashAlgorithm(None)
        # 未定义计算目录而直接调用
        with pytest.raises(FileNotFoundError):
            self.DH._computeHash()
        # 目录下没有计算好的哈希结果
        test_path = os.path.join(TEST_DIR, "noHashFile")
        self.DH.setDirectory(test_path)
        with pytest.raises(FileNotFoundError):
            self.DH.loadFromFile()
        # 目录下hash文件存在解析错误
        test_path = os.path.join(TEST_DIR, "wrongHashFile")
        self.DH.setDirectory(test_path)
        from json import JSONDecodeError
        with pytest.raises(JSONDecodeError):
            self.DH.loadFromFile()

    def test_main_cli(self):
        t = subprocess.Popen(["uv", "run", "main.py", "test/data/dataForTest", "-v"])
        t.wait()
        if t.returncode == 9009:
            print("未找到uv环境")
            return
        assert t.returncode == 0