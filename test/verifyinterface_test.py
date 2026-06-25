import os
import time
from PySide6.QtCore import Qt

from src.ui.verify_interface import VerifyInterface

TEST_DIR = "./test/data"


class TestVerifyInterface:
    def test_start_button(self, qtbot):
        """测试开始按钮"""
        VI = VerifyInterface()
        qtbot.addWidget(VI)
        # 测试目录设置功能
        VI.sec_input.setText(os.path.join(TEST_DIR, "dataForTester"))
        VI.sec_input.editingFinished.emit()
        assert VI.dirHasher.directory == VI.sec_input.displayText()

        # 开始计算按钮
        with qtbot.waitSignal(VI.dirHasher.completed, timeout=10000):
            VI.sec_input.setText(os.path.join(TEST_DIR, "dataForTest"))
            VI.sec_input.editingFinished.emit()
            qtbot.mouseClick(VI.start_button, Qt.MouseButton.LeftButton)
        assert len(VI.dirHasher.error_list) == 0

    def test_modify_file(self, qtbot):
        """测试文件与校验和存在不一致"""
        VI = VerifyInterface()
        qtbot.addWidget(VI)
        VI.sec_input.setText(os.path.join(TEST_DIR, "verify"))
        VI.sec_input.editingFinished.emit()
        with qtbot.waitSignal(VI.dirHasher.completed, timeout=10000):
            qtbot.mouseClick(VI.start_button, Qt.MouseButton.LeftButton)
            time.sleep(0.1)  # 需要等待一定时间出校验结果，qtbot收到信号后似乎会终止线程执行
        assert len(VI.dirHasher.error_list) == 4
