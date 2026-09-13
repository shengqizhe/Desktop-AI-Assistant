import os
import subprocess
import sys


def main():
    """用仓库根目录 .venv 启动 Coach。"""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    python_path = os.path.join(base_dir, ".venv", "Scripts", "python.exe")
    if not os.path.exists(python_path):
        python_path = sys.executable
    subprocess.check_call([python_path, "-m", "app.main"], cwd=base_dir)


if __name__ == "__main__":
    main()
