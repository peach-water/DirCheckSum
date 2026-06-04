# 测试QDirectoryHasher模块、Home_interface模块有效性
import os
import pytest
import time
from PySide6.QtCore import Qt
from qfluentwidgets import Action, RoundMenu

from src.constant import HASH_ALGORITHM
from src.hasher import calculateDirHash
from src.ui.home_interface import HomeInterface
from src.utils.entity import QDirectoryHasher

TEST_DIR = "./test/data/"


class TestQDirectoryHasher:
    @pytest.fixture
    def setup(self):
        print("初始化测试对象")
        self.QDH = QDirectoryHasher(None)
        yield
        del self.QDH
        print("删除测试对象")

    def test_function(self, setup):
        """测试主要功能"""
        test_path = os.path.join(TEST_DIR, "dataForTest\\")
        self.QDH.setDirectory(test_path)
        assert self.QDH.directory == test_path

        # 验证hash目录计算功能
        self.QDH._computeHash()
        while self.QDH.isRunning():
            time.sleep(0.1)
        res1 = calculateDirHash(test_path, "sha256")
        res2 = self.QDH.result
        for key in res1.keys():
            assert key in res2
            assert res1[key] == res2[key]


class TestHomeInterface:

    def test_exception(self, qtbot):
        """测试常见函数意外情况"""
        HI = HomeInterface(None)
        qtbot.addWidget(HI)
        with pytest.raises(NotImplementedError):
            HI.setHashAlgorithm("cyc")

    def test_start_button(self, qtbot):
        """测试开始按钮"""
        HI = HomeInterface(None)
        qtbot.addWidget(HI)
        # 测试设置目录功能
        HI.sec_input.setText(os.path.join(TEST_DIR, "dataForTester"))
        HI.sec_input.editingFinished.emit()
        assert HI.dirHasher.directory == HI.sec_input.displayText()
        # QFileDialog的模拟测试是不可能的
        # HI.openDirectoryFolder()
        # assert HI.dirHasher.directory == HI.sec_input.displayText()

        # 开始计算
        with qtbot.waitSignal(HI.dirHasher.completed, timeout=10000):
            HI.sec_input.setText(os.path.join(TEST_DIR, "dataForTest"))
            HI.sec_input.editingFinished.emit()
            qtbot.mouseClick(HI.start_button, Qt.MouseButton.LeftButton)
        assert len(HI.dirHasher.result) == 3
        # 测试空目录计算，不应该产生除数为0的问题
        HI.sec_input.setText(os.path.join(TEST_DIR, "empty"))
        HI.sec_input.editingFinished.emit()
        qtbot.mouseClick(HI.start_button, Qt.MouseButton.LeftButton)

        # 测试设置算法功能
        # 可以通过测试，因为不是通过模仿用户点击触发，所以意义不是很大
        # hash_algorithm_round_menu = HI.command_bar.findChild(RoundMenu, name="hash_algorithm_round_menu", options=Qt.FindChildOption.FindChildrenRecursively)
        # for i, alg in enumerate(HASH_ALGORITHM):
        #     hash_algorithm_round_menu.actions()[i].trigger()
        #     assert HI.dirHasher.hash_algorithm == alg
