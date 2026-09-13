import os
import sys
import json
import subprocess
import shutil
from pathlib import Path
import subprocess as sp

def get_resource_path(relative_path):
    """ 获取打包进 EXE 内部的只读资源路径 """
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

def get_app_data_path(filename):
    """ 获取持久化数据路径（EXE 同级目录，实现绿色便携模式） """
    if hasattr(sys, '_MEIPASS'):
        base_path = os.path.dirname(sys.executable)
    else:
        base_path = os.path.abspath(".")
    
    data_dir = os.path.join(base_path, "data")
    target_path = Path(data_dir) / filename
    
    # 确保目标目录存在
    if not target_path.parent.exists():
        target_path.parent.mkdir(parents=True, exist_ok=True)
    
    # 如果目标文件不存在，但打包资源中存在初始模板，则从 EXE 内部复制出来
    if not target_path.exists():
        bundled_path = get_resource_path(str(filename))
        if os.path.exists(bundled_path):
            import shutil
            shutil.copy2(bundled_path, target_path)
    
    return target_path

try:
    import psutil
except Exception:
    psutil = None
try:
    import winreg
except ImportError:
    winreg = None

SYSTEM_START_MENU = r"C:\ProgramData\Microsoft\Windows\Start Menu\Programs"
USER_START_MENU = os.path.expandvars(r"%APPDATA%\Microsoft\Windows\Start Menu\Programs")

ALIASES = {
    "抖音": ["抖音", "TikTok"],
    "微信": ["微信", "WeChat"],
    "钉钉": ["钉钉", "DingTalk"],
    "qq": ["QQ", "qq"],
    "企业微信": ["企业微信", "WeCom"],
    "飞书": ["飞书", "Feishu", "Lark"],
    "浏览器": ["Chrome", "Google Chrome", "Microsoft Edge", "Edge", "Firefox", "火狐浏览器"],
    "永劫无间": ["永劫无间", "NARAKA", "NARAKA: BLADEPOINT", "Bladepoint"],
}

PROC_ALIASES = {
    "企业微信": ["WXWork.exe", "WeCom.exe"],
    "微信": ["WeChat.exe", "WeChatApp.exe"],
    "钉钉": ["DingTalk.exe"],
    "qq": ["QQ.exe", "QQ"],
    "抖音": ["TikTok.exe"],
    "飞书": ["Lark.exe", "Feishu.exe"],
    "浏览器": ["chrome.exe", "msedge.exe", "firefox.exe"],
    "永劫无间": ["NarakaBladePoint.exe", "NARAKABladePoint.exe", "naraka.exe"]
}

NORMALIZATION_MAP = {
    # 常见中文误写/同音
    "丁丁": "钉钉",
    "叮叮": "钉钉",
    "釘釘": "钉钉",
    "企微": "企业微信",
    "企业vx": "企业微信",
    "企业微信wecom": "企业微信",
    "wecom": "企业微信",
    "wxwork": "企业微信",
    "we work": "企业微信",
    "vx": "微信",
    "企鹅": "qq",
    # 英文/拼音归一
    "tiktok": "抖音",
    "douyin": "抖音",
    "lark": "飞书",
    "feishu": "飞书",
    # 游戏
    "naraka": "永劫无间",
    "naraka:bladepoint": "永劫无间",
    "bladepoint": "永劫无间",
}

COMMON_DIRS = [
    os.path.expandvars(r"%ProgramFiles%"),
    os.path.expandvars(r"%ProgramFiles(x86)%"),
    os.path.expandvars(r"%LOCALAPPDATA%\Programs"),
]

APPDATA_DIR = Path(os.path.expandvars(r"%APPDATA%")) / "XiaoZhuo"
APPDATA_DIR.mkdir(parents=True, exist_ok=True)
MAPPING_FILE = APPDATA_DIR / "app_mappings.json"

# 将 apps.json 也放到 APPDATA 目录下以实现持久化修改
KB_APPS_FILE = get_app_data_path(os.path.join("knowledge", "apps.json"))

