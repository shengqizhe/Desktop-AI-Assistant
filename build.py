import os
import PyInstaller.__main__


def build():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    dist_dir = os.path.join(base_dir, "dist")
    qml_dir = os.path.join(base_dir, "app", "ui", "qml")

    params = [
        os.path.join(base_dir, "app", "main.py"),
        "--name=DesktopAICoach",
        "--noconfirm",
        "--windowed",
        "--clean",
        "--onefile",
        f"--distpath={dist_dir}",
        f"--workpath={os.path.join(base_dir, 'build')}",
        f"--paths={base_dir}",
        # QML 必须作为数据文件随包分发，否则运行时找不到界面
        f"--add-data={qml_dir}{os.pathsep}app/ui/qml",
        # PySide6 的 QML 插件与 Qt Quick 模块无法靠静态分析收全
        "--collect-all=PySide6",
        "--hidden-import=PySide6.QtQml",
        "--hidden-import=PySide6.QtQuick",
        "--hidden-import=mss",
    ]
    PyInstaller.__main__.run(params)
    print(f"Build complete: {os.path.join(dist_dir, 'DesktopAICoach.exe')}")


if __name__ == "__main__":
    build()
