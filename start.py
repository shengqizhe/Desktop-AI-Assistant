import os
import sys
import shutil
import subprocess
import time

def run_command(command, description):
    print(f"\n[INFO] 正在执行: {description}...")
    try:
        # 使用 shell=True 以便在 Windows 上正确运行
        result = subprocess.run(command, shell=True, check=True, capture_output=False)
        return True
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] 执行失败: {description}")
        print(f"[ERROR] 错误代码: {e.returncode}")
        return False

def main():
    # 获取当前脚本所在目录
    base_dir = os.path.dirname(os.path.abspath(__file__))
    venv_dir = os.path.join(base_dir, ".venv")
    requirements_file = os.path.join(base_dir, "requirements.txt")
    
    # 切换工作目录到脚本所在目录
    os.chdir(base_dir)

    # 1. 删除旧的虚拟环境
    if os.path.exists(venv_dir):
        print(f"[INFO] 发现旧的虚拟环境，正在删除: {venv_dir}")
        # 尝试多次删除，防止文件占用
        for i in range(3):
            try:
                shutil.rmtree(venv_dir)
                break
            except Exception as e:
                if i < 2:
                    print(f"[WARN] 删除失败，重试中 ({i+1}/3)...")
                    time.sleep(2)
                else:
                    print(f"[ERROR] 无法删除 .venv 文件夹，请确保没有程序正在使用它: {e}")
                    return

    # 2. 创建新的虚拟环境
    if not run_command(f"{sys.executable} -m venv .venv", "创建虚拟环境"):
        return

    # 3. 确定 pip 路径
    if sys.platform == "win32":
        pip_path = os.path.join(venv_dir, "Scripts", "pip.exe")
        python_path = os.path.join(venv_dir, "Scripts", "python.exe")
    else:
        pip_path = os.path.join(venv_dir, "bin", "pip")
        python_path = os.path.join(venv_dir, "bin", "python")

    # 4. 升级 pip
    run_command(f'"{python_path}" -m pip install --upgrade pip', "升级 pip")

    # 5. 安装依赖
    if os.path.exists(requirements_file):
        # 添加 numpy 到安装列表（如果 requirements.txt 里没有）
        # 这里直接安装 requirements.txt
        if not run_command(f'"{pip_path}" install -r requirements.txt', "安装 requirements.txt 中的依赖"):
            print("[ERROR] 依赖安装失败。")
            return
    else:
        print(f"[WARN] 未找到 {requirements_file}，将只安装基础库。")
        run_command(f'"{pip_path}" install numpy PyQt5 PyQt-Fluent-Widgets PyAudio', "安装基础依赖")

    print("\n" + "="*50)
    print("✨ 环境修复完成！")
    print(f"现在您可以使用以下命令启动程序：")
    print(f"1. 激活环境: .\\.venv\\Scripts\\Activate.ps1")
    print(f"2. 运行程序: python desktop_pet_fluent.py")
    print("="*50)

if __name__ == "__main__":
    main()