def _load_mappings():
    try:
        if MAPPING_FILE.exists():
            with open(MAPPING_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return {k.lower(): v for k, v in data.items()}
    except Exception:
        pass
    return {}

def _load_kb_mappings():
    try:
        if KB_APPS_FILE.exists():
            with open(KB_APPS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    print(f"[应用启动] 已加载知识库映射: {KB_APPS_FILE}")
                    return {k.lower(): v for k, v in data.items()}
    except Exception:
        pass
    return {}

def _save_mappings(m):
    try:
        with open(MAPPING_FILE, "w", encoding="utf-8") as f:
            json.dump(m, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

def _save_kb_mappings(m):
    try:
        with open(KB_APPS_FILE, "w", encoding="utf-8") as f:
            json.dump(m, f, ensure_ascii=False, indent=2)
        print(f"[应用启动] 已保存知识库映射: {KB_APPS_FILE}")
    except Exception:
        pass

def register_app(app, exe_path):
    if not app or not exe_path:
        return False
    exe_path = os.path.expandvars(exe_path)
    if not os.path.isfile(exe_path):
        print(f"[应用启动] 注册失败（不是有效文件）: {exe_path}")
        return False
    app_key = app.lower()
    # 写入 KB
    kb = _load_kb_mappings()
    kb[app_key] = exe_path
    _save_kb_mappings(kb)
    print(f"[应用启动] 已注册 '{app_key}' -> {exe_path}（写入知识库）")
    # 同步到本地映射（兼容旧逻辑）
    m = _load_mappings()
    m[app_key] = exe_path
    _save_mappings(m)
    print(f"[应用启动] 已同步本地映射: '{app_key}'")
    return True

def get_mapped_path(app):
    app_key = app.lower()
    # 优先使用知识库中的映射
    kb = _load_kb_mappings()
    if app_key in kb:
        print(f"[应用启动] 知识库命中 '{app_key}': {kb[app_key]}")
        return kb[app_key]
    print(f"[应用启动] 知识库未命中 '{app_key}'，尝试本地映射")
    m = _load_mappings()
    return m.get(app_key)

def _candidate_names(app):
    names = [app]
    for k, v in ALIASES.items():
        if app.lower() == k.lower() or any(app.lower() == x.lower() for x in v):
            names.extend(v)
            names.append(k)
    return list(dict.fromkeys([n for n in names if n]))

def _find_in_registry(app):
    """
    通过注册表查找安装信息
    """
    if not winreg:
        return None
    
    names = _candidate_names(app)
    print(f"[应用启动] 在注册表中查找: {names}")
    
    # 需要遍历的注册表位置
    reg_paths = [
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Uninstall")
    ]
    
    for root_key, sub_key in reg_paths:
        try:
            with winreg.OpenKey(root_key, sub_key) as key:
                for i in range(winreg.QueryInfoKey(key)[0]):
                    try:
                        sub_key_name = winreg.EnumKey(key, i)
                        with winreg.OpenKey(key, sub_key_name) as sub_key_obj:
                            # 1. 检查 DisplayName
                            try:
                                display_name = winreg.QueryValueEx(sub_key_obj, "DisplayName")[0]
                                for n in names:
                                    if n.lower() in display_name.lower():
                                        # 尝试获取安装路径或卸载路径
                                        # 优先 InstallLocation
                                        try:
                                            install_loc = winreg.QueryValueEx(sub_key_obj, "InstallLocation")[0]
                                            if install_loc:
                                                # 猜测exe：通常在安装目录下有同名exe或主exe
                                                # 这里简单搜索一下目录下的exe
                                                install_path = _find_exe_in_dir(install_loc, names)
                                                if install_path:
                                                    print(f"[应用启动] 注册表(Uninstall)命中: {install_path}")
                                                    return install_path
                                        except OSError:
                                            pass
                                        
                                        # 其次 DisplayIcon
                                        try:
                                            display_icon = winreg.QueryValueEx(sub_key_obj, "DisplayIcon")[0]
                                            if display_icon:
                                                icon_path = display_icon.split(",")[0].strip('"')
                                                if icon_path.lower().endswith(".exe") and os.path.exists(icon_path):
                                                    print(f"[应用启动] 注册表(DisplayIcon)命中: {icon_path}")
                                                    return icon_path
                                        except OSError:
                                            pass
                            except OSError:
                                pass
                    except OSError:
                        continue
        except OSError:
            continue

    # 2. 检查 App Paths (HKLM)
    # HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths
    # key name 就是 exe 名字，例如 wechat.exe
    try:
        app_paths_key = r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths"
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, app_paths_key) as key:
            for i in range(winreg.QueryInfoKey(key)[0]):
                try:
                    exe_name = winreg.EnumKey(key, i)
                    # 检查 exe_name 是否包含我们的关键字
                    for n in names:
                        # 比如关键字是 "wechat"，exe_name 是 "wechat.exe"
                        if n.lower() in exe_name.lower():
                            with winreg.OpenKey(key, exe_name) as sub_key_obj:
                                try:
                                    # 默认值通常是完整路径
                                    full_path = winreg.QueryValue(sub_key_obj, None)
                                    if full_path and os.path.exists(full_path):
                                        print(f"[应用启动] 注册表(App Paths)命中: {full_path}")
                                        return full_path
                                except OSError:
                                    pass
                except OSError:
                    continue
    except OSError:
        pass

    return None

def _find_exe_in_dir(directory, names):
    """在指定目录下查找符合名称的exe（非递归，深度1）"""
    if not os.path.isdir(directory):
        return None
    # 优先精确匹配
    for f in os.listdir(directory):
        if not f.lower().endswith(".exe"): continue
        for n in names:
            if f.lower() == n.lower() or f.lower() == f"{n}.exe".lower():
                 return os.path.join(directory, f)
    # 其次模糊匹配
    for f in os.listdir(directory):
        if not f.lower().endswith(".exe"): continue
        for n in names:
            if n.lower() in f.lower():
                return os.path.join(directory, f)
    return None

def _find_in_known_paths(app):
    """
    检查常见软件的默认安装路径
    """
    names = _candidate_names(app)
    # 构造常见路径列表
    program_files = [
        os.environ.get("ProgramFiles", r"C:\Program Files"),
        os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"),
        os.path.expandvars(r"%LOCALAPPDATA%"),
        os.path.expandvars(r"%APPDATA%")
    ]
    
    # 常见软件及其子目录特征
    known_patterns = {
        "wechat": [r"Tencent\WeChat\WeChat.exe"],
        "qq": [r"Tencent\QQ\Bin\QQ.exe", r"Tencent\QQNT\QQ.exe"],
        "dingtalk": [r"DingDing\DingTalk\DingTalk.exe"],
        "feishu": [r"Lark\Lark.exe"],
        "lark": [r"Lark\Lark.exe"],
        "chrome": [r"Google\Chrome\Application\chrome.exe"],
        "edge": [r"Microsoft\Edge\Application\msedge.exe"],
        "firefox": [r"Mozilla Firefox\firefox.exe"],
        "douyin": [r"ByteDance\Douyin\Douyin.exe", r"Douyin\Douyin.exe"],
        # 常见发行渠道：Steam/NetEase Launcher/Naraka 独立安装
        "naraka": [
            r"Steam\steamapps\common\NARAKA BLADEPOINT\NarakaBladePoint.exe",
            r"NetEase\NarakaBladePoint\NarakaBladePoint.exe",
            r"NARAKA BLADEPOINT\NarakaBladePoint.exe"
        ],
    }
    
    # 检查是否有匹配的pattern
    matched_patterns = []
    for n in names:
        if n.lower() in known_patterns:
            matched_patterns.extend(known_patterns[n.lower()])
            
    # 如果没有特定的pattern，尝试通用的 Vendor/App 结构? 暂时不搞太复杂
    
    for base in program_files:
        for pattern in matched_patterns:
            full_path = os.path.join(base, pattern)
            if os.path.exists(full_path):
                print(f"[应用启动] 常见路径命中: {full_path}")
                return full_path
    return None

def _find_in_start_menu(app):
    names = _candidate_names(app)
    paths = [SYSTEM_START_MENU, USER_START_MENU]
    print(f"[应用启动] 在开始菜单中查找: {names}")
    for base in paths:
        if not os.path.isdir(base): 
            continue
        for root, _, files in os.walk(base):
            for f in files:
                if not f.lower().endswith(".lnk"):
                    continue
                for n in names:
                    if n.lower() in f.lower():
                        print(f"[应用启动] 开始菜单命中: {os.path.join(root, f)}")
                        return os.path.join(root, f)
    return None

def _find_exe_in_common_dirs(app):
    names = _candidate_names(app)
    print(f"[应用启动] 在常见目录中查找: {names}")
    for base in COMMON_DIRS:
        if not base or not os.path.isdir(base):
            continue
        for root, _, files in os.walk(base):
            for f in files:
                if not f.lower().endswith(".exe"):
                    continue
                for n in names:
                    if n.lower() in f.lower():
                        print(f"[应用启动] 常见目录命中: {os.path.join(root, f)}")
                        return os.path.join(root, f)
    return None

def _find_in_path(app):
    names = _candidate_names(app)
    print(f"[应用启动] 在 PATH 中查找: {names}")
    for n in names:
        p = shutil.which(n)
        if p:
            print(f"[应用启动] PATH 命中: {p}")
            return p
    return None

def launch_app(app):
    # 1) 知识库映射优先
    print(f"[应用启动] 启动请求: {app}")
    mapped = get_mapped_path(app)
    if mapped:
        if os.path.isfile(mapped):
            try:
                print(f"[应用启动] 从知识库路径启动: {mapped}")
                if mapped.lower().endswith(".lnk"):
                    os.startfile(mapped)
                else:
                    subprocess.Popen([mapped], cwd=os.path.dirname(mapped) or None)
                return True, mapped
            except Exception:
                print(f"[应用启动] 知识库路径启动失败: {mapped}")
                pass
        else:
             print(f"[应用启动] 知识库路径失效: {mapped}")
    
    # 2) 注册表查找 (New! Fast & Accurate)
    p = _find_in_registry(app)
    if p:
        try:
            print(f"[应用启动] 从注册表路径启动: {p}")
            subprocess.Popen([p], cwd=os.path.dirname(p) or None)
            register_app(app, p)
            return True, p
        except Exception:
            pass

    # 3) 常见默认路径 (New! Fast)
    p = _find_in_known_paths(app)
    if p:
        try:
            print(f"[应用启动] 从常见默认路径启动: {p}")
            subprocess.Popen([p], cwd=os.path.dirname(p) or None)
            register_app(app, p)
            return True, p
        except Exception:
            pass

    # 4) 开始菜单
    p = _find_in_start_menu(app)
    if p:
        try:
            print(f"[应用启动] 从开始菜单启动: {p}")
            os.startfile(p)
            # 写入知识库
            register_app(app, p)
            return True, p
        except Exception:
            print(f"[应用启动] 开始菜单启动失败: {p}")
            pass
    # 5) 常见安装目录
    p = _find_exe_in_common_dirs(app)
    if p:
        try:
            print(f"[应用启动] 从常见目录启动: {p}")
            subprocess.Popen([p], cwd=os.path.dirname(p) or None)
            register_app(app, p)
            return True, p
        except Exception:
            print(f"[应用启动] 常见目录启动失败: {p}")
            pass
    # 6) PATH
    p = _find_in_path(app)
    if p:
        try:
            print(f"[应用启动] 从 PATH 启动: {p}")
            subprocess.Popen([p], cwd=os.path.dirname(p) or None)
            register_app(app, p)
            return True, p
        except Exception:
            print(f"[应用启动] PATH 启动失败: {p}")
            pass
    print(f"[应用启动] 启动失败：未找到 '{app}' 的可执行文件")
    return False, None

def _candidate_proc_names(app):
    names = set()
    # 归一化处理（用于进程名推断）
    app = normalize_app_name(app)
    # 来自知识库路径
    p = get_mapped_path(app)
    if p and os.path.isfile(p):
        base = os.path.basename(p)
        names.add(base)
    # 来自进程别名
    for k, v in PROC_ALIASES.items():
        if app.lower() == k.lower():
            names.update(v)
    # 来自名称别名
    for n in _candidate_names(app):
        if n.lower().endswith(".exe"):
            names.add(n)
        else:
            names.add(n + ".exe")
    return list(names)

def close_app(app):
    print(f"[应用启动] 关闭请求: {app}")
    app = normalize_app_name(app)
    targets = _candidate_proc_names(app)
    print(f"[应用启动] 关闭目标进程名候选: {targets}")
    closed = 0
    if psutil:
        for proc in psutil.process_iter(["name", "exe", "cmdline"]):
            try:
                name = proc.info.get("name") or ""
                exe = proc.info.get("exe") or ""
                if any(name.lower() == t.lower() for t in targets) or \
                   any(exe.lower().endswith(t.lower()) for t in targets):
                    print(f"[应用启动] 尝试关闭进程: pid={proc.pid}, name={name}, exe={exe}")
                    proc.terminate()
                    try:
                        proc.wait(timeout=5)
                    except psutil.TimeoutExpired:
                        proc.kill()
                    closed += 1
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
    else:
        # Fallback: 使用 taskkill（可能需要管理员权限）
        for t in targets:
            try:
                sp.run(["taskkill", "/IM", t, "/T", "/F"], check=False, stdout=sp.DEVNULL, stderr=sp.DEVNULL)
                closed += 1
            except Exception:
                pass
    if closed > 0:
        print(f"[应用启动] 已关闭 {closed} 个相关进程。")
        return True
    print(f"[应用启动] 未找到可关闭的 '{app}' 进程。")
    return False

def normalize_app_name(app: str) -> str:
    """中文/英文误写归一化：去空白/符号、小写、查表替换"""
    if not app:
        return app
    s = app.strip().lower()
    for ch in [" ", "　", "·", "-", "_"]:
        s = s.replace(ch, "")
    # 直接匹配表
    if s in NORMALIZATION_MAP:
        return NORMALIZATION_MAP[s]
    # 组合关键字
    if "企业" in app and ("vx" in s or "wecom" in s or "wxwork" in s):
        return "企业微信"
    return app
