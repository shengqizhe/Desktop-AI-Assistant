import os
import sys
import shutil
import PyInstaller.__main__

# 解决某些环境下路径编码导致 Qt 插件加载失败的问题
if sys.platform == "win32":
    # 强制使用 UTF-8 编码处理路径
    os.environ["PYTHONIOENCODING"] = "utf-8"

def build():
    print("开始打包 desktop_pet_fluent.py ...")
    
    # 使用当前脚本所在目录
    base_dir = os.path.dirname(os.path.abspath(__file__))
    # 转换成 Windows 长路径格式以减少编码问题
    base_dir = os.path.normpath(base_dir)
    
    dist_dir = os.path.join(base_dir, "dist")
    
    # 清理旧的 dist 目录
    # if os.path.exists(dist_dir):
    #     shutil.rmtree(dist_dir)

    # PyInstaller 参数
    params = [
        os.path.join(base_dir, 'desktop_pet_fluent.py'), # 主程序文件
        '--name=皮皮桌面助手',                 # 生成的exe名称
        '--noconfirm',                        # 不确认覆盖
        '--windowed',                         # 不显示控制台窗口（GUI程序）
        '--clean',                            # 清理临时文件
        f'--distpath={dist_dir}',             # 输出目录
        '--workpath=./build',                 # 临时工作目录
        '--onefile',                          # 打包成单个 EXE 文件
        
        # 添加搜索路径（确保找到本地的 wxauto 等库）
        f'--paths={os.path.join(base_dir, "model", "wxauto-WeChat3.9.11")}',
        
        # 收集依赖库的数据文件（qfluentwidgets 需要特殊处理）
        '--collect-all=qfluentwidgets',
        '--collect-all=vosk',
        '--collect-all=langchain',
        '--collect-all=langchain_openai',
        '--collect-all=langchain_core',
        
        # 隐藏一些不需要的导入警告（可选）
        '--hidden-import=PyQt5.sip',
        '--hidden-import=engineio.async_drivers.threading',
        '--hidden-import=langchain_openai',
        '--hidden-import=langchain_core',
        '--hidden-import=wxauto',
        '--hidden-import=pyaudio',
        '--hidden-import=openai',
        '--hidden-import=pyttsx3',
        '--hidden-import=psutil',
    ]

    # 添加静态资源和模型文件 (格式: source;destination)
    resources = [
        ('knowledge', 'knowledge'),
        ('model', 'model'),
        ('public', 'public'),
        ('memory.db', '.'),
        ('requirements.txt', '.'),
    ]
    
    for src, dst in resources:
        src_full = os.path.join(base_dir, src)
        if os.path.exists(src_full):
            # Windows 下使用 ; 分隔
            params.append(f'--add-data={src}{os.pathsep}{dst}')
            print(f"已添加资源: {src} -> {dst}")
    
    # 如果有图标文件，添加图标
    icon_path = os.path.join(base_dir, "public", "皮皮.png")
    if os.path.exists(icon_path):
        params.append(f'--icon={icon_path}')
    elif os.path.exists(os.path.join(base_dir, "public", "logo.png")):
        params.append(f'--icon={os.path.join(base_dir, "public", "logo.png")}')

    # 运行 PyInstaller
    try:
        PyInstaller.__main__.run(params)
        print(f"打包完成！可执行文件位于: {os.path.join(dist_dir, '皮皮桌面助手.exe')}")
    except Exception as e:
        print(f"打包失败: {e}")

if __name__ == "__main__":
    build()
