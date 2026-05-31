import subprocess


def build():
    t1 = subprocess.Popen(["python", "-m", "nuitka", "--version"], shell=True)
    t2 = subprocess.Popen(["pyinstaller", "-F", "main.py"])
    t3 = subprocess.Popen(["pyinstaller", "-Fw", "main_ui.py"])

    # nuitka构建，没有cli是因为nuitka似乎无法处理AugmentParser模块
    # 构建ui结果比pyinstaller小一倍
    t1.wait()
    if t1.returncode == 0:
        print("nuitka worked success")
        t1 = subprocess.Popen(["python", "-m", "nuitka", "--standalone", "--onefile",
                              "--enable-plugin=pyside6", "--windows-console-mode=disable", "main_ui.py"], shell=True)
        t1.wait()

    # 采用pyinstaller构建ui和cli程序
    t2.wait()
    t3.wait()

    if t2.returncode != 0:
        print("cli compile failed")
        return
    if t3.returncode != 0:
        print("ui compile failed")
        return


if __name__ == "__main__":
    build()
