import subprocess

def build():
    t1 = subprocess.Popen(["pyinstaller", "-F", "main.py"])
    t1.wait()
    t2 = subprocess.Popen(["pyinstaller", "-Fw", "main_ui.py"])
    t2.wait()

if __name__ == "__main__":
    build()