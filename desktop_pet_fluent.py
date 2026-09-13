import sys
import os
def _setup_qt_plugin_path():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    venv_plugins = os.path.join(script_dir, ".venv", "Lib", "site-packages", "PyQt5", "Qt5", "plugins")
    if os.path.exists(venv_plugins):
        os.environ["QT_PLUGIN_PATH"] = venv_plugins
        if venv_plugins not in os.environ.get("PATH", ""):
            os.environ["PATH"] = venv_plugins + os.pathsep + os.environ.get("PATH", "")
    elif "QT_PLUGIN_PATH" not in os.environ:
        try:
            import PyQt5
            pyqt5_dir = os.path.dirname(PyQt5.__file__)
            plugins_path = os.path.join(pyqt5_dir, "Qt5", "plugins")
            if os.path.exists(plugins_path):
                os.environ["QT_PLUGIN_PATH"] = plugins_path
        except Exception:
            pass

_setup_qt_plugin_path()

import json
import time
import sqlite3
import threading
import queue
import datetime
import re
import pythoncom
import subprocess
import ctypes
import hashlib
import base64
import mimetypes
import shutil
import uuid
import traceback
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

# 设置 AppUserModelID 以确保任务栏图标正确显示
try:
    myappid = 'mycompany.desktop_pet.fluent.1.0'
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
except ImportError:
    pass

def get_resource_path(relative_path):
    """ 获取打包进 EXE 内部的只读资源路径 """
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), relative_path)

def get_windows_short_path(path: str) -> str:
    try:
        GetShortPathNameW = ctypes.windll.kernel32.GetShortPathNameW
    except Exception:
        return path
    if not path:
        return path
    try:
        buf = ctypes.create_unicode_buffer(32768)
        r = GetShortPathNameW(path, buf, len(buf))
        if r == 0:
            return path
        return buf.value
    except Exception:
        return path

def get_app_data_path(filename):
    """ 获取持久化数据路径（EXE 同级目录，实现绿色便携模式） """
    if hasattr(sys, '_MEIPASS'):
        base_path = os.path.dirname(sys.executable)
    else:
        base_path = os.path.abspath(".")
    
    # 确保数据目录存在
    data_dir = os.path.join(base_path, "data")
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
        
    target_path = os.path.join(data_dir, filename)
    
    # 如果数据文件不存在，但打包资源中存在初始模板，则从 EXE 内部复制出来
    if not os.path.exists(target_path):
        bundled_path = get_resource_path(filename)
        if os.path.exists(bundled_path):
            import shutil
            os.makedirs(os.path.dirname(target_path), exist_ok=True)
            shutil.copy2(bundled_path, target_path)
    
    return target_path

LOADING_GIF_FILE = get_resource_path(os.path.join("public", "小猫咪等待动画.gif"))

# 将下载的 wxauto 路径添加到系统路径
WXAUTO_PATH = get_resource_path(os.path.join("model", "wxauto-WeChat3.9.11"))
if os.path.exists(WXAUTO_PATH) and WXAUTO_PATH not in sys.path:
    sys.path.insert(0, WXAUTO_PATH)

# === 在导入 PyQt5 之前设置 Qt 插件路径 ===
# 这一步必须在导入 PyQt5 之前完成，否则 Qt 无法找到 Windows 平台插件
def _setup_qt_plugin_path_early():
    """在导入 PyQt5 之前设置 Qt 插件路径"""
    import site
    for site_path in site.getsitepackages():
        qt_plugins = os.path.join(site_path, "PyQt5", "Qt5", "plugins")
        if os.path.isdir(qt_plugins):
            platforms_dir = os.path.join(qt_plugins, "platforms")
            if os.path.isdir(platforms_dir):
                os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = get_windows_short_path(platforms_dir)
                break
        qt_plugins_alt = os.path.join(site_path, "PyQt5", "Qt", "plugins")
        if os.path.isdir(qt_plugins_alt):
            platforms_dir = os.path.join(qt_plugins_alt, "platforms")
            if os.path.isdir(platforms_dir):
                os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = get_windows_short_path(platforms_dir)
                break

_setup_qt_plugin_path_early()
# === Qt 插件路径设置完成 ===

from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QFrame, QSystemTrayIcon, QMenu, QFileDialog, QLabel, QListWidgetItem, QSlider, QGraphicsOpacityEffect, QDialog, QFormLayout, QDialogButtonBox, QCalendarWidget, QGridLayout, QPushButton, QLineEdit as NativeLineEdit, QShortcut, QSizePolicy
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QThread, QPoint, QSize, QUrl, QRect, QDate
from PyQt5.QtGui import QColor, QPainter, QBrush, QCursor, QFont, QIcon, QPixmap, QTransform, QDesktopServices, QPainterPath, QKeySequence, QImage, QMovie, QKeyEvent
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
from PyQt5.QtNetwork import QLocalServer, QLocalSocket

# 音乐模式模块
try:
    from music_mode import MusicModeWidget, MusicAuraOverlay, IOSToggleSwitch, AudioMonitorThread
    _MUSIC_MODE_AVAILABLE = True
except Exception as _music_import_err:
    _MUSIC_MODE_AVAILABLE = False
    print(f"[music_mode] 导入失败: {_music_import_err}")

# PyQt-Fluent-Widgets 引入
from qfluentwidgets import (FluentWindow, NavigationInterface, NavigationItemPosition, NavigationDisplayMode,
                             MessageBox, SubtitleLabel, setFont, LineEdit, TextEdit, 
                             PrimaryPushButton, ScrollArea, VerticalSeparator, 
                             CardWidget, BodyLabel, CaptionLabel, TransparentToolButton,
                             FluentIcon as FIF, SettingCardGroup, SwitchSettingCard, 
                             PushSettingCard, ExpandLayout, SettingCard, ComboBox, Slider,
                             ListWidget, SimpleCardWidget, Theme, setTheme,
                             InfoBar, InfoBarPosition)

class TextSettingCard(SettingCard):
    """ 自定义带文本输入框的设置卡片 """
    def __init__(self, icon, title, content=None, parent=None):
        super().__init__(icon, title, content, parent)
        self.lineEdit = LineEdit(self)
        self.lineEdit.setFixedWidth(200)
        self.hBoxLayout.addWidget(self.lineEdit, 0, Qt.AlignRight)
        self.hBoxLayout.addSpacing(16)

class OptionsSettingCard(SettingCard):
    """ 自定义带下拉框的设置卡片 """
    def __init__(self, icon, title, content=None, parent=None):
        super().__init__(icon, title, content, parent)
        self.comboBox = ComboBox(self)
        self.comboBox.setFixedWidth(200)
        self.hBoxLayout.addWidget(self.comboBox, 0, Qt.AlignRight)
        self.hBoxLayout.addSpacing(16)

class SliderSettingCard(SettingCard):
    """ 自定义带滑块的设置卡片 """
    def __init__(self, icon, title, content=None, parent=None):
        super().__init__(icon, title, content, parent)
        self.slider = Slider(Qt.Horizontal, self)
        self.slider.setFixedWidth(200)
        self.hBoxLayout.addWidget(self.slider, 0, Qt.AlignRight)
        self.hBoxLayout.addSpacing(16)

# 导入原有逻辑模块
from kb import KnowledgeBase
import app_launcher
import lc_engine
from music_mode import MusicModeWidget, MusicAuraOverlay, IOSToggleSwitch
try:
    import psutil
except Exception:
    psutil = None

# 情感分析模块
try:
    from emotion_analyzer import get_emotion_analyzer, analyze_user_emotion, generate_face_log as _generate_face_log
    _EMOTION_AVAILABLE = True
except Exception as _emotion_err:
    _EMOTION_AVAILABLE = False
    print(f"[情感分析] 导入失败: {_emotion_err}")
    def get_emotion_analyzer(api_key=None):
        return None
    def analyze_user_emotion(text):
        return {"dominant_emotion": "neutral", "dominant_score": 0.5}
    def _generate_face_log(api_key=None, output_path=None):
        return ""

def generate_face_log(api_key=None, output_path=None):
    return _generate_face_log(api_key, output_path)

# --- 核心逻辑工具函数 ---

def normalize_decimal_hours_time_expr(expr: str) -> str:
    s = str(expr or "")

    def repl(m: re.Match):
        hours = int(m.group(1))
        frac_digits = m.group(2) or "0"
        frac_value = int(frac_digits) / (10 ** len(frac_digits))
        minutes = int(round(frac_value * 60))
        if minutes >= 60:
            hours += minutes // 60
            minutes = minutes % 60
        has_after = bool(m.group(5))
        after = "后" if has_after else ""
        if hours <= 0 and minutes > 0:
            return f"{minutes}分钟{after}"
        if minutes <= 0:
            return f"{hours}小时{after}"
        return f"{hours}小时{minutes}分钟{after}"

    return re.sub(r"(\d+)\.(\d+)\s*(个)?(小?时|钟头)(后)?", repl, s)

def console_chat_log(role: str, text: str):
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    r = (role or "").strip().upper() or "CHAT"
    t = "" if text is None else str(text)
    lines = t.splitlines() if "\n" in t else [t]
    for line in lines:
        print(f"[CHAT][{ts}] {r}: {line}", flush=True)

_CHAT_VENDOR_OPTIONS = [
    "请选择厂商",
    "OpenAI",
    "Kimi (月之暗面)",
    "豆包",
    "通义千问",
    "DeepSeek",
    "智谱GLM",
    "文心一言",
    "腾讯混元",
    "自定义模型",
]

_CHAT_VENDOR_DEFAULT_BASE_URL = {
    "OpenAI": "https://api.openai.com/v1",
    "Kimi (月之暗面)": "https://api.moonshot.cn/v1",
    "豆包": "https://ark.cn-beijing.volces.com/api/v3",
    "通义千问": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    "DeepSeek": "https://api.deepseek.com/v1",
    "智谱GLM": "https://open.bigmodel.cn/api/paas/v4/",
    "文心一言": "https://qianfan.baidubce.com/v2",
    "腾讯混元": "https://api.hunyuan.cloud.tencent.com/v1",
}

_VISION_VENDOR_DEFAULT_BASE_URL = dict(_CHAT_VENDOR_DEFAULT_BASE_URL)

def _clean_base_url(raw: str) -> str:
    s = str(raw or "").strip()
    if not s:
        return ""
    s = s.strip().rstrip(";")
    m = re.search(r"https?://[^\s'\"`]+", s)
    if m:
        s = m.group(0)
    return s.strip().strip("'\"`").rstrip("/")

def _guess_chat_vendor(base_url: str, selected_vendor: str = "") -> str:
    v = str(selected_vendor or "").strip()
    if v and v != "请选择厂商":
        return v
    u = str(base_url or "").lower()
    if any(x in u for x in ("kimi", "moonshot")):
        return "Kimi (月之暗面)"
    if "dashscope" in u:
        return "通义千问"
    if "deepseek" in u:
        return "DeepSeek"
    if "bigmodel" in u or "zhipu" in u:
        return "智谱GLM"
    if "qianfan" in u or "baidubce" in u:
        return "文心一言"
    if "hunyuan" in u or "tencent" in u:
        return "腾讯混元"
    if "volces" in u or "ark.cn" in u:
        return "豆包"
    if "openai.com" in u:
        return "OpenAI"
    return ""

def _try_parse_json_from_text(text: str):
    s = str(text or "")
    i = s.find("{")
    j = s.rfind("}")
    if i == -1 or j == -1 or j <= i:
        return None
    frag = s[i : j + 1]
    try:
        return json.loads(frag)
    except Exception:
        return None

def _format_access_terminated_message(vendor: str, base_url: str, model: str, raw_error: str) -> str:
    v = str(vendor or "").strip()
    base = _clean_base_url(base_url)
    m = str(model or "").strip()
    data = _try_parse_json_from_text(raw_error) or {}
    err_obj = data.get("error") if isinstance(data, dict) else None
    err_msg = ""
    err_type = ""
    if isinstance(err_obj, dict):
        err_msg = str(err_obj.get("message") or "").strip()
        err_type = str(err_obj.get("type") or "").strip()
    msg_low = (err_msg or raw_error or "").lower()
    if ("access_terminated_error" not in (err_type or "")) and ("access_terminated_error" not in (raw_error or "")) and ("only available for coding agents" not in msg_low):
        return ""
    lines = []
    lines.append("⚠️ 当前模型暂时不可用，可能是权限或入口不匹配。")
    if err_msg:
        lines.append("原因：" + _sanitize_visible_text(err_msg))
    if v:
        lines.append(f"厂商：{v}")
    if m:
        lines.append("模型：" + _sanitize_visible_text(m))
    if base:
        lines.append("地址：" + _sanitize_visible_text(base))
    return "\n".join(lines).strip()

def _http_post_json(url: str, payload: dict, headers: dict, timeout: int = 120) -> str:
    req = Request(
        url=url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8")
    except HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {e.code}: {body}") from e
    except URLError as e:
        raise RuntimeError(f"网络错误：{e}") from e


def _iter_sse_events(resp):
    event_name = ""
    data_lines = []
    while True:
        raw_line = resp.readline()
        if not raw_line:
            break
        try:
            line = raw_line.decode("utf-8")
        except Exception:
            line = raw_line.decode("utf-8", errors="ignore")
        line = line.rstrip("\r\n")
        if line == "":
            if data_lines:
                yield event_name, "\n".join(data_lines)
            event_name = ""
            data_lines = []
            continue
        if line.startswith(":"):
            continue
        if line.startswith("event:"):
            event_name = line[6:].strip()
            continue
        if line.startswith("data:"):
            data_lines.append(line[5:].lstrip())
    if data_lines:
        yield event_name, "\n".join(data_lines)


def _http_post_stream(url: str, payload: dict, headers: dict, timeout: int = 120):
    req = Request(
        url=url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        return urlopen(req, timeout=timeout)
    except HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {e.code}: {body}") from e
    except URLError as e:
        raise RuntimeError(f"网络错误：{e}") from e

def _parse_openai_compatible_text(raw_body: str) -> str:
    data = json.loads(raw_body)
    if isinstance(data, dict) and isinstance(data.get("error"), dict):
        raise RuntimeError(data["error"].get("message") or raw_body)
    choices = (data.get("choices") or []) if isinstance(data, dict) else []
    if not choices:
        raise RuntimeError(f"响应缺少 choices：{raw_body}")
    c0 = choices[0] if isinstance(choices[0], dict) else {}
    msg = c0.get("message") if isinstance(c0, dict) else None
    if isinstance(msg, dict) and msg.get("content") is not None:
        return str(msg.get("content") or "")
    if c0.get("text") is not None:
        return str(c0.get("text") or "")
    raise RuntimeError(f"响应缺少 message.content：{raw_body}")

def _parse_anthropic_compatible_text(raw_body: str) -> str:
    data = json.loads(raw_body)
    if isinstance(data, dict) and isinstance(data.get("error"), dict):
        raise RuntimeError(data["error"].get("message") or raw_body)
    blocks = data.get("content") if isinstance(data, dict) else None
    if isinstance(blocks, list):
        parts = []
        for b in blocks:
            if isinstance(b, dict) and b.get("type") == "text" and b.get("text") is not None:
                parts.append(str(b.get("text") or ""))
        if parts:
            return "".join(parts)
    if isinstance(data, dict) and data.get("choices"):
        return _parse_openai_compatible_text(raw_body)
    raise RuntimeError(f"无法解析响应：{raw_body}")

def _chat_openai_compatible(api_key: str, base_url: str, model: str, messages: list, temperature: float = 0.7, max_tokens: int = 2000) -> str:
    base = _clean_base_url(base_url)
    if not base:
        raise RuntimeError("Base URL 为空")
    if base.endswith("/chat/completions"):
        url = base
    else:
        url = base + "/chat/completions"
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": False,
    }
    body = _http_post_json(
        url=url,
        payload=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )
    return _parse_openai_compatible_text(body).strip()


def _stream_openai_compatible(api_key: str, base_url: str, model: str, messages: list, temperature: float = 0.7, max_tokens: int = 2000):
    base = _clean_base_url(base_url)
    if not base:
        raise RuntimeError("Base URL 为空")
    url = base if base.endswith("/chat/completions") else (base + "/chat/completions")
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": True,
    }
    collected = []
    with _http_post_stream(
        url=url,
        payload=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    ) as resp:
        for _event_name, data in _iter_sse_events(resp):
            s = str(data or "").strip()
            if not s:
                continue
            if s == "[DONE]":
                break
            obj = json.loads(s)
            if isinstance(obj, dict) and isinstance(obj.get("error"), dict):
                raise RuntimeError(obj["error"].get("message") or s)
            choices = obj.get("choices") if isinstance(obj, dict) else None
            if not isinstance(choices, list) or not choices:
                continue
            delta = choices[0].get("delta") if isinstance(choices[0], dict) else None
            if isinstance(delta, dict):
                content = delta.get("content")
                if isinstance(content, str) and content:
                    collected.append(content)
                    yield content
    return "".join(collected).strip()

def _chat_anthropic_compatible(api_key: str, base_url: str, model: str, system_prompt: str, user_text: str, temperature: float = 0.7, max_tokens: int = 2000) -> str:
    base = _clean_base_url(base_url)
    if not base:
        raise RuntimeError("Base URL 为空")
    if base.endswith("/v1/messages"):
        url = base
    else:
        url = base + "/v1/messages"
    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": [{"type": "text", "text": str(user_text or "")}],
            }
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": False,
        "system": str(system_prompt or ""),
    }
    body = _http_post_json(
        url=url,
        payload=payload,
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        },
    )
    return _parse_anthropic_compatible_text(body).strip()


def _stream_anthropic_compatible(api_key: str, base_url: str, model: str, system_prompt: str, user_text: str, temperature: float = 0.7, max_tokens: int = 2000):
    base = _clean_base_url(base_url)
    if not base:
        raise RuntimeError("Base URL 为空")
    url = base if base.endswith("/v1/messages") else (base + "/v1/messages")
    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": [{"type": "text", "text": str(user_text or "")}],
            }
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": True,
        "system": str(system_prompt or ""),
    }
    collected = []
    with _http_post_stream(
        url=url,
        payload=payload,
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        },
    ) as resp:
        for event_name, data in _iter_sse_events(resp):
            s = str(data or "").strip()
            if not s:
                continue
            obj = json.loads(s)
            if event_name == "error":
                err = obj.get("error") if isinstance(obj, dict) else None
                if isinstance(err, dict):
                    raise RuntimeError(err.get("message") or s)
                raise RuntimeError(s)
            if not isinstance(obj, dict):
                continue
            if obj.get("type") == "content_block_delta":
                delta = obj.get("delta") or {}
                text_part = delta.get("text")
                if isinstance(text_part, str) and text_part:
                    collected.append(text_part)
                    yield text_part
    return "".join(collected).strip()

def chat_once_unified(api_key: str, base_url: str, model: str, system_prompt: str, user_text: str, selected_vendor: str = "") -> str:
    base = _clean_base_url(base_url)
    vendor = _guess_chat_vendor(base, selected_vendor)
    # 优先根据厂商选择 API 格式
    if vendor == "Kimi (月之暗面)":
        return _chat_anthropic_compatible(
            api_key=api_key,
            base_url=base,
            model=model,
            system_prompt=system_prompt,
            user_text=user_text,
        )
    # 其他情况使用 OpenAI 兼容格式
    return _chat_openai_compatible(
        api_key=api_key,
        base_url=base,
        model=model,
        messages=[
            {"role": "system", "content": str(system_prompt or "")},
            {"role": "user", "content": str(user_text or "")},
        ],
    )


def chat_stream_unified(api_key: str, base_url: str, model: str, system_prompt: str, user_text: str, selected_vendor: str = ""):
    base = _clean_base_url(base_url)
    vendor = _guess_chat_vendor(base, selected_vendor)
    if vendor == "Kimi (月之暗面)":
        yield from _stream_anthropic_compatible(
            api_key=api_key,
            base_url=base,
            model=model,
            system_prompt=system_prompt,
            user_text=user_text,
        )
        return
    yield from _stream_openai_compatible(
        api_key=api_key,
        base_url=base,
        model=model,
        messages=[
            {"role": "system", "content": str(system_prompt or "")},
            {"role": "user", "content": str(user_text or "")},
        ],
    )

def _vision_messages_openai(prompt: str, image_data_url: str) -> list:
    p = str(prompt or "").strip()
    if not p:
        p = "请用中文简洁描述这张图片里有什么。只输出识别到的内容，不要额外解释。"
    return [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": p},
                {"type": "image_url", "image_url": {"url": str(image_data_url or "")}},
            ],
        }
    ]

def _vision_openai_compatible(api_key: str, base_url: str, model: str, prompt: str, image_data_url: str, timeout: int = 120) -> str:
    base = _clean_base_url(base_url)
    if not base:
        raise RuntimeError("Base URL 为空")
    url = base + "/chat/completions" if not base.endswith("/chat/completions") else base
    payload = {
        "model": str(model or ""),
        "messages": _vision_messages_openai(prompt, image_data_url),
        "temperature": 0.2,
        "max_tokens": 2000,
        "stream": False,
    }
    body = _http_post_json(
        url=url,
        payload=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        timeout=timeout,
    )
    return _parse_openai_compatible_text(body).strip()

def _parse_image_data_url(image_data_url: str) -> tuple[str, str]:
    s = str(image_data_url or "").strip()
    m = re.match(r"^data:([^;]+);base64,(.*)$", s, flags=re.I | re.S)
    if not m:
        raise RuntimeError("图片数据格式错误")
    mime_type = str(m.group(1) or "").strip() or "image/jpeg"
    b64_data = str(m.group(2) or "").strip()
    if not b64_data:
        raise RuntimeError("图片数据为空")
    return mime_type, b64_data

def _vision_anthropic_compatible(api_key: str, base_url: str, model: str, prompt: str, image_data_url: str, timeout: int = 120) -> str:
    base = _clean_base_url(base_url)
    if not base:
        raise RuntimeError("Base URL 为空")
    if base.endswith("/v1/messages"):
        url = base
    else:
        url = base + "/v1/messages"
    p = str(prompt or "").strip()
    if not p:
        p = """请先判断图片内容类型：

如果是题目（选择题、填空题、判断题、问答题、计算题等）：
1. 第一行直接给出答案（如"答案是A"、"答案是xx"、"正确/错误"）
2. 第二行空行
3. 第三行开始给出简要解释

如果不是题目（普通图片、照片、截图等）：
请用中文详细描述这张图片里有什么。尽可能全面地识别图片中的各种元素、人物、场景、物品、颜色、动作等细节。

注意：只输出识别到的内容，不要提及"识别/解析/多模态/模型"等后台词。"""
    mime_type, b64_data = _parse_image_data_url(image_data_url)
    payload = {
        "model": str(model or ""),
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": p},
                    {"type": "image", "source": {"type": "base64", "media_type": mime_type, "data": b64_data}},
                ],
            }
        ],
        "temperature": 0.2,
        "max_tokens": 2000,
        "stream": False,
    }
    body = _http_post_json(
        url=url,
        payload=payload,
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        },
        timeout=timeout,
    )
    return _parse_anthropic_compatible_text(body).strip()

def vision_recognize_unified(api_key: str, base_url: str, model: str, prompt: str, image_data_url: str, selected_vendor: str = "") -> str:
    base = _clean_base_url(base_url)
    vendor = _guess_chat_vendor(base, selected_vendor)
    # 优先根据厂商选择 API 格式
    if vendor == "Kimi (月之暗面)":
        return _vision_anthropic_compatible(
            api_key=api_key,
            base_url=base,
            model=model,
            prompt=prompt,
            image_data_url=image_data_url,
        )
    # 其他情况使用 OpenAI 兼容格式
    return _vision_openai_compatible(
        api_key=api_key,
        base_url=base,
        model=model,
        prompt=prompt,
        image_data_url=image_data_url,
    )

def parse_natural_time_expression_to_datetime(time_expr: str) -> datetime.datetime:
    print(f"[TimeParser] 原始输入: {time_expr}")
    now = datetime.datetime.now()
    target_datetime = now
    normalized_decimal = normalize_decimal_hours_time_expr(time_expr)
    if normalized_decimal != str(time_expr or ""):
        print(f"[TimeParser] 小数小时换算: {normalized_decimal}")
        time_expr = normalized_decimal
    def _is_duration_like(expr: str) -> bool:
        s = re.sub(r"\s+", "", str(expr or ""))
        if not s:
            return False
        if any(x in s for x in ("月", "日", "号", "今天", "明天", "后天")):
            return False
        if re.search(r"[:：点]", s):
            return False
        if re.search(r"(小?时|钟头|分(钟)?|秒(钟)?|半)", s):
            return True
        return False

    def _parse_duration_seconds(expr: str):
        s = str(expr or "")
        s = re.sub(r"\s+", "", s)
        if not s:
            return None

        total = 0.0
        m_half = re.search(r"(\d+)\s*(个)?半\s*(小?时|钟头)", s)
        if m_half:
            n = int(m_half.group(1))
            total += (n + 0.5) * 3600
            s = s.replace(m_half.group(0), "")

        m_h_half = re.search(r"(\d+(?:\.\d+)?)\s*(个)?(小?时|钟头)\s*半", s)
        if m_h_half:
            hours = float(m_h_half.group(1))
            total += hours * 3600 + 1800
            s = s.replace(m_h_half.group(0), "")

        s = s.replace("半小时", "30分钟").replace("半钟头", "30分钟").replace("半分钟", "30秒")

        for m in re.finditer(r"(\d+(?:\.\d+)?)\s*(个)?(小?时|钟头)", s):
            total += float(m.group(1)) * 3600
        s2 = re.sub(r"(\d+(?:\.\d+)?)\s*(个)?(小?时|钟头)", "", s)
        for m in re.finditer(r"(\d+)\s*分(钟)?", s2):
            total += int(m.group(1)) * 60
        s3 = re.sub(r"(\d+)\s*分(钟)?", "", s2)
        for m in re.finditer(r"(\d+)\s*秒(钟)?", s3):
            total += int(m.group(1))

        if total <= 0:
            return None
        return int(total)

    if _is_duration_like(time_expr):
        seconds = _parse_duration_seconds(time_expr)
        if seconds is not None:
            if "后" in str(time_expr) or re.fullmatch(r"[\d\.个小时钟头分秒半\s]+", str(time_expr)):
                print(f"[TimeParser] 匹配到相对时长: {seconds}秒")
                return now + datetime.timedelta(seconds=seconds)
    
    # 简单优化中文数字替换顺序
    cn_map = {
        '十二': '12', '十一': '11', '十': '10', 
        '零': '0', '一': '1', '二': '2', '两': '2', '三': '3', '四': '4', 
        '五': '5', '六': '6', '七': '7', '八': '8', '九': '9'
    }
    for k, v in cn_map.items(): time_expr = time_expr.replace(k, v)
    
    print(f"[TimeParser] 归一化后: {time_expr}")

    if _is_duration_like(time_expr):
        seconds = _parse_duration_seconds(time_expr)
        if seconds is not None:
            if "后" in str(time_expr) or re.fullmatch(r"[\d\.个小时钟头分秒半\s]+", str(time_expr)):
                print(f"[TimeParser] 匹配到相对时长: {seconds}秒")
                return now + datetime.timedelta(seconds=seconds)

    match_hm = re.search(r"(\d+(?:\.\d+)?)\s*(个)?(小?时|钟头)\s*(\d+)\s*分(钟)?后", time_expr)
    if match_hm:
        hours = float(match_hm.group(1))
        minutes = int(match_hm.group(4))
        print(f"[TimeParser] 匹配到复合相对时间: {hours}小时{minutes}分钟后")
        return now + datetime.timedelta(seconds=int(hours * 3600 + minutes * 60))

    match_hms = re.search(r"(\d+(?:\.\d+)?)\s*(个)?(小?时|钟头)\s*(\d+)\s*分(钟)?\s*(\d+)\s*秒(钟)?后", time_expr)
    if match_hms:
        hours = float(match_hms.group(1))
        minutes = int(match_hms.group(4))
        seconds = int(match_hms.group(6))
        print(f"[TimeParser] 匹配到复合相对时间: {hours}小时{minutes}分钟{seconds}秒后")
        return now + datetime.timedelta(seconds=int(hours * 3600 + minutes * 60 + seconds))

    match_ms = re.search(r"(\d+)\s*分(钟)?\s*(\d+)\s*秒(钟)?后", time_expr)
    if match_ms:
        minutes = int(match_ms.group(1))
        seconds = int(match_ms.group(3))
        print(f"[TimeParser] 匹配到复合相对时间: {minutes}分钟{seconds}秒后")
        return now + datetime.timedelta(seconds=int(minutes * 60 + seconds))

    match_min = re.search(r"(\d+)\s*分(钟)?后", time_expr)
    if match_min: 
        print(f"[TimeParser] 匹配到分钟相对时间: {match_min.group(1)}分钟后")
        return now + datetime.timedelta(minutes=int(match_min.group(1)))
        
    match_sec = re.search(r"(\d+)\s*秒(钟)?后", time_expr)
    if match_sec: 
        print(f"[TimeParser] 匹配到秒相对时间: {match_sec.group(1)}秒后")
        return now + datetime.timedelta(seconds=int(match_sec.group(1)))

    match_hour = re.search(r"(\d+(?:\.\d+)?)\s*(个)?(小?时|钟头)\s*后", time_expr)
    if match_hour:
        hours = float(match_hour.group(1))
        print(f"[TimeParser] 匹配到小时相对时间: {hours}小时后")
        return now + datetime.timedelta(seconds=int(hours * 3600))

    md = re.search(r"(\d{1,2})\s*月\s*(\d{1,2})\s*(号|日)?", time_expr)
    if md:
        m = int(md.group(1))
        d = int(md.group(2))
        year = now.year
        try:
            dt = datetime.datetime(year, m, d, 9, 0, 0)
        except ValueError:
            dt = now
        ampm = None
        if "早上" in time_expr or "上午" in time_expr: ampm = "am"
        if "中午" in time_expr: ampm = "noon"
        if "下午" in time_expr or "晚上" in time_expr: ampm = "pm"
        hhmm = re.search(r"(\d{1,2})[:：](\d{2})", time_expr)
        if hhmm:
            h, m2 = int(hhmm.group(1)), int(hhmm.group(2))
            if ampm == "pm" and h < 12: h += 12
            if ampm == "noon": h = 12
            if ampm == "am" and h == 12: h = 0
            dt = dt.replace(hour=h, minute=m2, second=0, microsecond=0)
        else:
            mh = re.search(r"(\d{1,2})\s*点(半|(\d{2})分?)?", time_expr)
            if mh:
                h = int(mh.group(1))
                if ampm == "pm" and h < 12: h += 12
                if ampm == "noon": h = 12
                mm = 30 if mh.group(2) and "半" in mh.group(2) else (int(mh.group(2)) if mh.group(2) and mh.group(2).isdigit() else 0)
                dt = dt.replace(hour=h, minute=mm, second=0, microsecond=0)
            else:
                if ampm == "noon": dt = dt.replace(hour=12, minute=0, second=0, microsecond=0)
                elif ampm == "pm": dt = dt.replace(hour=15, minute=0, second=0, microsecond=0)
                elif ampm == "am": dt = dt.replace(hour=9, minute=0, second=0, microsecond=0)
        if dt <= now:
            try:
                dt = datetime.datetime(year + 1, dt.month, dt.day, dt.hour, dt.minute, 0, 0)
            except Exception:
                dt = dt + datetime.timedelta(days=365)
        print(f"[TimeParser] 匹配到月日时间 -> {dt}")
        return dt
        
    # 如果不含“点/:/：”，尝试匹配纯数字的分钟/秒（视为相对时间）
    if not re.search(r"[:：点]", time_expr):
        match_hour_pure = re.search(r"(\d+(?:\.\d+)?)\s*(个)?(小?时|钟头)", time_expr)
        if match_hour_pure:
            hours = float(match_hour_pure.group(1))
            print(f"[TimeParser] 匹配到纯小时相对时间: {hours}小时")
            return now + datetime.timedelta(seconds=int(hours * 3600))
        match_min_pure = re.search(r"(\d+)\s*分(钟)?", time_expr)
        if match_min_pure:
            print(f"[TimeParser] 匹配到纯分钟相对时间: {match_min_pure.group(1)}分钟")
            return now + datetime.timedelta(minutes=int(match_min_pure.group(1)))
        match_sec_pure = re.search(r"(\d+)\s*秒(钟)?", time_expr)
        if match_sec_pure:
            print(f"[TimeParser] 匹配到纯秒相对时间: {match_sec_pure.group(1)}秒")
            return now + datetime.timedelta(seconds=int(match_sec_pure.group(1)))
            
    day_offset = 0
    if "明天" in time_expr: day_offset = 1
    elif "后天" in time_expr: day_offset = 2
    target_datetime += datetime.timedelta(days=day_offset)
    
    match_hhmm = re.search(r"(\d{1,2})[:：](\d{2})", time_expr)
    if match_hhmm:
        h, m = int(match_hhmm.group(1)), int(match_hhmm.group(2))
        print(f"[TimeParser] 匹配到绝对时间 HH:MM -> {h}:{m}")
        target_datetime = target_datetime.replace(hour=h, minute=m, second=0, microsecond=0)
    else:
        default_hour = target_datetime.hour
        if "早上" in time_expr: default_hour = 9
        elif "中午" in time_expr: default_hour = 12
        elif "下午" in time_expr: default_hour = 15
        elif "晚上" in time_expr: default_hour = 20
        
        match_hour = re.search(r"(\d{1,2})\s*点", time_expr)
        if match_hour:
            h = int(match_hour.group(1))
            if ("下午" in time_expr or "晚上" in time_expr) and h < 12: h += 12
            default_hour = h
            print(f"[TimeParser] 匹配到小时点 -> {default_hour}点")
        
        # 如果没有匹配到具体分钟，保留当前分钟（或者设为0？通常设为0更合理，比如“明天下午3点”）
        # 原逻辑是保留当前分钟，这里保持原样，但如果是相对小时呢？
        # 如果只说了“下午3点”，通常意味着 15:00:00，而不是 15:08:00
        # 所以如果匹配到了小时，应该把分钟清零
        if match_hour:
             target_datetime = target_datetime.replace(hour=default_hour, minute=0, second=0, microsecond=0)
        else:
             # 如果连小时都没匹配到（且不是相对时间），那可能是解析失败，或者只有日期
             target_datetime = target_datetime.replace(hour=default_hour, minute=target_datetime.minute, second=0, microsecond=0)

    if target_datetime < now and (now - target_datetime).total_seconds() > 120:
        if day_offset == 0: 
            print("[TimeParser] 目标时间已过，自动加一天")
            target_datetime += datetime.timedelta(days=1)
            
    print(f"[TimeParser] 最终解析结果: {target_datetime}")
    return target_datetime

def normalize_birthday_value(value: str) -> str:
    """将生日的自然语言值归一化为 'M月D日'，支持 昨天/今天/明天/后天、YYYY-MM-DD、MM-DD、M/D、4月2号 等"""
    v = value.strip()
    now = datetime.datetime.now()
    # 相对日
    rel = {"昨天": -1, "今天": 0, "明天": 1, "后天": 2}
    if v in rel:
        dt = now + datetime.timedelta(days=rel[v])
        return f"{dt.month}月{dt.day}日"
    # YYYY-MM-DD
    m = re.match(r"^\s*(\d{4})-(\d{1,2})-(\d{1,2})\s*$", v)
    if m:
        _, mm, dd = m.groups()
        return f"{int(mm)}月{int(dd)}日"
    # MM-DD 或 M-D
    m = re.match(r"^\s*(\d{1,2})-(\d{1,2})\s*$", v)
    if m:
        mm, dd = m.groups()
        return f"{int(mm)}月{int(dd)}日"
    # M/D 或 MM/DD
    m = re.match(r"^\s*(\d{1,2})/(\d{1,2})\s*$", v)
    if m:
        mm, dd = m.groups()
        return f"{int(mm)}月{int(dd)}日"
    # 4月2号 / 4月2日
    m = re.search(r"(\d{1,2})\s*月\s*(\d{1,2})\s*(号|日)?", v)
    if m:
        mm, dd = m.group(1), m.group(2)
        return f"{int(mm)}月{int(dd)}日"
    return v

def normalize_voice_text(s: str) -> str:
    def to_halfwidth(text):
        res = []
        for ch in text:
            code = ord(ch)
            if code == 0x3000: res.append(' ')
            elif 0xFF01 <= code <= 0xFF5E: res.append(chr(code - 0xFEE0))
            else: res.append(ch)
        return ''.join(res)
    t = to_halfwidth(s)
    t = re.sub(r"\s+", " ", t).strip()
    pairs_cn = [("丁丁", "钉钉"), ("叮叮", "钉钉"), ("企微", "企业微信"), ("企鹅", "QQ"), ("v 信", "微信"), ("微 信", "微信")]
    for a, b in pairs_cn: t = t.replace(a, b)
    def ci(p, r, x): return re.sub(p, r, x, flags=re.I)
    t = ci(r"\bwecom\b", "企业微信", t); t = ci(r"\bwxwork\b", "企业微信", t); t = ci(r"\bwe\s*work\b", "企业微信", t)
    t = ci(r"\btiktok\b", "抖音", t); t = ci(r"\bdouyin\b", "抖音", t); t = ci(r"\blark\b", "飞书", t); t = ci(r"\bfeishu\b", "飞书", t)
    t = ci(r"\bvx\b", "微信", t); t = ci(r"\bwechat\b", "微信", t)
    return t

# --- 线程支持检测 ---
try:
    import pyaudio
    from vosk import Model, KaldiRecognizer
    VOICE_SUPPORT = True
except ImportError:
    VOICE_SUPPORT = False

try:
    from wxauto import WeChat
    WX_SUPPORT = True
except ImportError:
    WX_SUPPORT = False

# 全局微信操作锁
wx_lock = threading.Lock()

# ================= 配置 =================
DB_FILE = get_app_data_path("memory.db")
APP_DATA_DIR = os.path.dirname(DB_FILE)
ALARM_FILE = get_resource_path(os.path.join("model", "alarm.mp3"))
VOSK_PATH = get_resource_path("model")
CHAT_LOG_FILE = get_app_data_path("chat_history.log")
from openai import OpenAI
import pyttsx3

# --- 数据库管理 (全功能保留) ---
class DBManager:
    def __init__(self):
        self.conn = sqlite3.connect(DB_FILE, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self._lock = threading.Lock()
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS tasks 
                               (id INTEGER PRIMARY KEY, time TEXT, content TEXT, status TEXT, timestamp TEXT, update_time TEXT)''')
        
        # 尝试为旧 tasks 表添加 update_time 列
        try:
            self.cursor.execute("ALTER TABLE tasks ADD COLUMN update_time TEXT")
        except sqlite3.OperationalError:
            pass

        self.cursor.execute('''CREATE TABLE IF NOT EXISTS memos
                               (key TEXT PRIMARY KEY, value TEXT, timestamp TEXT, update_time TEXT)''')
        
        # 尝试为旧 memos 表添加 update_time 列
        try:
            self.cursor.execute("ALTER TABLE memos ADD COLUMN update_time TEXT")
        except sqlite3.OperationalError:
            pass

        self.cursor.execute('''CREATE TABLE IF NOT EXISTS settings
                               (key TEXT PRIMARY KEY, value TEXT)''')
                               
        # 新建：修改记录表
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS task_history
                               (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                                task_id INTEGER, 
                                old_time TEXT, 
                                new_time TEXT, 
                                old_content TEXT, 
                                new_content TEXT, 
                                modify_time TEXT)''')
        
        # 新建：备忘录修改记录表
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS memo_history
                               (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                                memo_key TEXT, 
                                old_value TEXT, 
                                new_value TEXT, 
                                original_time TEXT, 
                                modify_time TEXT)''')

        # 新建：删除记录表
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS task_deleted
                               (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                                original_task_id INTEGER, 
                                content TEXT, 
                                delete_time TEXT,
                                original_time TEXT)''')
        
        # 新建：备忘录删除记录表
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS memo_deleted
                               (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                                memo_key TEXT, 
                                value TEXT, 
                                delete_time TEXT,
                                record_time TEXT)''')

        # 新建：对话管理表（替代旧的chat_history）
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS conversations
                               (id INTEGER PRIMARY KEY AUTOINCREMENT,
                                title TEXT,
                                created_at TEXT,
                                updated_at TEXT,
                                messages TEXT,
                                is_active INTEGER DEFAULT 0)''')
        
        # 保留旧表用于兼容（如果存在）
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS chat_history
                               (id INTEGER PRIMARY KEY AUTOINCREMENT,
                                user_text TEXT,
                                ai_text TEXT,
                                user_type TEXT,
                                ai_type TEXT,
                                user_media_rel_path TEXT,
                                ai_media_rel_path TEXT,
                                created_at TEXT)''')
        try:
            self.cursor.execute("ALTER TABLE chat_history ADD COLUMN user_type TEXT")
        except sqlite3.OperationalError:
            pass
        try:
            self.cursor.execute("ALTER TABLE chat_history ADD COLUMN ai_type TEXT")
        except sqlite3.OperationalError:
            pass
        try:
            self.cursor.execute("ALTER TABLE chat_history ADD COLUMN user_media_rel_path TEXT")
        except sqlite3.OperationalError:
            pass
        try:
            self.cursor.execute("ALTER TABLE chat_history ADD COLUMN ai_media_rel_path TEXT")
        except sqlite3.OperationalError:
            pass

        self.cursor.execute('''CREATE TABLE IF NOT EXISTS image_recognitions
                               (id INTEGER PRIMARY KEY AUTOINCREMENT,
                                source TEXT,
                                original_path TEXT,
                                saved_rel_path TEXT,
                                image_sha256 TEXT,
                                prompt TEXT,
                                recognized_text TEXT,
                                model TEXT,
                                created_at TEXT)''')
        self.conn.commit()

    def set_setting(self, key, value):
        with self._lock:
            self.cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, str(value)))
            self.conn.commit()

    def get_setting(self, key, default_value=None):
        with self._lock:
            self.cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
            result = self.cursor.fetchone()
            return result[0] if result else default_value

    def add_task(self, time_str, content):
        current_timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        print(f"[DB] Inserting task: time={time_str}, content={content}")
        try:
            with self._lock:
                self.cursor.execute("INSERT INTO tasks (time, content, status, timestamp) VALUES (?, ?, ?, ?)", 
                                    (time_str, content, 'pending', current_timestamp))
                self.conn.commit()
            print("[DB] Insert successful")
        except Exception as e:
            print(f"[DB] Insert failed: {e}")

    def update_task(self, task_id, new_time_str, new_content):
        """更新任务并记录历史"""
        with self._lock:
            self.cursor.execute("SELECT time, content FROM tasks WHERE id = ?", (task_id,))
            res = self.cursor.fetchone()
        if not res: return False
        
        old_time, old_content = res
        current_time = time.strftime("%Y-%m-%d %H:%M:%S")

        with self._lock:
            self.cursor.execute('''INSERT INTO task_history 
                                   (task_id, old_time, new_time, old_content, new_content, modify_time) 
                                   VALUES (?, ?, ?, ?, ?, ?)''', 
                                   (task_id, old_time, new_time_str, old_content, new_content, current_time))
            
            self.cursor.execute("UPDATE tasks SET time = ?, content = ?, update_time = ? WHERE id = ?", 
                                (new_time_str, new_content, current_time, task_id))
            self.conn.commit()
        return True

    def delete_task_with_log(self, task_id):
        """删除任务并记录到删除表"""
        with self._lock:
            self.cursor.execute("SELECT content, time FROM tasks WHERE id = ?", (task_id,))
            res = self.cursor.fetchone()
        if not res: return False
        
        content, original_time = res
        current_time = time.strftime("%Y-%m-%d %H:%M:%S")

        with self._lock:
            self.cursor.execute("INSERT INTO task_deleted (original_task_id, content, delete_time, original_time) VALUES (?, ?, ?, ?)", 
                                (task_id, content, current_time, original_time))
            
            self.cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
            self.conn.commit()
        return True

    def get_pending_tasks(self):
        self.cursor.execute("SELECT id, time, content FROM tasks WHERE status = 'pending'")
        all_tasks = self.cursor.fetchall()
        trigger_tasks = []
        now = datetime.datetime.now()
        current_hhmm = now.strftime("%H:%M")
        for t_id, t_time, content in all_tasks:
            try:
                if len(t_time) > 10 and "-" in t_time:
                     t_dt = datetime.datetime.strptime(t_time, "%Y-%m-%d %H:%M:%S")
                     if t_dt <= now: trigger_tasks.append((t_id, content))
                elif ":" in t_time and t_time.strip() == current_hhmm:
                    trigger_tasks.append((t_id, content))
            except: continue
        return trigger_tasks

    def mark_done(self, task_id):
        with self._lock:
            self.cursor.execute("UPDATE tasks SET status = 'done' WHERE id = ?", (task_id,))
            self.conn.commit()

    def add_memo(self, key, value):
        current_timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        with self._lock:
            self.cursor.execute("INSERT OR REPLACE INTO memos (key, value, timestamp) VALUES (?, ?, ?)", (key, value, current_timestamp))
            self.conn.commit()
        
    def update_memo(self, key, new_value):
        """更新备忘录并记录历史"""
        with self._lock:
            self.cursor.execute("SELECT value, timestamp, update_time FROM memos WHERE key = ?", (key,))
            res = self.cursor.fetchone()
        if not res: return False
        
        old_value, create_time, last_update_time = res
        original_time = last_update_time if last_update_time else create_time
        current_time = time.strftime("%Y-%m-%d %H:%M:%S")
        
        with self._lock:
            self.cursor.execute('''INSERT INTO memo_history 
                                   (memo_key, old_value, new_value, original_time, modify_time) 
                                   VALUES (?, ?, ?, ?, ?)''',
                                   (key, old_value, new_value, original_time, current_time))
                                   
            self.cursor.execute("UPDATE memos SET value = ?, update_time = ? WHERE key = ?", (new_value, current_time, key))
            self.conn.commit()
        return True

    def delete_memo_with_log(self, key):
        """删除备忘录并记录到删除表"""
        with self._lock:
            self.cursor.execute("SELECT value, timestamp, update_time FROM memos WHERE key = ?", (key,))
            res = self.cursor.fetchone()
        if not res: return False
        
        value, create_time, last_update_time = res
        record_time = last_update_time if last_update_time else create_time
        current_time = time.strftime("%Y-%m-%d %H:%M:%S")
        
        with self._lock:
            self.cursor.execute('''INSERT INTO memo_deleted
                                   (memo_key, value, delete_time, record_time)
                                   VALUES (?, ?, ?, ?)''',
                                   (key, value, current_time, record_time))
                                   
            self.cursor.execute("DELETE FROM memos WHERE key = ?", (key,))
            self.conn.commit()
        return True

    def get_all_memos(self):
        with self._lock:
            self.cursor.execute("SELECT key, value, timestamp, update_time FROM memos")
            return self.cursor.fetchall()

    def get_memo(self, key: str):
        k = str(key or "").strip()
        if not k:
            return None
        with self._lock:
            self.cursor.execute("SELECT value FROM memos WHERE key = ?", (k,))
            row = self.cursor.fetchone()
            return row[0] if row else None

    def find_memos_by_keyword_fuzzy(self, keyword: str):
        kw = str(keyword or "").strip()
        if not kw:
            return []
        with self._lock:
            self.cursor.execute("SELECT key, value, timestamp FROM memos WHERE key LIKE ?", (f"%{kw}%",))
            return self.cursor.fetchall()

    def get_tasks_in_range(self, status='pending'):
        with self._lock:
            self.cursor.execute("SELECT id, time, content, timestamp FROM tasks WHERE status = ?", (status,))
            return self.cursor.fetchall()

    def get_all_tasks(self):
        """Retrieve all tasks regardless of status"""
        with self._lock:
            self.cursor.execute("SELECT id, time, content, status, timestamp FROM tasks")
            return self.cursor.fetchall()

    def append_conversation_message(self, conv_id: int, text: str, is_user: bool, image_path: str = None):
        """向指定对话追加单条消息"""
        conv = self.get_conversation(conv_id)
        if not conv:
            return None

        messages = list(conv.get("messages", []))
        messages.append({
            "text": str(text or ""),
            "is_user": bool(is_user),
            "image_path": image_path,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        })
        self.update_conversation(conv_id, messages)
        return messages

    def ensure_active_conversation(self, title: str = "") -> int:
        """确保当前存在活跃对话，没有则创建"""
        active = self.get_active_conversation()
        if active and active.get("id"):
            return int(active["id"])

        conv_id = self.create_conversation(title or "新对话")
        self.set_active_conversation(conv_id)
        return conv_id

    def add_chat_pair(
        self,
        user_text: str,
        ai_text: str,
        user_type: str = "text",
        ai_type: str = "text",
        user_media_rel_path: str = "",
        ai_media_rel_path: str = "",
    ):
        created_at = time.strftime("%Y-%m-%d %H:%M:%S")
        with self._lock:
            self.cursor.execute(
                "INSERT INTO chat_history (user_text, ai_text, user_type, ai_type, user_media_rel_path, ai_media_rel_path, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    str(user_text),
                    str(ai_text),
                    str(user_type),
                    str(ai_type),
                    str(user_media_rel_path),
                    str(ai_media_rel_path),
                    created_at,
                ),
            )
            self.conn.commit()
        try:
            with open(CHAT_LOG_FILE, "a", encoding="utf-8") as f:
                f.write(f"[{created_at}] 用户：{str(user_text)}\n")
                f.write(f"[{created_at}] AI：{str(ai_text)}\n")
        except Exception:
            pass

    def add_image_recognition(
        self,
        source: str,
        original_path: str,
        saved_rel_path: str,
        image_sha256: str,
        prompt: str,
        recognized_text: str,
        model: str,
    ) -> int:
        created_at = time.strftime("%Y-%m-%d %H:%M:%S")
        with self._lock:
            self.cursor.execute(
                """
                INSERT INTO image_recognitions
                (source, original_path, saved_rel_path, image_sha256, prompt, recognized_text, model, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(source),
                    str(original_path),
                    str(saved_rel_path),
                    str(image_sha256),
                    str(prompt),
                    str(recognized_text),
                    str(model),
                    created_at,
                ),
            )
            self.conn.commit()
            return int(self.cursor.lastrowid or 0)

    def get_chat_pairs(self, limit: int = 10, offset: int = 0):
        with self._lock:
            self.cursor.execute(
                "SELECT user_text, ai_text, created_at FROM chat_history ORDER BY id DESC LIMIT ? OFFSET ?",
                (int(limit), int(offset)),
            )
            return self.cursor.fetchall()

    def clear_chat_history(self):
        with self._lock:
            self.cursor.execute("DELETE FROM chat_history")
            self.conn.commit()
        try:
            if os.path.exists(CHAT_LOG_FILE):
                os.remove(CHAT_LOG_FILE)
        except Exception:
            pass

    # ========== 对话管理功能 ==========
    
    def create_conversation(self, title: str = "") -> int:
        """创建新对话，返回对话ID"""
        created_at = time.strftime("%Y-%m-%d %H:%M:%S")
        # 先取消所有活跃对话
        with self._lock:
            self.cursor.execute("UPDATE conversations SET is_active = 0")
            # 创建新对话
            self.cursor.execute(
                "INSERT INTO conversations (title, created_at, updated_at, messages, is_active) VALUES (?, ?, ?, ?, ?)",
                (title or "新对话", created_at, created_at, "[]", 1)
            )
            self.conn.commit()
            return int(self.cursor.lastrowid or 0)
    
    def get_conversation(self, conv_id: int) -> dict:
        """获取指定对话"""
        with self._lock:
            self.cursor.execute(
                "SELECT id, title, created_at, updated_at, messages, is_active FROM conversations WHERE id = ?",
                (conv_id,)
            )
            row = self.cursor.fetchone()
            if row:
                return {
                    "id": row[0],
                    "title": row[1],
                    "created_at": row[2],
                    "updated_at": row[3],
                    "messages": json.loads(row[4]) if row[4] else [],
                    "is_active": bool(row[5])
                }
            return None
    
    def update_conversation(self, conv_id: int, messages: list, title: str = None):
        """更新对话内容和标题"""
        updated_at = time.strftime("%Y-%m-%d %H:%M:%S")
        messages_json = json.dumps(messages, ensure_ascii=False)
        with self._lock:
            if title:
                self.cursor.execute(
                    "UPDATE conversations SET messages = ?, updated_at = ?, title = ? WHERE id = ?",
                    (messages_json, updated_at, title, conv_id)
                )
            else:
                self.cursor.execute(
                    "UPDATE conversations SET messages = ?, updated_at = ? WHERE id = ?",
                    (messages_json, updated_at, conv_id)
                )
            self.conn.commit()
    
    def set_active_conversation(self, conv_id: int):
        """设置活跃对话"""
        with self._lock:
            self.cursor.execute("UPDATE conversations SET is_active = 0")
            self.cursor.execute("UPDATE conversations SET is_active = 1 WHERE id = ?", (conv_id,))
            self.conn.commit()
    
    def get_active_conversation(self) -> dict:
        """获取当前活跃对话"""
        with self._lock:
            self.cursor.execute(
                "SELECT id, title, created_at, updated_at, messages, is_active FROM conversations WHERE is_active = 1 LIMIT 1"
            )
            row = self.cursor.fetchone()
            if row:
                return {
                    "id": row[0],
                    "title": row[1],
                    "created_at": row[2],
                    "updated_at": row[3],
                    "messages": json.loads(row[4]) if row[4] else [],
                    "is_active": bool(row[5])
                }
            return None
    
    def get_all_conversations(self) -> list:
        """获取所有对话列表"""
        with self._lock:
            self.cursor.execute(
                "SELECT id, title, created_at, updated_at, is_active FROM conversations ORDER BY is_active DESC, updated_at DESC"
            )
            rows = self.cursor.fetchall()
            return [
                {
                    "id": row[0],
                    "title": row[1],
                    "created_at": row[2],
                    "updated_at": row[3],
                    "is_active": bool(row[4])
                }
                for row in rows
            ]
    
    def delete_conversation(self, conv_id: int):
        """删除指定对话"""
        with self._lock:
            self.cursor.execute("DELETE FROM conversations WHERE id = ?", (conv_id,))
            self.conn.commit()
    
    def clear_active_conversation(self):
        """清除所有活跃对话标记"""
        with self._lock:
            self.cursor.execute("UPDATE conversations SET is_active = 0")
            self.conn.commit()
    
    def _get_beijing_time(self):
        """从云端获取北京时间"""
        try:
            import urllib.request
            import json
            from datetime import datetime as dt
            # 使用阿里云的时间API或其他可靠的时间源
            url = "https://timeapi.io/api/Time/current/zone?timeZone=Asia/Shanghai"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=5) as response:
                data = json.loads(response.read().decode('utf-8'))
                # 解析返回的时间
                year = data.get('year')
                month = data.get('month')
                day = data.get('day')
                hour = data.get('hour')
                minute = data.get('minute')
                seconds = data.get('seconds')
                return dt(year, month, day, hour, minute, seconds)
        except Exception as e:
            # 如果获取失败，使用本地时间并打印警告
            from datetime import datetime as dt
            print(f"[System] 获取北京时间失败，使用本地时间: {e}")
            return dt.now()
    
    def cleanup_old_conversations(self, active_conv_id: int = None):
        """清理超过7天的非活跃对话（使用北京时间）"""
        retention = self.get_setting("history_retention", "7days")
        if retention != "7days":
            return 0
        
        # 从云端获取北京时间（7天前）
        from datetime import timedelta
        beijing_now = self._get_beijing_time()
        cutoff_time = beijing_now - timedelta(days=7)
        cutoff_str = cutoff_time.strftime("%Y-%m-%d %H:%M:%S")
        
        print(f"[System] 使用北京时间进行清理检查: {beijing_now.strftime('%Y-%m-%d %H:%M:%S')}, 7天前: {cutoff_str}")
        
        with self._lock:
            # 删除超过7天且不是活跃对话的记录
            if active_conv_id:
                self.cursor.execute(
                    "DELETE FROM conversations WHERE updated_at < ? AND id != ? AND is_active = 0",
                    (cutoff_str, active_conv_id)
                )
            else:
                self.cursor.execute(
                    "DELETE FROM conversations WHERE updated_at < ? AND is_active = 0",
                    (cutoff_str,)
                )
            deleted_count = self.cursor.rowcount
            self.conn.commit()
            return deleted_count

db = DBManager()
# 不再自动清空历史记录，改为对话管理功能
# 清理过期对话
active_conv = db.get_active_conversation()
active_id = active_conv["id"] if active_conv else None
deleted = db.cleanup_old_conversations(active_id)
if deleted > 0:
    print(f"[System] 自动清理了 {deleted} 条过期对话")

kb_engine = KnowledgeBase("knowledge")
kb_engine.load_or_build()

def _normalize_for_match(text: str) -> str:
    if text is None:
        return ""
    s = str(text).strip().lower()
    s = re.sub(r"\s+", " ", s)
    return s

def _tokens_for_match(text: str):
    s = _normalize_for_match(text)
    if not s:
        return set()
    parts = re.findall(r"[a-z0-9]+|[\u4e00-\u9fff]+", s, flags=re.I)
    tokens = set()
    for p in parts:
        if re.fullmatch(r"[a-z0-9]+", p, flags=re.I):
            tokens.add(p)
        else:
            if len(p) <= 2:
                tokens.add(p)
            else:
                for ch in p:
                    tokens.add(ch)
                for i in range(len(p) - 1):
                    tokens.add(p[i:i+2])
    return tokens

def _similarity_score(a: str, b: str) -> float:
    a2 = _normalize_for_match(a)
    b2 = _normalize_for_match(b)
    if not a2 or not b2:
        return 0.0
    if a2 == b2:
        return 1.0
    if len(a2) >= 3 and a2 in b2:
        return 0.95
    if len(b2) >= 3 and b2 in a2:
        return 0.95
    ta = _tokens_for_match(a2)
    tb = _tokens_for_match(b2)
    if not ta or not tb:
        return 0.0
    inter = len(ta & tb)
    union = len(ta | tb)
    jacc = inter / union if union else 0.0
    return jacc

def _jump_keywords():
    return ("前面", "往前", "上条", "更早", "之前", "上一轮", "刚才", "之前说过")

def _cn_number_to_int(s: str):
    if not s:
        return None
    s = str(s).strip()
    if not s:
        return None
    if s.isdigit():
        try:
            return int(s)
        except Exception:
            return None
    m = {"零": 0, "一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}
    if s == "十":
        return 10
    if "十" in s:
        parts = s.split("十")
        left = parts[0]
        right = parts[1] if len(parts) > 1 else ""
        a = m.get(left, 1) if left != "" else 1
        b = m.get(right, 0) if right != "" else 0
        return a * 10 + b
    if len(s) == 1 and s in m:
        return m[s]
    return None

def _parse_front_count(text: str):
    s = _normalize_for_match(text)
    m = re.search(r"前\s*(\d+)\s*(次|条|句|轮|个|一个)", s)
    if m:
        try:
            return int(m.group(1))
        except Exception:
            return None
    m2 = re.search(r"前\s*([一二三四五六七八九十两]+)\s*(次|条|句|轮|个|一个)", s)
    if m2:
        return _cn_number_to_int(m2.group(1))
    return None

def _parse_ordinal(text: str):
    s = _normalize_for_match(text)
    m = re.search(r"倒数\s*第\s*(\d+)\s*(次|条|句|轮|个|一个)", s)
    if m:
        try:
            return ("reverse", int(m.group(1)))
        except Exception:
            pass
    m2 = re.search(r"倒数\s*第\s*([一二三四五六七八九十两]+)\s*(次|条|句|轮|个|一个)", s)
    if m2:
        n = _cn_number_to_int(m2.group(1))
        if n:
            return ("reverse", n)
    m3 = re.search(r"第\s*(\d+)\s*(次|条|句|轮|个|一个)", s)
    if m3:
        try:
            return ("forward", int(m3.group(1)))
        except Exception:
            pass
    m4 = re.search(r"第\s*([一二三四五六七八九十两]+)\s*(次|条|句|轮|个|一个)", s)
    if m4:
        n = _cn_number_to_int(m4.group(1))
        if n:
            return ("forward", n)
    return None

def _is_history_recall_query(text: str):
    s = _normalize_for_match(text)
    if not s:
        return None
    if ("什么" not in s) and ("啥" not in s):
        return None
    if _parse_front_count(s) or _parse_ordinal(s):
        pass
    elif ("刚刚" in s) or ("刚才" in s) or ("上次" in s) or ("上一句" in s) or ("上一条" in s) or ("上个" in s) or ("上一个" in s):
        pass
    elif any(k in s for k in _jump_keywords()):
        pass
    else:
        return None
    if ("我" in s) and (("问" in s) or ("说" in s)) and (("什么" in s) or ("啥" in s)):
        return "user_last"
    if (("你" in s) or ("皮皮" in s)) and (("回答" in s) or ("回复" in s) or ("说" in s)) and (("什么" in s) or ("啥" in s)):
        return "ai_last"
    if ("问了什么" in s) or ("问的什么" in s) or ("说了什么" in s):
        return "user_last"
    return None

def _looks_like_follow_up(text: str) -> bool:
    s = _normalize_for_match(text)
    if not s:
        return False
    # 明显的承接/追问用语
    cues = ("那", "然后呢", "继续", "还有呢", "再详细点", "具体点", "举个例子", "比如说", "这个", "它", "这些", "上述", "上面说的", "前面说的", "能再说说")
    if any(c in s for c in cues):
        return True
    # 题目追问：直接给出答案、直接说答案等
    answer_cues = ("直接给出", "直接输出", "直接说", "直接告诉我", "直接讲", "直接答", "答案是什么", "选哪个", "选什么", "选哪个选项", "答案是", "答案就是", "直接给")
    if any(c in s for c in answer_cues):
        return True
    # 题目错误分析追问
    error_cues = ("为什么会错", "为什么", "错在哪里", "哪里错了", "为什么不对", "为啥", "怎么回事", "解释一下", "详细说说", "展开说说", "具体说说", "分析一下")
    if any(c in s for c in error_cues):
        return True
    if len(s) <= 8 and (s.endswith("吗") or s.endswith("？") or s.endswith("?")):
        if any(k in s for k in ("这", "那", "它", "他", "她", "真", "假", "是否", "是不是", "对吗", "行吗", "可以吗", "懂吗", "明白吗")):
            return True
    return False

def _history_recall_reply(text: str):
    mode = _is_history_recall_query(text)
    if not mode:
        return None
    s = _normalize_for_match(text)
    has_jump = any(k in s for k in _jump_keywords())
    ord_res = _parse_ordinal(s)
    if isinstance(ord_res, tuple):
        direction, n = ord_res
        if n and n > 0:
            all_pairs = db.get_chat_pairs(limit=1000, offset=0)
            if not all_pairs:
                return "这次启动后还没有可回忆的对话。"
            if direction == "forward":
                asc = list(reversed(all_pairs))
                if n <= len(asc):
                    u, a, _ts = asc[n-1]
                    if mode == "ai_last":
                        return f"你第{n}次时我回答的是：{a}" if a else "我没能找到对应的回复。"
                    else:
                        return f"你第{n}次问的是：{u}" if u else "我没能找到对应的提问。"
                return "这次启动后还没有可回忆的对话。"
            else:
                idx = n - 1
                if idx < len(all_pairs):
                    u, a, _ts = all_pairs[idx]
                    if mode == "ai_last":
                        return f"你倒数第{n}次时我回答的是：{a}" if a else "我没能找到对应的回复。"
                    else:
                        return f"你倒数第{n}次问的是：{u}" if u else "我没能找到对应的提问。"
                return "这次启动后还没有可回忆的对话。"
    front_n = _parse_front_count(s)
    if isinstance(front_n, int) and front_n > 0:
        base_offset = 10 if has_jump else 0
        pairs = db.get_chat_pairs(limit=base_offset + front_n, offset=0)
        if not pairs or len(pairs) <= base_offset:
            return "这次启动后还没有可回忆的对话。"
        picked = pairs[base_offset:base_offset + front_n]
        if not picked:
            return "这次启动后还没有可回忆的对话。"
        picked = list(reversed(picked))
        lines = []
        if mode == "ai_last":
            for i, (_u, a, _ts) in enumerate(picked, start=1):
                if a:
                    lines.append(f"{i}. {a}")
        else:
            for i, (u, _a, _ts) in enumerate(picked, start=1):
                if u:
                    lines.append(f"{i}. {u}")
        if not lines:
            return "这次启动后还没有可回忆的对话。"
        who = "回答" if mode == "ai_last" else "问"
        desc = f"前{front_n}次"
        return f"你{desc}{who}的是：\n" + "\n".join(lines)
    steps = 1
    try:
        m = re.search(r"(上+)(次|条|句|轮|个|一个)", s)
        if m:
            steps = max(1, len(m.group(1)))
        elif "刚刚" in s or "刚才" in s:
            steps = 1
        elif "上上" in s:
            steps = 2
    except Exception:
        steps = 1
    base_offset = 10 if has_jump else 0
    pairs = db.get_chat_pairs(limit=base_offset + steps, offset=0)
    if not pairs:
        return "这次启动后还没有可回忆的对话。"
    idx = base_offset + (steps - 1)
    if idx >= len(pairs):
        return "这次启动后还没有可回忆的对话。"
    last_user, last_ai, _ts = pairs[idx]
    desc = "刚刚" if steps == 1 else ("上" * steps + "次")
    if mode == "ai_last":
        if last_ai:
            return f"我{desc}回答的是：{last_ai}"
        return "我刚刚还没有给出有效回复。"
    if last_user:
        return f"你{desc}问的是：{last_user}"
    return "我没能回忆起你刚刚的提问内容。"

def _find_relevant_history(current_user_text: str):
    cur = _normalize_for_match(current_user_text)
    if not cur:
        return None
    keywords = _jump_keywords()
    has_jump = any(k in cur for k in keywords)
    
    # 如果是追问（包括对题目的追问），优先查找最近的图片对话
    is_follow_up = _looks_like_follow_up(cur) or _looks_like_image_follow_up(cur)
    
    if is_follow_up and not _is_history_recall_query(cur):
        # 获取最近的几条对话
        recent = db.get_chat_pairs(limit=5, offset=0)
        if recent:
            # 优先查找包含图片的对话（题目）
            for u_text, a_text, _ts in recent:
                if str(u_text or "").strip().startswith("[图片]"):
                    return [(u_text, a_text)]
            # 如果没有图片，返回最近的一组对话
            u_text, a_text, _ts = recent[0]
            return [(u_text, a_text)]
    
    search_offset = 10 if has_jump else 0
    threshold = 0.35
    while True:
        pairs = db.get_chat_pairs(limit=10, offset=search_offset)
        if not pairs:
            return None
        scored = []
        for u_text, a_text, _ts in pairs:
            score = _similarity_score(cur, u_text)
            scored.append((score, u_text, a_text))
        scored.sort(key=lambda x: x[0], reverse=True)
        top = [ (u,a) for s,u,a in scored if s >= threshold ][:2]
        if top:
            return top
        if not has_jump:
            return None
        search_offset += 10

# --- 线程类 (与原文件一致) ---

def _looks_like_vosk_model_dir(model_dir: str) -> bool:
    try:
        if not model_dir or not os.path.isdir(model_dir):
            return False
        conf_file = os.path.join(model_dir, "conf", "model.conf")
        if os.path.isfile(conf_file):
            return True
        am_dir = os.path.join(model_dir, "am")
        if os.path.isdir(am_dir):
            for name in ("final.mdl", "final.mdl.gz"):
                if os.path.isfile(os.path.join(am_dir, name)):
                    return True
        return False
    except Exception:
        return False

def _is_ascii_only_path(p: str) -> bool:
    try:
        s = str(p or "")
        return bool(s) and all(ord(ch) < 128 for ch in s)
    except Exception:
        return False

def _pick_ascii_writable_dir() -> str | None:
    candidates = []
    for k in ("TEMP", "TMP"):
        v = os.environ.get(k, "")
        if v:
            candidates.append(v)
    candidates.append(os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "Temp"))
    candidates.append(os.path.join(os.environ.get("SystemDrive", "C:"), "Temp"))
    candidates.append(r"C:\Temp")

    seen = set()
    for base in candidates:
        base = os.path.abspath(str(base or "").strip())
        if not base or base in seen:
            continue
        seen.add(base)
        if not _is_ascii_only_path(base):
            continue
        try:
            os.makedirs(base, exist_ok=True)
            probe = os.path.join(base, f"._w_{uuid.uuid4().hex}")
            with open(probe, "wb") as f:
                f.write(b"1")
            os.remove(probe)
            return base
        except Exception:
            continue
    return None

def _ensure_ascii_vosk_model_dir(model_dir: str) -> str | None:
    base = _pick_ascii_writable_dir()
    if not base:
        return None
    try:
        h = hashlib.sha256(str(model_dir).encode("utf-8", errors="ignore")).hexdigest()[:10]
    except Exception:
        h = uuid.uuid4().hex[:10]
    target_dir = os.path.join(base, f"desktop_pet_vosk_{h}")
    try:
        if _looks_like_vosk_model_dir(target_dir):
            return target_dir
    except Exception:
        pass

    try:
        if not os.path.exists(target_dir):
            cmd = f'cmd /c mklink /J "{target_dir}" "{model_dir}"'
            subprocess.run(cmd, shell=True, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if _looks_like_vosk_model_dir(target_dir):
            return target_dir
    except Exception:
        pass

    try:
        os.makedirs(target_dir, exist_ok=True)
        for name in ("conf", "am", "graph", "ivector"):
            src = os.path.join(model_dir, name)
            dst = os.path.join(target_dir, name)
            if os.path.exists(src):
                shutil.copytree(src, dst, dirs_exist_ok=True)
        if _looks_like_vosk_model_dir(target_dir):
            return target_dir
    except Exception:
        return None
    return None

class VoiceThread(QThread):
    text_received = pyqtSignal(str)
    error_occurred = pyqtSignal(str)
    def __init__(self):
        super().__init__()
        self.running = False
        self.model = None
        self._model_error = ""
        if not VOICE_SUPPORT:
            self._model_error = "未安装 PyAudio 或 Vosk，语音功能已禁用。"
            return
        if not os.path.exists(VOSK_PATH):
            self._model_error = f"未找到语音模型目录：{VOSK_PATH}"
            return
        ascii_vosk_path = None
        if not _is_ascii_only_path(VOSK_PATH):
            ascii_vosk_path = _ensure_ascii_vosk_model_dir(VOSK_PATH)

        short_path = get_windows_short_path(VOSK_PATH)
        candidates = []
        if ascii_vosk_path:
            candidates.append(ascii_vosk_path)
        if short_path and short_path != VOSK_PATH:
            candidates.append(short_path)
        candidates.append(VOSK_PATH)

        if not any(_looks_like_vosk_model_dir(p) for p in candidates):
            self._model_error = f"语音模型目录不包含 Vosk 模型文件：{VOSK_PATH}"
            return

        last_err = None
        for p in candidates:
            if not _looks_like_vosk_model_dir(p):
                continue
            try:
                self.model = Model(p)
                last_err = None
                break
            except Exception as e:
                last_err = e
                self.model = None

        if not self.model:
            self._model_error = f"语音模型加载失败：{last_err}" if last_err else f"语音模型加载失败：{VOSK_PATH}"
    def run(self):
        if not VOICE_SUPPORT:
            self.error_occurred.emit("未安装 PyAudio 或 Vosk，语音功能已禁用。")
            return
        if not self.model:
            self.error_occurred.emit(self._model_error or f"未能加载语音模型：{VOSK_PATH}")
            return
        self.running = True
        p = pyaudio.PyAudio()
        try:
            stream = p.open(format=pyaudio.paInt16, channels=1, rate=16000, input=True, frames_per_buffer=4000)
            rec = KaldiRecognizer(self.model, 16000)
            while self.running:
                data = stream.read(4000, exception_on_overflow=False)
                if rec.AcceptWaveform(data):
                    res = json.loads(rec.Result())
                    txt = res['text'].replace(" ", "")
                    if txt: self.text_received.emit(txt)
            stream.stop_stream(); stream.close()
        except Exception as e: self.error_occurred.emit(str(e))
        finally: p.terminate()
    def stop(self): self.running = False

class TTSWorker(QThread):
    def __init__(self):
        super().__init__()
        self.text_to_speak = ""
        self._engine = None
        self.volume = 1.0
        try:
            self.volume = float(db.get_setting("tts_volume", "1.0"))
        except:
            self.volume = 1.0

    def set_volume(self, volume):
        self.volume = max(0.0, min(1.0, volume))
        print(f"[TTS] 音量已设置为: {self.volume}")

    def stop_speaking(self):
        """尝试停止当前的播报"""
        if self._engine:
            try:
                # 注意：在非 run 线程中调用 stop 可能有风险，但在 SAPI5 通常有效
                self._engine.stop()
                print("[TTS] 已发出停止指令")
            except Exception as e:
                print(f"[TTS] 停止失败: {e}")

    def say(self, text):
        if self.isRunning():
            print("[TTS] 打断当前播报，播放新内容...")
            self.stop_speaking()
            # 等待线程结束（最多等 1 秒，避免卡死）
            if not self.wait(1000):
                print("[TTS] 线程停止超时，强制终止（可能导致资源未释放）")
                self.terminate()
                self.wait()
        
        self.text_to_speak = text
        self.start()

    def run(self):
        print(f"[TTS] 开始播报: {self.text_to_speak[:20]}... (音量: {self.volume})")
        pythoncom.CoInitialize()
        try:
            self._engine = pyttsx3.init()
            self._engine.setProperty('rate', 180)
            self._engine.setProperty('volume', self.volume)
            self._engine.say(self.text_to_speak)
            self._engine.runAndWait()
            print("[TTS] 播报完成")
        except Exception as e:
            print(f"[TTS] 播报出错: {e}")
        finally:
            if self._engine:
                self._engine.stop()
                del self._engine
            pythoncom.CoUninitialize()

class WeChatStatusThread(QThread):
    status_changed = pyqtSignal(bool)
    def __init__(self, interval_online=60, interval_offline=10):
        super().__init__()
        self.interval_online = interval_online
        self.interval_offline = interval_offline
        self._running = True
        self._last_ok = None

    def stop(self):
        print("[WeChatStatusThread] 停止监控线程")
        self._running = False
    
    def __del__(self):
        try:
            self._running = False
            if self.isRunning():
                self.wait(1000)
        except Exception:
            pass

    def run(self):
        if not WX_SUPPORT:
            print("[WeChatStatusThread] 未检测到 wxauto 支持库，监控中止")
            return
        
        print("[WeChatStatusThread] 开始监控微信状态...")
        self._running = True
        
        pythoncom.CoInitialize()
        try:
            wx = None
            while self._running:
                ok = False
                
                # 1. 简单进程检查
                has_proc = True
                if psutil:
                    try:
                        names = set(p.name() for p in psutil.process_iter(['name']))
                        if not any(n.lower() in ('wechat.exe', 'wechatapp.exe') for n in names if n):
                            has_proc = False
                            print("[WeChatStatusThread] 未发现微信进程")
                    except: pass
                
                if has_proc:
                    try:
                        with wx_lock:
                            if wx is None:
                                wx = WeChat()
                            wx.GetSessionList()
                        ok = True
                        if self._last_ok != True:
                            print("[WeChatStatusThread] 微信连接成功")
                    except Exception as e:
                        print(f"[WeChatStatusThread] 轮询异常: {e}")
                        ok = False
                        wx = None
                else:
                    ok = False
                
                is_online = ok
                
                if self._running and is_online != self._last_ok:
                    print(f"[WeChatStatusThread] 状态变更: {self._last_ok} -> {is_online}")
                    self.status_changed.emit(is_online)
                    self._last_ok = is_online
                
                sleep_sec = self.interval_online if is_online else self.interval_offline
                for _ in range(sleep_sec):
                    if not self._running: break
                    time.sleep(1)
        finally:
            pythoncom.CoUninitialize()
            print("[WeChatStatusThread] 线程退出")

class WeChatLogoutWatcher(QThread):
    status_changed = pyqtSignal(bool)  # 仅在退出时发 False
    def __init__(self, interval=2):
        super().__init__()
        self.interval = interval
        self._running = True

    def stop(self): 
        print("[WeChatLogoutWatcher] 停止退出监控")
        self._running = False

    def run(self):
        print("[WeChatLogoutWatcher] 开始监控微信退出...")
        self._running = True
        
        while self._running:
            offline = False
            try:
                if psutil:
                    names = set(p.name() for p in psutil.process_iter(['name']))
                    if not any(n.lower() in ('wechat.exe', 'wechatapp.exe') for n in names if n):
                        offline = True
                        print("[WeChatLogoutWatcher] 检测到微信进程消失")
                else:
                    pythoncom.CoInitialize()
                    try:
                        ok = True
                        try:
                            wx = WeChat()
                            wx.GetSessionList()
                        except Exception:
                            ok = False
                        offline = not ok
                        if offline: print("[WeChatLogoutWatcher] 检测到微信连接断开")
                    finally:
                        pythoncom.CoUninitialize()
            except Exception as e:
                print(f"[WeChatLogoutWatcher] 监控异常: {e}")
                offline = True
            
            if self._running and offline:
                self.status_changed.emit(False)
                break
                
            for _ in range(self.interval):
                if not self._running: break
                time.sleep(1)
        print("[WeChatLogoutWatcher] 线程退出")

class WxCheckWorker(QThread):
    result_ready = pyqtSignal(bool, str) # (is_online, message)
    
    def run(self):
        print("[WxCheckWorker] 开始手动检查微信状态...")
        if not WX_SUPPORT:
            self.result_ready.emit(False, "未检测到微信支持库")
            return
            
        if psutil:
            try:
                names = set(p.name() for p in psutil.process_iter(['name']))
                if not any(n.lower() in ('wechat.exe', 'wechatapp.exe') for n in names if n):
                    print("[WxCheckWorker] 未发现微信进程")
                    self.result_ready.emit(False, "未检测到微信运行")
                    return
            except Exception:
                pass
        
        max_retries = 3
        last_error = ""
        
        pythoncom.CoInitialize()
        try:
            for i in range(max_retries):
                print(f"[WxCheckWorker] 尝试连接微信 (第 {i+1} 次)...")
                try:
                    with wx_lock:
                        wx = WeChat()
                        wx.GetSessionList()
                    print("[WxCheckWorker] 连接成功")
                    self.result_ready.emit(True, "微信已连接")
                    return
                except Exception as e:
                    last_error = str(e)
                    print(f"[WxCheckWorker] 连接失败: {e}")
                    if i < max_retries - 1:
                        time.sleep(1)
            
            print(f"[WxCheckWorker] 最终检查失败: {last_error}")
            self.result_ready.emit(False, "未检测到微信登录或连接超时")
        finally:
            pythoncom.CoUninitialize()
            print("[WxCheckWorker] 检查结束")

def _extract_json_payload(text: str) -> str:
    s = str(text or "").strip()
    if not s:
        return "{}"
    a = s.find("[")
    o = s.find("{")
    if a != -1 and (o == -1 or a < o):
        end = s.rfind("]")
        if end != -1 and end > a:
            return s[a : end + 1]
    if o != -1:
        end = s.rfind("}")
        if end != -1 and end > o:
            return s[o : end + 1]
    return s

def _sanitize_visible_text(text: str) -> str:
    s = str(text or "")
    if not s:
        return ""
    s = s.replace("```", "")
    for ch in ("{", "}", "[", "]", "\"", "'", "`"):
        s = s.replace(ch, "")
    lines = []
    for line in s.splitlines():
        t = str(line or "").strip()
        if not t:
            continue
        lines.append(t)
    return "\n".join(lines).strip()


def _format_ai_reply_text(text: str) -> str:
    s = str(text or "")
    if not s:
        return ""
    s = s.replace("\r\n", "\n").replace("\r", "\n")
    s = s.replace("```", "")
    s = s.replace("**", "").replace("__", "")
    s = re.sub(r"^\s{0,3}#{1,6}\s*", "", s, flags=re.M)
    lines = []
    for raw_line in s.split("\n"):
        line = str(raw_line or "").strip()
        if not line:
            if lines and lines[-1] != "":
                lines.append("")
            continue
        if re.fullmatch(r"[\|:\-\s]+", line):
            continue
        if line.startswith("|") and line.endswith("|"):
            cells = [c.strip() for c in line.strip("|").split("|") if c.strip()]
            line = "  ·  ".join(cells)
        line = re.sub(r"^[-*•]\s+", "• ", line)
        line = re.sub(r"^\d+\.\s+", lambda m: m.group(0), line)
        line = line.replace("\t", "    ")
        lines.append(line)
    out = "\n".join(lines)
    out = re.sub(r"\n{3,}", "\n\n", out).strip()
    return _sanitize_visible_text(out)

def _parse_internal_actions_and_reply(text: str):
    raw = str(text or "")
    actions = []
    visible_lines = []
    for line in raw.splitlines():
        s = str(line or "").strip()
        if not s:
            continue
        if s.startswith("操作"):
            body = s[len("操作"):].lstrip("：: ").strip()
            if not body:
                continue
            if body.startswith("设置备忘录"):
                rest = body[len("设置备忘录"):].strip()
                key = ""
                val = ""
                m = re.search(r"关键字\s+(.*?)\s+内容\s+(.*)", rest)
                if m:
                    key = (m.group(1) or "").strip()
                    val = (m.group(2) or "").strip()
                else:
                    parts = rest.split()
                    if len(parts) >= 2:
                        key = parts[0].strip()
                        val = " ".join(parts[1:]).strip()
                if key and val:
                    actions.append({"type": "set_memo", "key": key, "value": val})
                continue
            if body.startswith("查询备忘录"):
                rest = body[len("查询备忘录"):].strip()
                key = ""
                m = re.search(r"关键字\s+(.*)", rest)
                if m:
                    key = (m.group(1) or "").strip()
                else:
                    key = rest.strip()
                if key:
                    actions.append({"type": "get_memo", "key": key})
                continue
            if body.startswith("列出备忘录"):
                actions.append({"type": "list_memos"})
                continue
            if body.startswith("添加提醒"):
                rest = body[len("添加提醒"):].strip()
                t_expr = ""
                content = ""
                m = re.search(r"时间\s+(.*?)\s+内容\s+(.*)", rest)
                if m:
                    t_expr = (m.group(1) or "").strip()
                    content = (m.group(2) or "").strip()
                else:
                    parts = rest.split()
                    if len(parts) >= 2:
                        t_expr = parts[0].strip()
                        content = " ".join(parts[1:]).strip()
                if t_expr and content:
                    actions.append({"type": "task", "time": t_expr, "content": content})
                continue
            if body.startswith("列出提醒"):
                actions.append({"type": "list_tasks"})
                continue
            if body.startswith("打开应用"):
                rest = body[len("打开应用"):].strip()
                app = ""
                m = re.search(r"名称\s+(.*)", rest)
                if m:
                    app = (m.group(1) or "").strip()
                else:
                    app = rest.strip()
                if app:
                    actions.append({"type": "launch_app", "app": app})
                continue
            if body.startswith("关闭应用"):
                rest = body[len("关闭应用"):].strip()
                app = ""
                m = re.search(r"名称\s+(.*)", rest)
                if m:
                    app = (m.group(1) or "").strip()
                else:
                    app = rest.strip()
                if app:
                    actions.append({"type": "close_app", "app": app})
                continue
            if body.startswith("查询知识库"):
                rest = body[len("查询知识库"):].strip()
                q = ""
                m = re.search(r"问题\s+(.*)", rest)
                if m:
                    q = (m.group(1) or "").strip()
                else:
                    q = rest.strip()
                if q:
                    actions.append({"type": "kb_query", "question": q})
                continue
            continue
        visible_lines.append(s)
    visible = _sanitize_visible_text("\n".join(visible_lines))
    return actions, visible

# ============ 历史对话面板 ============

class HistoryBubbleWidget(QWidget):
    """气泡式历史消息组件（用于左侧历史对话展示）"""
    delete_requested = pyqtSignal(int)
    load_requested = pyqtSignal(int)
    
    def __init__(self, conv_id: int, text: str, is_user: bool, created_at: str, parent=None):
        super().__init__(parent)
        self.conv_id = conv_id
        self.is_user = is_user
        self.setMaximumWidth(600)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 6, 12, 6)
        layout.setSpacing(8)
        
        # 时间戳
        time_str = str(created_at or "")[11:16] if created_at else ""
        self.timeLabel = QLabel(time_str)
        self.timeLabel.setFont(QFont("Microsoft YaHei", 8))
        
        # 气泡内容
        self.contentLabel = QLabel(str(text or ""))
        self.contentLabel.setFont(QFont("Microsoft YaHei", 10))
        self.contentLabel.setWordWrap(True)
        self.contentLabel.setMaximumWidth(400)
        self.contentLabel.setMinimumWidth(60)
        self.contentLabel.setTextInteractionFlags(Qt.TextSelectableByMouse)
        
        is_dark = db.get_setting("dark_mode", "False") == "True"
        self._update_style(is_dark)
        
        # 布局：用户消息右对齐，AI消息左对齐
        if is_user:
            layout.addStretch(1)
            layout.addWidget(self.contentLabel)
            layout.addSpacing(8)
            layout.addWidget(self.timeLabel, 0, Qt.AlignBottom)
        else:
            layout.addWidget(self.timeLabel, 0, Qt.AlignBottom)
            layout.addSpacing(8)
            layout.addWidget(self.contentLabel)
            layout.addStretch(1)
    
    def _update_style(self, is_dark: bool):
        """更新样式"""
        if self.is_user:
            # 用户消息：右侧浅蓝
            if is_dark:
                bubble_style = '''
                    QLabel {
                        background: rgba(64,158,255,0.85);
                        color: white;
                        border-radius: 12px;
                        padding: 8px 12px;
                        border-top-right-radius: 4px;
                    }
                '''
                time_style = "color: rgba(180,180,180,180);"
            else:
                bubble_style = '''
                    QLabel {
                        background: rgba(64,158,255,0.75);
                        color: white;
                        border-radius: 12px;
                        padding: 8px 12px;
                        border-top-right-radius: 4px;
                    }
                '''
                time_style = "color: rgba(120,120,120,180);"
        else:
            # AI消息：左侧浅灰
            if is_dark:
                bubble_style = '''
                    QLabel {
                        background: rgba(255,255,255,0.15);
                        color: white;
                        border-radius: 12px;
                        padding: 8px 12px;
                        border-top-left-radius: 4px;
                    }
                '''
                time_style = "color: rgba(180,180,180,180);"
            else:
                bubble_style = '''
                    QLabel {
                        background: rgba(240,240,240,0.85);
                        color: #333;
                        border-radius: 12px;
                        padding: 8px 12px;
                        border-top-left-radius: 4px;
                    }
                '''
                time_style = "color: rgba(120,120,120,180);"
        
        self.contentLabel.setStyleSheet(bubble_style)
        self.timeLabel.setStyleSheet(f"background: transparent; {time_style}")
    
    def update_theme(self, is_dark: bool):
        self._update_style(is_dark)


class HistoryItemWidget(QWidget):
    """历史对话列表项组件（微信样式）"""
    delete_requested = pyqtSignal(int)
    load_requested = pyqtSignal(int)
    
    def __init__(self, conv_id: int, title: str, created_at: str, updated_at: str, is_active: bool, parent=None):
        super().__init__(parent)
        self.conv_id = conv_id
        self.is_active = is_active
        self.setFixedHeight(64)
        self.setCursor(Qt.PointingHandCursor)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(10)
        
        # 头像/图标区域
        self.iconLabel = QLabel(self)
        self.iconLabel.setFixedSize(44, 44)
        self.iconLabel.setAlignment(Qt.AlignCenter)
        self.iconLabel.setFont(QFont("Microsoft YaHei", 18))
        self.iconLabel.setText("💬")
        
        # 中间内容区
        content_layout = QVBoxLayout()
        content_layout.setSpacing(4)
        
        # 标题和时间的横向布局
        title_layout = QHBoxLayout()
        title_layout.setSpacing(8)
        
        self.titleLabel = QLabel(str(title or "新对话")[:20])
        self.titleLabel.setFont(QFont("Microsoft YaHei", 11, QFont.Bold))
        
        time_str = str(updated_at or created_at or "")[5:16] if (updated_at or created_at) else ""
        self.timeLabel = QLabel(time_str)
        self.timeLabel.setFont(QFont("Microsoft YaHei", 9))
        
        title_layout.addWidget(self.titleLabel, 1)
        title_layout.addWidget(self.timeLabel)
        
        # 创建时间提示
        create_time = str(created_at or "")[:16] if created_at else ""
        self.subtitleLabel = QLabel(f"创建于 {create_time}")
        self.subtitleLabel.setFont(QFont("Microsoft YaHei", 9))
        
        content_layout.addLayout(title_layout)
        content_layout.addWidget(self.subtitleLabel)
        
        # 删除按钮（默认隐藏）
        self.deleteBtn = TransparentToolButton(FIF.DELETE, self)
        self.deleteBtn.setFixedSize(28, 28)
        self.deleteBtn.setIconSize(QSize(14, 14))
        self.deleteBtn.setToolTip("删除此对话")
        self.deleteBtn.setStyleSheet("background: transparent; border: none;")
        self.deleteBtn.hide()
        
        layout.addWidget(self.iconLabel)
        layout.addLayout(content_layout, 1)
        layout.addWidget(self.deleteBtn)
        
        # 应用样式
        self._update_style()
        
        # 信号连接
        self.deleteBtn.clicked.connect(self._on_delete)
    
    def _update_style(self):
        """更新样式"""
        is_dark = db.get_setting("dark_mode", "False") == "True"
        
        if self.is_active:
            # 活跃对话高亮
            self.setStyleSheet("""
                HistoryItemWidget {
                    background: rgba(64,158,255,0.15);
                    border-radius: 8px;
                }
            """)
        else:
            if is_dark:
                self.setStyleSheet("""
                    HistoryItemWidget {
                        background: transparent;
                        border-radius: 8px;
                    }
                    HistoryItemWidget:hover {
                        background: rgba(255,255,255,0.08);
                    }
                """)
            else:
                self.setStyleSheet("""
                    HistoryItemWidget {
                        background: transparent;
                        border-radius: 8px;
                    }
                    HistoryItemWidget:hover {
                        background: rgba(0,0,0,0.05);
                    }
                """)
        
        # 时间颜色
        if is_dark:
            self.timeLabel.setStyleSheet("color: rgba(180,180,180,180);")
            self.subtitleLabel.setStyleSheet("color: rgba(140,140,140,180);")
        else:
            self.timeLabel.setStyleSheet("color: rgba(120,120,120,180);")
            self.subtitleLabel.setStyleSheet("color: rgba(100,100,100,180);")
    
    def enterEvent(self, event):
        """鼠标进入时显示删除按钮"""
        self.deleteBtn.show()
        super().enterEvent(event)
    
    def leaveEvent(self, event):
        """鼠标离开时隐藏删除按钮"""
        self.deleteBtn.hide()
        super().leaveEvent(event)
    
    def mousePressEvent(self, event):
        """点击加载对话"""
        if event.button() == Qt.LeftButton and not self.deleteBtn.geometry().contains(event.pos()):
            self.load_requested.emit(self.conv_id)
        super().mousePressEvent(event)
    
    def _on_delete(self):
        """删除对话"""
        self.delete_requested.emit(self.conv_id)


class HistoryPanel(QWidget):
    """历史对话侧边栏面板（嵌入在聊天界面右侧）"""
    load_conversation = pyqtSignal(int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(280)
        
        # 根据深色/浅色模式设置样式
        is_dark = db.get_setting("dark_mode", "False") == "True"
        self._update_panel_style(is_dark)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # 头部
        header = QLabel("  📋 历史对话")
        header.setFixedHeight(48)
        header.setFont(QFont("Microsoft YaHei", 12, QFont.Bold))
        if is_dark:
            header.setStyleSheet("background: rgba(64,158,255,220); color: white; padding-left: 8px;")
        else:
            header.setStyleSheet("background: rgba(64,158,255,200); color: white; padding-left: 8px;")
        layout.addWidget(header)
        
        # 滚动区域
        self.scrollArea = ScrollArea(self)
        self.scrollArea.setWidgetResizable(True)
        self.scrollArea.setStyleSheet("background: transparent; border: none;")
        self.container = QWidget()
        self.containerLayout = QVBoxLayout(self.container)
        self.containerLayout.setContentsMargins(0, 0, 0, 0)
        self.containerLayout.setSpacing(0)
        self.containerLayout.setAlignment(Qt.AlignTop)
        self.scrollArea.setWidget(self.container)
        layout.addWidget(self.scrollArea)
        
        # 空状态提示
        self.empty_hint = QLabel("📭 暂无历史对话\n\n发送消息开始新对话")
        self.empty_hint.setAlignment(Qt.AlignCenter)
        self.empty_hint.setFont(QFont("Microsoft YaHei", 11))
        if is_dark:
            self.empty_hint.setStyleSheet("color: rgba(200,200,200,180); background: transparent; padding: 20px;")
        else:
            self.empty_hint.setStyleSheet("color: rgba(100,100,100,180); background: transparent; padding: 20px;")
        self.containerLayout.addWidget(self.empty_hint)
        
        self._history_items = []
        self._is_dark = is_dark
        self.refresh()
    
    def _update_panel_style(self, is_dark: bool):
        """更新面板样式"""
        if is_dark:
            self.setStyleSheet("""
                HistoryPanel {
                    background: rgba(30,30,30,240);
                    border-left: 1px solid rgba(255,255,255,20);
                }
            """)
        else:
            self.setStyleSheet("""
                HistoryPanel {
                    background: rgba(245,245,245,240);
                    border-left: 1px solid rgba(0,0,0,15);
                }
            """)
    
    def refresh(self, current_conv_id: int = None, current_has_messages: bool = False):
        """刷新历史列表
        Args:
            current_conv_id: 当前对话ID（如果有）
            current_has_messages: 当前对话是否有消息
        """
        # 清空旧条目（保留 empty_hint）
        while self.containerLayout.count() > 0:
            item = self.containerLayout.takeAt(0)
            w = item.widget()
            if w and w is not self.empty_hint:
                w.deleteLater()
        self._history_items.clear()
        
        convs = db.get_all_conversations()
        if not convs and not current_has_messages:
            self.empty_hint.show()
            self.containerLayout.addWidget(self.empty_hint)
            return
        
        self.empty_hint.hide()
        
        # 排序逻辑：
        # 1. 如果当前对话有消息，放在第一位
        # 2. 其他对话按更新时间倒序（新的在前）
        current_conv_data = None
        if current_conv_id and current_has_messages:
            # 获取当前对话的完整数据
            current_conv_data = db.get_conversation(current_conv_id)
        
        # 排除当前对话（如果有），剩下的按时间排序
        other_convs = [c for c in convs if c["id"] != current_conv_id]
        other_convs.sort(key=lambda x: x["updated_at"], reverse=True)
        
        # 组合列表：当前对话（如果有）+ 其他对话
        sorted_convs = []
        if current_conv_data:
            sorted_convs.append({
                "id": current_conv_data["id"],
                "title": current_conv_data["title"],
                "created_at": current_conv_data["created_at"],
                "updated_at": current_conv_data["updated_at"],
                "is_active": True  # 当前对话标记为活跃
            })
        sorted_convs.extend(other_convs)
        
        for conv in sorted_convs:
            item_w = HistoryItemWidget(
                conv["id"], 
                conv["title"], 
                conv["created_at"], 
                conv["updated_at"], 
                conv["is_active"],
                self.container
            )
            item_w.delete_requested.connect(self._on_delete)
            item_w.load_requested.connect(self._on_load)
            self.containerLayout.addWidget(item_w)
            self._history_items.append(item_w)
    
    def _on_delete(self, conv_id: int):
        box = MessageBox(
            "删除对话",
            "删除后永久不可恢复，确定删除？",
            self
        )
        box.yesButton.setText("确定")
        box.cancelButton.setText("取消")
        if box.exec():
            db.delete_conversation(conv_id)
            self.refresh()
            InfoBar.success("成功", "对话已删除", duration=2000, parent=self)
    
    def _on_load(self, conv_id: int):
        self.load_conversation.emit(conv_id)
    
    def update_theme(self, is_dark: bool):
        self._is_dark = is_dark
        self._update_panel_style(is_dark)
        for item in self._history_items:
            item._update_style()


class AIWorker(QThread):
    response_chunk = pyqtSignal(str)
    response_ready = pyqtSignal(str, str)
    def __init__(
        self,
        user_text: str,
        llm_text: str | None = None,
        image_context: str = "",
        user_type: str = "text",
        user_media_rel_path: str = "",
        reply_target=None,
        emotion_data: dict = None,
    ):
        super().__init__()
        self.user_text = str(user_text or "")
        self.text = self.user_text
        self.llm_text = str(llm_text) if isinstance(llm_text, str) else self.user_text
        self.image_context = str(image_context or "")
        self.user_type = str(user_type or "text")
        self.user_media_rel_path = str(user_media_rel_path or "")
        self.reply_target = reply_target
        self.emotion_data = emotion_data
    def run(self):
        api_key = db.get_setting("api_key", "")
        base_url = db.get_setting("base_url", "")
        model_name = db.get_setting("model_name", "")
        if not api_key or not base_url or not model_name:
            msg = "⚠️ 还没配置模型信息。"
            self.response_ready.emit(msg, msg)
            return
            
        # 注入备忘录信息
        memos = db.get_all_memos()
        memo_str = "用户已记录的备忘信息：\n"
        for key, val, _, _ in memos:
            memo_str += f"- {key}: {val}\n"
            
        # 注入待办任务信息
        tasks = db.get_tasks_in_range(status='pending')
        task_str = "用户当前的待办任务：\n"
        if tasks:
            for _, t_time, content, _ in tasks:
                task_str += f"- {t_time}: {content}\n"
        else:
            task_str += "(暂无待办任务)\n"
            
        relevant = _find_relevant_history(self.user_text)
        history_injection = ""
        if relevant:
            if isinstance(relevant, list):
                lines = []
                for idx, tup in enumerate(relevant, start=1):
                    try:
                        u_text, a_text = tup
                    except Exception:
                        continue
                    lines.append(f"片段{idx} - 用户：{u_text}\n片段{idx} - 皮皮：{a_text}")
                if lines:
                    history_injection = '\n【重要】历史对话记录（用户可能在对其中提到的题目进行追问，你必须参考这些内容）：\n' + '\n'.join(lines) + '\n【注意】如果用户问"为什么"、"错在哪里"等问题，请基于上述历史记录中的题目内容回答，不要要求用户重新发送题目。\n'
            else:
                try:
                    u_text, a_text = relevant
                    history_injection = f'\n【重要】历史对话记录（用户可能在对其中提到的题目进行追问，你必须参考这些内容）：\n用户：{u_text}\n皮皮：{a_text}\n【注意】如果用户问"为什么"、"错在哪里"等问题，请基于上述历史记录中的题目内容回答，不要要求用户重新发送题目。\n'
                except Exception:
                    pass
        
        follow_up_hint = ""
        try:
            is_follow_up = _looks_like_follow_up(self.user_text) and not _is_history_recall_query(self.user_text)
        except Exception:
            is_follow_up = False
        if is_follow_up and history_injection:
            follow_up_hint = """
追问强约束（必须遵守）：
- 当前问题属于"追问/承接型问题"，你必须围绕上面的历史片段主题作答。
- 你的回复必须基于历史对话片段中的内容，特别是如果历史记录包含题目（标注为[图片]的对话），你必须基于该题目内容回答。
- 绝对禁止说"我需要看到具体题目"或"请把题目发给我"，因为题目已经在历史记录中。
- 如果用户问"为什么C错"或"A为什么对"，必须回顾历史记录中的上一道题目，分析该选项的具体错误原因。
"""

        img_ctx = ""
        try:
            s = (self.image_context or "").strip()
            if s:
                img_ctx = "\n本轮图片内容（仅供你理解，不要提及“识别/解析/多模态/模型”等后台词）：\n" + s + "\n"
        except Exception:
            img_ctx = ""

        selected_vendor = db.get_setting("chat_vendor", "")
        current_date = datetime.datetime.now().strftime("%Y-%m-%d")
        
        emotion_hint = ""
        if self.emotion_data:
            dominant_emotion = self.emotion_data.get("dominant_emotion", "neutral")
            dominant_score = self.emotion_data.get("dominant_score", 0.5)
            emotion_hint = f"\n[情感分析] 用户当前主导情感: {dominant_emotion} (置信度: {dominant_score:.2f})\n根据用户的情绪状态调整你的回复风格。\n"
        
        sys_prompt = f"""你是一个名叫皮皮的桌面助手。

输出格式强制要求：
1 必须只输出纯自然语言文本
2 一行一句 分段清晰
3 禁止输出任何 JSON 代码块 数组 对象
4 禁止输出花括号 方括号 英文引号
5 禁止提及后台处理过程
{follow_up_hint}

内部指令规则：
如果你需要系统执行操作 请额外输出若干行 以 操作 开头
这些操作行不会展示给用户
操作行格式 只能用下面这些
操作 设置备忘录 关键字 关键词 内容 内容
操作 查询备忘录 关键字 关键词
操作 列出备忘录
操作 添加提醒 时间 时间短语 内容 提醒内容
操作 列出提醒
操作 打开应用 名称 应用名
操作 关闭应用 名称 应用名
操作 查询知识库 问题 问题内容（仅在用户明确要求查询文档、手册或资料时使用）

拟人化回复规则（核心）：
1 称呼用户为"你"或"您"，保持亲切感
2 根据用户的情绪调整回复风格：
   - 用户情绪低落时，用温柔、支持的语气
   - 用户开心时，可以适当活泼俏皮
   - 用户提问时，保持专业但不死板
3 回复中适度加入情感表达：
   - 可以使用简单的表情符号如 :) (: 等
   - 用词要自然，不要过度正式或机械
4 保持对话的连贯性，记住之前聊过的内容
5 遇到不确定的事，直接说"我不太确定"而不是编造答案

时间规则：
1 只提取用户原话里的时间短语 不要自行换算成具体日期
2 如果用户没给明确时间 但想设置提醒 就用自然口语追问时间

生日规则：
如果用户让你记住生日 请把内容归一化为 X月Y日

题目与考试场景处理（重要）：
1 如果用户发送了包含题目的图片（如选择题、填空题、问答题等），你必须：
  - 第一行直接给出答案（如"答案是A"、"答案是xx"）
  - 然后空一行再给出详细解释
  - 不要先分析再给出答案
2 如果用户说"直接给出答案"、"直接输出答案"、"直接告诉我答案"、"为什么会错"、"为什么"、"错在哪里"等类似表述，这是对前一张图片题目的追问，必须基于历史记录中的题目内容回答
3 保持上下文连贯性：用户追问时，不要重置对话或忽略之前的图片内容
4 当用户问"为什么C错"或"A为什么对"时，必须基于上一道题目的内容分析具体选项

上下文与历史记录规则（极其重要）：
1 历史对话片段中可能包含用户发送的题目图片内容（标注为[图片]的对话）
2 用户说"直接给出答案"、"继续"、"然后呢"、"为什么会错"、"为什么"、"错在哪里"等表述时，这是对当前话题的追问，不是新话题
3 必须基于之前的对话内容（特别是上一张图片识别的题目内容）继续回答
4 不要以"你好"、"有什么可以帮你的"、"我需要看到具体题目"等开场白重新开始对话
5 历史对话片段中的信息必须被充分利用，特别是最近一次的题目内容
6 如果用户问某个选项为什么错（如"C为什么错"），你必须回顾历史记录中的上一道题目，分析该选项的错误原因

今天是 {current_date}

{memo_str}
{task_str}
{history_injection}
{emotion_hint}
"""
        
        try:
            sys_prompt = sys_prompt + (img_ctx if img_ctx else "")
            def _is_retryable_error(err: Exception) -> bool:
                try:
                    status_code = getattr(err, "status_code", None)
                    if status_code in (408, 409, 425, 429, 500, 502, 503, 504):
                        return True
                except Exception:
                    pass
                s = str(err or "")
                if "Error code: 429" in s or "RateLimitError" in s or re.search(r"\bHTTP\s*429\b", s):
                    return True
                if "temporarily overloaded" in s.lower():
                    return True
                if "timed out" in s.lower() or "timeout" in s.lower():
                    return True
                if "connection" in s.lower() and ("reset" in s.lower() or "aborted" in s.lower() or "refused" in s.lower()):
                    return True
                return False

            chunks = []
            got_stream_output = False
            last_err = None
            delays = (0.6, 1.2, 2.4)
            for attempt in range(len(delays) + 1):
                try:
                    chunks = []
                    got_stream_output = False
                    for chunk in chat_stream_unified(
                        api_key=api_key,
                        base_url=base_url,
                        model=model_name,
                        system_prompt=sys_prompt,
                        user_text=self.llm_text,
                        selected_vendor=selected_vendor,
                    ):
                        part = str(chunk or "")
                        if not part:
                            continue
                        got_stream_output = True
                        chunks.append(part)
                        self.response_chunk.emit(part)
                    last_err = None
                    break
                except Exception as e:
                    last_err = e
                    retryable = _is_retryable_error(e)
                    try:
                        print(f"[AIWorker] 流式请求失败(第{attempt+1}次): {e}")
                        if retryable and attempt < len(delays) and not got_stream_output:
                            d = float(delays[attempt])
                            j = (time.time() - int(time.time()))
                            wait_s = d * (1.0 + 0.25 * j)
                            print(f"[AIWorker] 将在 {wait_s:.2f}s 后重试")
                        else:
                            print("[AIWorker] 不重试")
                    except Exception:
                        pass
                    if retryable and attempt < len(delays) and not got_stream_output:
                        try:
                            time.sleep(wait_s)
                        except Exception:
                            pass
                        continue
                    break
            if last_err is not None and not chunks:
                raise last_err
            res = "".join(chunks).strip()
            if not res:
                raise RuntimeError("对话请求失败")
            self.response_ready.emit(res, res)
        except Exception as e:
            selected_vendor = db.get_setting("chat_vendor", "")
            vendor = _guess_chat_vendor(base_url, selected_vendor)
            msg = "⚠️ 连接失败，请稍后重试。"
            try:
                s = str(e or "")
                friendly_403 = _format_access_terminated_message(vendor=vendor, base_url=base_url, model=model_name, raw_error=s)
                if friendly_403:
                    msg = friendly_403
                else:
                    msg_low = s.lower()
                    if ("error code: 429" in msg_low) or ("temporarily overloaded" in msg_low) or re.search(r"\bhttp\s*429\b", msg_low):
                        msg = "⚠️ 服务繁忙，请稍后再试。"
            except Exception:
                msg = "⚠️ 连接失败，请稍后重试。"
            try:
                print(f"[AIWorker] {msg}")
                if "HTTP 403" not in str(e or ""):
                    print(traceback.format_exc())
            except Exception:
                pass
            self.response_ready.emit(msg, msg)

def _hash_file_sha256(file_path: str) -> str:
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def _encode_image_as_data_url(image_path: str) -> str:
    mime_type, _ = mimetypes.guess_type(image_path)
    if not mime_type:
        mime_type = "image/jpeg"
    with open(image_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")
    return f"data:{mime_type};base64,{b64}"

def _trigger_windows_screen_snip():
    try:
        user32 = ctypes.windll.user32
        KEYEVENTF_KEYUP = 0x0002
        VK_LWIN = 0x5B
        VK_SHIFT = 0x10
        VK_S = 0x53
        user32.keybd_event(VK_LWIN, 0, 0, 0)
        user32.keybd_event(VK_SHIFT, 0, 0, 0)
        user32.keybd_event(VK_S, 0, 0, 0)
        user32.keybd_event(VK_S, 0, KEYEVENTF_KEYUP, 0)
        user32.keybd_event(VK_SHIFT, 0, KEYEVENTF_KEYUP, 0)
        user32.keybd_event(VK_LWIN, 0, KEYEVENTF_KEYUP, 0)
        return True
    except Exception:
        return False

def _is_image_file_path(path: str) -> bool:
    try:
        ext = os.path.splitext(str(path))[1].lower()
    except Exception:
        ext = ""
    return ext in (".png", ".jpg", ".jpeg", ".bmp", ".webp", ".gif", ".tiff", ".tif")

def _save_qimage_to_clipboard_cache(img: QImage) -> str | None:
    if img is None or img.isNull():
        return None
    try:
        img_dir = os.path.join(APP_DATA_DIR, "clipboard_images")
        os.makedirs(img_dir, exist_ok=True)
        filename = f"{time.strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex}.png"
        saved_abs_path = os.path.join(img_dir, filename)
        ok = img.save(saved_abs_path, "PNG")
        if not ok:
            return None
        return saved_abs_path
    except Exception:
        return None

class ImageRecognitionWorker(QThread):
    result_ready = pyqtSignal(str, str, int)
    error_ready = pyqtSignal(str)

    def __init__(self, image_path: str, prompt: str = "", source: str = "ui"):
        super().__init__()
        self.image_path = image_path
        self.prompt = prompt
        self.source = source

    def run(self):
        vision_vendor = str(db.get_setting("vision_vendor", "") or "").strip()
        api_key = db.get_setting("vision_api_key", "") or db.get_setting("api_key", "")
        base_url = db.get_setting("vision_base_url", "") or db.get_setting("base_url", "")
        model_name = db.get_setting("vision_model_name", "") or db.get_setting("model_name", "")

        if not api_key or not base_url or not model_name:
            self.error_ready.emit("⚠️ 图片识别模型调用失败，请检查配置")
            return

        if not self.image_path or not os.path.exists(self.image_path):
            self.error_ready.emit("⚠️ 图片识别模型调用失败，请检查配置")
            return

        try:
            img_dir = os.path.join(APP_DATA_DIR, "image_recognitions")
            os.makedirs(img_dir, exist_ok=True)
            ext = os.path.splitext(self.image_path)[1] or ".jpg"
            filename = f"{time.strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex}{ext}"
            saved_abs_path = os.path.join(img_dir, filename)
            shutil.copy2(self.image_path, saved_abs_path)
            saved_rel_path = os.path.relpath(saved_abs_path, APP_DATA_DIR)
        except Exception as e:
            try:
                print(f"[ImageRecognitionWorker] 保存图片失败: {e}")
                print(traceback.format_exc())
            except Exception:
                pass
            self.error_ready.emit("⚠️ 图片识别模型调用失败，请检查配置")
            return

        try:
            image_sha256 = _hash_file_sha256(saved_abs_path)
            data_url = _encode_image_as_data_url(saved_abs_path)
            prompt = self.prompt.strip() if isinstance(self.prompt, str) else ""
            if not prompt:
                prompt = """请先判断图片内容类型：

如果是题目（选择题、填空题、判断题、问答题、计算题等）：
1. 第一行直接给出答案（如"答案是A"、"答案是xx"、"正确/错误"）
2. 第二行空行
3. 第三行开始给出简要解释

如果不是题目（普通图片、照片、截图等）：
请用中文详细描述这张图片里有什么。尽可能全面地识别图片中的各种元素、人物、场景、物品、颜色、动作等细节。

注意：只输出识别到的内容，不要提及"识别/解析/多模态/模型"等后台词。"""
            def _is_retryable_error(err: Exception) -> bool:
                try:
                    status_code = getattr(err, "status_code", None)
                    if status_code in (408, 409, 425, 429, 500, 502, 503, 504):
                        return True
                except Exception:
                    pass
                s = str(err or "")
                if re.search(r"\bHTTP\s*429\b", s) or "Error code: 429" in s or "RateLimitError" in s:
                    return True
                if "temporarily overloaded" in s.lower():
                    return True
                if "timed out" in s.lower() or "timeout" in s.lower():
                    return True
                if "connection" in s.lower() and ("reset" in s.lower() or "aborted" in s.lower() or "refused" in s.lower()):
                    return True
                return False

            recognized_text = None
            last_err = None
            delays = (0.8, 1.6, 3.2)
            for attempt in range(len(delays) + 1):
                try:
                    recognized_text = vision_recognize_unified(
                        api_key=str(api_key or ""),
                        base_url=str(base_url or ""),
                        model=str(model_name or ""),
                        prompt=str(prompt or ""),
                        image_data_url=str(data_url or ""),
                        selected_vendor=vision_vendor,
                    )
                    last_err = None
                    break
                except Exception as e:
                    last_err = e
                    retryable = _is_retryable_error(e)
                    try:
                        print(f"[ImageRecognitionWorker] 请求失败(第{attempt+1}次): {e}")
                        if retryable and attempt < len(delays):
                            d = float(delays[attempt])
                            j = (time.time() - int(time.time()))
                            wait_s = d * (1.0 + 0.25 * j)
                            print(f"[ImageRecognitionWorker] 将在 {wait_s:.2f}s 后重试")
                        else:
                            print("[ImageRecognitionWorker] 不重试")
                    except Exception:
                        pass
                    if retryable and attempt < len(delays):
                        try:
                            time.sleep(wait_s)
                        except Exception:
                            pass
                        continue
                    break

            if recognized_text is None:
                raise last_err if last_err is not None else RuntimeError("图片识别请求失败")
            recognized_text = str(recognized_text or "").strip()
            rec_id = 0
            try:
                rec_id = db.add_image_recognition(
                    source=self.source,
                    original_path=self.image_path,
                    saved_rel_path=saved_rel_path,
                    image_sha256=image_sha256,
                    prompt=prompt,
                    recognized_text=recognized_text,
                    model=model_name,
                )
            except Exception:
                rec_id = 0
            self.result_ready.emit(saved_abs_path, recognized_text, rec_id)
        except Exception as e:
            s = str(e or "")
            try:
                print(f"[ImageRecognitionWorker] 识别失败: {e}")
                print(traceback.format_exc())
            except Exception:
                pass
            if ("Error code: 429" in s) or ("temporarily overloaded" in s.lower()) or re.search(r"\bHTTP\s*429\b", s):
                self.error_ready.emit("⚠️ 图片识别模型调用失败，请稍后重试")
            else:
                self.error_ready.emit("⚠️ 图片识别模型调用失败，请检查配置")

# ===================== Fluent UI 界面 =====================

class ChatMessageWidget(CardWidget):
    stop_signal = pyqtSignal()
    BUBBLE_HORIZONTAL_PADDING = 24
    
    def __init__(self, text, is_user=True, parent=None, image_path: str | None = None):
        super().__init__(parent)
        self.is_user = bool(is_user)
        self.layout = QVBoxLayout(self)
        self.layout.setSpacing(6)
        self.imageLabel = QLabel(self)
        self.imageLabel.setScaledContents(True)
        self.imageLabel.setAlignment(Qt.AlignLeft)
        self.imageLabel.hide()
        self.layout.addWidget(self.imageLabel)
        self.loadingLabel = QLabel(self)
        self.loadingLabel.setAlignment(Qt.AlignCenter)
        self.loadingLabel.hide()
        self.layout.addWidget(self.loadingLabel, 0, Qt.AlignHCenter)
        self.label = BodyLabel(text)
        self.label.setWordWrap(True)
        try:
            self.label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        except Exception:
            pass
        try:
            self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
            self.setMaximumWidth(920)
            self.label.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
            self.label.setMaximumWidth(860)
            self.label.setMinimumWidth(120)
        except Exception:
            pass
        self.layout.addWidget(self.label)
        self.set_image(image_path)
        self._loading_movie = None
        self._normal_style = ""
        self._normal_margins = None
        self._normal_size_policy = None
        self._is_waiting = False
        
        # 停止播报按钮（仅助手消息添加）
        if not is_user:
            self.stopBtn = TransparentToolButton(FIF.CLOSE, self)
            self.stopBtn.setFixedSize(20, 20)
            self.stopBtn.setIconSize(QSize(10, 10))
            self.stopBtn.setToolTip("停止播报")
            self.stopBtn.clicked.connect(self.on_stop_clicked)
            self.stopBtn.hide() # 默认隐藏
            
            # 按钮布局：右下角
            self.btnLayout = QHBoxLayout()
            self.btnLayout.addStretch(1)
            self.btnLayout.addWidget(self.stopBtn)
            self.btnLayout.setContentsMargins(0, 0, 0, 0)
            self.layout.addLayout(self.btnLayout)
        else:
            self.stopBtn = None

        try:
            self.label.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        except Exception:
            try:
                self.label.setAlignment(Qt.AlignLeft)
            except Exception:
                pass

        is_dark = db.get_setting("dark_mode", "False") == "True"
        self.apply_theme(is_dark)
        
        self.layout.setContentsMargins(12, 8, 12, 8)
        try:
            self._normal_style = self.styleSheet()
            m = self.layout.contentsMargins()
            self._normal_margins = (m.left(), m.top(), m.right(), m.bottom())
            self._normal_size_policy = self.sizePolicy()
        except Exception:
            self._normal_style = self.styleSheet()
            self._normal_margins = None
            self._normal_size_policy = None

    def apply_theme(self, is_dark: bool | None = None):
        if is_dark is None:
            is_dark = db.get_setting("dark_mode", "False") == "True"
        is_dark = bool(is_dark)

        if self.is_user:
            if is_dark:
                bg = "#002b5e"
            else:
                bg = "#1677ff"
            style = f"ChatMessageWidget {{ background-color: {bg}; border-radius: 10px; }}"
            text_color = Qt.white
            btn_bg = "rgba(255,255,255,0.10)"
        else:
            if is_dark:
                bg = "#454545"
                text_color = Qt.white
                border = ""
                btn_bg = "rgba(255,255,255,0.10)"
            else:
                bg = "#e6e6e6"
                text_color = Qt.black
                border = " border: 1px solid rgba(0,0,0,0.06);"
                btn_bg = "rgba(0,0,0,0.06)"
            style = f"ChatMessageWidget {{ background-color: {bg}; border-radius: 10px;{border} }}"

        try:
            self._normal_style = style
        except Exception:
            pass

        if not getattr(self, "_is_waiting", False):
            try:
                self.setStyleSheet(style)
            except Exception:
                pass

        try:
            self.label.setTextColor(text_color, text_color)
        except Exception:
            pass

        if self.stopBtn:
            try:
                self.stopBtn.setStyleSheet(f"background-color: {btn_bg}; border-radius: 10px;")
            except Exception:
                pass

    def paintEvent(self, event):
        if getattr(self, "_is_waiting", False):
            return
        return super().paintEvent(event)

    def start_waiting(self, keep_text: bool = False):
        try:
            if self._loading_movie is None:
                if os.path.exists(LOADING_GIF_FILE):
                    self._loading_movie = QMovie(LOADING_GIF_FILE)
                    try:
                        self._loading_movie.setScaledSize(QSize(96, 96))
                    except Exception:
                        pass
                    self.loadingLabel.setMovie(self._loading_movie)
            if self._loading_movie is not None:
                self._is_waiting = True
                try:
                    self.setAttribute(Qt.WA_TranslucentBackground, True)
                    self.setAutoFillBackground(False)
                    self.setStyleSheet("ChatMessageWidget { background: transparent; background-color: transparent; border: none; }")
                    self.layout.setContentsMargins(0, 0, 0, 0)
                    self.layout.setSpacing(0)
                    self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
                except Exception:
                    pass
                try:
                    self.loadingLabel.setStyleSheet("background: transparent; border: none;")
                except Exception:
                    pass
                self.loadingLabel.show()
                try:
                    self._loading_movie.start()
                except Exception:
                    pass
                if not keep_text:
                    self.label.hide()
        except Exception:
            pass

    def stop_waiting(self):
        try:
            if self._loading_movie is not None:
                try:
                    self._loading_movie.stop()
                except Exception:
                    pass
            self.loadingLabel.hide()
            self._is_waiting = False
            try:
                if self._normal_style:
                    self.setStyleSheet(self._normal_style)
                if isinstance(self._normal_margins, tuple) and len(self._normal_margins) == 4:
                    self.layout.setContentsMargins(*self._normal_margins)
                else:
                    self.layout.setContentsMargins(12, 8, 12, 8)
                if self._normal_size_policy is not None:
                    self.setSizePolicy(self._normal_size_policy)
            except Exception:
                pass
            self.label.show()
        except Exception:
            pass

    def set_image(self, image_path: str | None):
        try:
            if not image_path:
                self.imageLabel.hide()
                self.imageLabel.clear()
                return
            p = str(image_path)
            if not os.path.exists(p):
                self.imageLabel.hide()
                self.imageLabel.clear()
                return
            pix = QPixmap(p)
            if pix.isNull():
                self.imageLabel.hide()
                self.imageLabel.clear()
                return
            max_w = 240
            if pix.width() > max_w:
                pix = pix.scaledToWidth(max_w, Qt.SmoothTransformation)
            self.imageLabel.setPixmap(pix)
            self.imageLabel.show()
        except Exception:
            try:
                self.imageLabel.hide()
                self.imageLabel.clear()
            except Exception:
                pass

    def set_text(self, text: str):
        try:
            self.label.setText(str(text or ""))
            self.label.adjustSize()
            self.adjustSize()
            self.updateGeometry()
            if self.parentWidget() is not None:
                self.parentWidget().adjustSize()
        except Exception:
            pass

    def append_text(self, text: str):
        part = str(text or "")
        if not part:
            return
        try:
            current = self.label.text() or ""
        except Exception:
            current = ""
        try:
            self.label.setText(current + part)
            self.label.adjustSize()
            self.adjustSize()
            self.updateGeometry()
            if self.parentWidget() is not None:
                self.parentWidget().adjustSize()
        except Exception:
            pass

    def on_stop_clicked(self):
        if self.stopBtn:
            self.stopBtn.hide()
            self.stop_signal.emit()

    def show_stop_button(self):
        if self.stopBtn:
            self.stopBtn.show()

    def hide_stop_button(self):
        if self.stopBtn:
            self.stopBtn.hide()

class ChatLineEdit(LineEdit):
    """支持统一剪贴板粘贴的输入框"""
    image_pasted = pyqtSignal(str)  # 粘贴图片时发出信号
    clipboard_paste_requested = pyqtSignal()  # 请求主窗口按统一逻辑处理 Ctrl+V
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._clipboard = QApplication.clipboard()
        self._clipboard_enabled_checker = None

    def set_clipboard_enabled_checker(self, checker):
        self._clipboard_enabled_checker = checker
    
    def keyPressEvent(self, event: QKeyEvent):
        # 检测 Ctrl+V 粘贴
        if event.key() == Qt.Key_V and event.modifiers() == Qt.ControlModifier:
            clipboard_enabled = False
            try:
                if callable(self._clipboard_enabled_checker):
                    clipboard_enabled = bool(self._clipboard_enabled_checker())
            except Exception:
                clipboard_enabled = False

            if clipboard_enabled:
                self.clipboard_paste_requested.emit()
                return

            if self._try_paste_image():
                return  # 成功粘贴图片，不执行默认的文本粘贴
        super().keyPressEvent(event)
    
    def _try_paste_image(self) -> bool:
        """尝试从剪贴板粘贴图片，返回是否成功"""
        try:
            md = self._clipboard.mimeData()
            if not md:
                return False
            
            # 检查是否有图片数据
            if md.hasImage():
                img = self._clipboard.image()
                if not img.isNull():
                    saved_path = self._save_qimage_to_temp(img)
                    if saved_path:
                        self.image_pasted.emit(saved_path)
                        return True
            
            # 检查是否有文件路径（图片文件）
            if md.hasUrls():
                urls = md.urls()
                for url in urls:
                    path = url.toLocalFile()
                    if path and os.path.isfile(path):
                        # 检查是否是图片文件
                        ext = os.path.splitext(path)[1].lower()
                        if ext in ('.png', '.jpg', '.jpeg', '.bmp', '.gif', '.webp'):
                            self.image_pasted.emit(path)
                            return True
        except Exception as e:
            print(f"[ChatLineEdit] 粘贴图片失败: {e}")
        return False
    
    def _save_qimage_to_temp(self, img: QImage) -> str | None:
        """将 QImage 保存到临时文件"""
        try:
            img_dir = os.path.join(APP_DATA_DIR, "clipboard_images")
            os.makedirs(img_dir, exist_ok=True)
            filename = f"clipboard_{time.strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}.png"
            filepath = os.path.join(img_dir, filename)
            if img.save(filepath, "PNG"):
                return filepath
        except Exception as e:
            print(f"[ChatLineEdit] 保存剪贴板图片失败: {e}")
        return None

class ChatPage(QFrame):
    BUBBLE_WIDTH_RATIO = 2 / 3
    BUBBLE_MAX_WIDTH = 1280
    BUBBLE_SIDE_PADDING = 44

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ChatPage")
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(6, 6, 6, 6)
        self.layout.setSpacing(6)
        
        # 微信状态指示
        self.statusLayout = QHBoxLayout()
        self.statusIcon = QLabel(self)
        self.statusIcon.setFixedSize(16, 16)
        self.statusIcon.setStyleSheet("border-radius: 8px; background-color: gray;")
        self.statusLabel = BodyLabel("微信未连接", self)
        
        # 统一的工具按钮样式
        tool_btn_style = """
            QToolButton {
                background: transparent;
                border: none;
                border-radius: 6px;
                padding: 4px;
            }
            QToolButton:hover {
                background: rgba(128, 128, 128, 30);
            }
            QToolButton:pressed {
                background: rgba(128, 128, 128, 50);
            }
        """
        
        # 刷新按钮
        self.refreshBtn = TransparentToolButton(FIF.SYNC, self)
        self.refreshBtn.setFixedSize(28, 28)
        self.refreshBtn.setIconSize(QSize(14, 14))
        self.refreshBtn.setToolTip("手动刷新微信状态")
        self.refreshBtn.setStyleSheet(tool_btn_style)
        
        # 动画相关
        self.refreshTimer = QTimer(self)
        self.refreshTimer.timeout.connect(self._rotate_icon)
        self.angle = 0
        self._original_icon = FIF.SYNC
        
        # 新建对话按钮
        self.newChatBtn = TransparentToolButton(FIF.ADD, self)
        self.newChatBtn.setFixedSize(28, 28)
        self.newChatBtn.setIconSize(QSize(14, 14))
        self.newChatBtn.setToolTip("新建对话：清空当前对话，开启全新对话")
        self.newChatBtn.setStyleSheet(tool_btn_style)
        
        # 历史对话按钮
        self.historyBtn = TransparentToolButton(FIF.HISTORY, self)
        self.historyBtn.setFixedSize(28, 28)
        self.historyBtn.setIconSize(QSize(14, 14))
        self.historyBtn.setToolTip("历史对话：查看并切换历史聊天记录")
        self.historyBtn.setStyleSheet(tool_btn_style)
        
        self.statusLayout.addWidget(self.statusIcon)
        self.statusLayout.addWidget(self.statusLabel)
        self.statusLayout.addSpacing(8)
        self.statusLayout.addWidget(self.refreshBtn)
        self.statusLayout.addStretch(1)
        self.statusLayout.addWidget(self.newChatBtn)
        self.statusLayout.addWidget(self.historyBtn)
        self.layout.addLayout(self.statusLayout)
        
        # 主内容区（左侧聊天区 + 右侧历史面板）
        self.contentLayout = QHBoxLayout()
        self.contentLayout.setContentsMargins(0, 0, 0, 0)
        self.contentLayout.setSpacing(0)
        
        # 左侧消息区域
        self.scrollArea = ScrollArea(self)
        self.scrollWidget = QWidget()
        self.scrollLayout = QVBoxLayout(self.scrollWidget)
        self.scrollLayout.setAlignment(Qt.AlignTop)
        self.scrollLayout.setContentsMargins(14, 12, 14, 18)
        self.scrollLayout.setSpacing(12)
        self.scrollArea.setWidget(self.scrollWidget)
        self.scrollArea.setWidgetResizable(True)
        self.scrollArea.setStyleSheet("background: transparent; border: none;")
        
        # 右侧历史对话面板（默认隐藏）
        self.historyPanel = HistoryPanel(self)
        self.historyPanel.hide()
        
        # 添加到内容布局
        self.contentLayout.addWidget(self.scrollArea, 1)
        self.contentLayout.addWidget(self.historyPanel)
        self.layout.addLayout(self.contentLayout)
        self.layout.setStretchFactor(self.contentLayout, 1)

        self.attachmentWidget = QFrame(self)
        self.attachmentLayout = QHBoxLayout(self.attachmentWidget)
        self.attachmentLayout.setContentsMargins(0, 0, 0, 0)
        self.attachmentPreview = QLabel(self.attachmentWidget)
        self.attachmentPreview.setFixedSize(48, 48)
        self.attachmentPreview.setScaledContents(True)
        self.attachmentName = BodyLabel("", self.attachmentWidget)
        self.attachmentRemoveBtn = TransparentToolButton(FIF.CLOSE, self.attachmentWidget)
        self.attachmentRemoveBtn.setFixedSize(28, 28)
        self.attachmentRemoveBtn.setIconSize(QSize(12, 12))
        self.attachmentRemoveBtn.setToolTip("移除图片")
        self.attachmentLayout.addWidget(self.attachmentPreview)
        self.attachmentLayout.addSpacing(8)
        self.attachmentLayout.addWidget(self.attachmentName, 1)
        self.attachmentLayout.addWidget(self.attachmentRemoveBtn)
        self.attachmentWidget.hide()

        self.inputLayout = QHBoxLayout()
        self.lineEdit = ChatLineEdit(self)
        self.lineEdit.setPlaceholderText("在这里输入指令或聊天内容...")
        
        # 统一的工具按钮样式（与顶部按钮一致）
        input_btn_style = """
            QToolButton {
                background: transparent;
                border: none;
                border-radius: 6px;
                padding: 4px;
            }
            QToolButton:hover {
                background: rgba(128, 128, 128, 30);
            }
            QToolButton:pressed {
                background: rgba(128, 128, 128, 50);
            }
        """
        
        self.sendBtn = PrimaryPushButton(FIF.SEND, "发送", self)
        self.sendBtn.setToolTip("发送消息")
        
        self.imageBtn = TransparentToolButton(FIF.PHOTO, self)
        self.imageBtn.setFixedSize(28, 28)
        self.imageBtn.setIconSize(QSize(14, 14))
        self.imageBtn.setToolTip("上传图片：选择本地图片发送给AI识别")
        self.imageBtn.setStyleSheet(input_btn_style)
        
        self.snipBtn = TransparentToolButton(FIF.CUT, self)
        self.snipBtn.setFixedSize(28, 28)
        self.snipBtn.setIconSize(QSize(14, 14))
        self.snipBtn.setToolTip("截图：截取屏幕内容发送给AI")
        self.snipBtn.setStyleSheet(input_btn_style)
        
        self.voiceBtn = TransparentToolButton(FIF.MICROPHONE, self)
        self.voiceBtn.setFixedSize(28, 28)
        self.voiceBtn.setIconSize(QSize(14, 14))
        self.voiceBtn.setToolTip("语音输入：点击开始语音说话")
        self.voiceBtn.setStyleSheet(input_btn_style)

        self.inputLayout.addWidget(self.snipBtn)
        self.inputLayout.addWidget(self.lineEdit)
        self.inputLayout.addWidget(self.imageBtn)
        self.inputLayout.addWidget(self.voiceBtn)
        self.inputLayout.addWidget(self.sendBtn)
        
        self.layout.addWidget(self.attachmentWidget)
        self.layout.addLayout(self.inputLayout)

    def start_loading_animation(self):
        print("[ChatPage] 启动刷新动画")
        self.angle = 0
        self.refreshBtn.setEnabled(False)
        self.refreshTimer.start(50)

    def stop_loading_animation(self):
        print("[ChatPage] 停止刷新动画")
        if self.refreshTimer.isActive():
            self.refreshTimer.stop()
        self.refreshBtn.setIcon(self._original_icon)
        self.refreshBtn.setEnabled(True)

    def _rotate_icon(self):
        self.angle = (self.angle + 20) % 360
        pixmap = self._original_icon.icon().pixmap(14, 14)
        transform = QTransform().rotate(self.angle)
        rotated_pixmap = pixmap.transformed(transform, Qt.SmoothTransformation)
        self.refreshBtn.setIcon(QIcon(rotated_pixmap))

    def _bubble_width_limits(self):
        viewport_w = max(320, self.scrollArea.viewport().width())
        bubble_max = min(self.BUBBLE_MAX_WIDTH, int(viewport_w * self.BUBBLE_WIDTH_RATIO))
        text_max = max(260, bubble_max - self.BUBBLE_SIDE_PADDING)
        return bubble_max, text_max

    def add_message(self, text, is_user=True, image_path: str | None = None, center: bool = False):
        msg = ChatMessageWidget(text, is_user, image_path=image_path)
        if center:
            self.scrollLayout.addWidget(msg, 0, Qt.AlignHCenter)
        else:
            self.scrollLayout.addWidget(msg, 0, Qt.AlignRight if is_user else Qt.AlignLeft)
        try:
            bubble_max, text_max = self._bubble_width_limits()
            msg.setMaximumWidth(bubble_max)
            if hasattr(msg, "label"):
                msg.label.setMaximumWidth(text_max)
        except Exception:
            pass
        self.scroll_to_bottom()
        return msg

    def set_message_alignment(self, msg, alignment):
        if msg is None:
            return
        try:
            idx = self.scrollLayout.indexOf(msg)
            if idx < 0:
                return
            self.scrollLayout.removeWidget(msg)
            self.scrollLayout.insertWidget(idx, msg, 0, alignment)
            msg.show()
        except Exception:
            pass

    def scroll_to_bottom(self):
        def _scroll():
            try:
                bar = self.scrollArea.verticalScrollBar()
                bar.setValue(bar.maximum())
            except Exception:
                pass
        QTimer.singleShot(0, _scroll)
        QTimer.singleShot(80, _scroll)

    def update_message_theme(self, is_dark: bool | None = None):
        if is_dark is None:
            is_dark = db.get_setting("dark_mode", "False") == "True"
        is_dark = bool(is_dark)
        try:
            for i in range(self.scrollLayout.count()):
                item = self.scrollLayout.itemAt(i)
                w = item.widget() if item else None
                if isinstance(w, ChatMessageWidget):
                    w.apply_theme(is_dark)
        except Exception:
            pass

    def update_bubble_widths(self):
        try:
            bubble_max, text_max = self._bubble_width_limits()
            for i in range(self.scrollLayout.count()):
                item = self.scrollLayout.itemAt(i)
                w = item.widget() if item else None
                if isinstance(w, ChatMessageWidget):
                    w.setMaximumWidth(bubble_max)
                    if hasattr(w, "label"):
                        w.label.setMaximumWidth(text_max)
        except Exception:
            pass

    def set_pending_image(self, image_path: str | None):
        if not image_path:
            self.attachmentPreview.clear()
            self.attachmentName.setText("")
            self.attachmentWidget.hide()
            return
        p = str(image_path)
        pix = QPixmap(p)
        if pix.isNull():
            self.attachmentPreview.clear()
            self.attachmentName.setText("")
            self.attachmentWidget.hide()
            return
        if pix.width() > 128 or pix.height() > 128:
            pix = pix.scaled(128, 128, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.attachmentPreview.setPixmap(pix)
        self.attachmentName.setText(os.path.basename(p))
        self.attachmentWidget.show()

    # ========== 对话管理功能 ==========
    
    def new_conversation(self):
        """新建对话 - 只清空界面，不立即创建数据库记录"""
        # 检查当前对话是否有用户发送的问题（消息）
        has_messages = False
        if hasattr(self, 'current_conv_id') and self.current_conv_id:
            current_conv = db.get_conversation(self.current_conv_id)
            if current_conv and current_conv.get("messages"):
                has_messages = True
        
        # 清空界面
        self._clear_chat_content()
        
        # 重置当前对话ID为None，表示还没有创建对话
        # 只有当用户发送第一条消息时才会真正创建对话
        self.current_conv_id = None
        
        # 如果之前的对话有消息，提示用户已保存
        if has_messages:
            InfoBar.success(
                "新建对话", 
                "已进入新对话，之前的对话已保存", 
                duration=2000, 
                parent=self
            )
        else:
            InfoBar.success(
                "新建对话", 
                "已进入新对话，可以开始提问了", 
                duration=2000, 
                parent=self
            )
    
    def open_history_panel(self):
        """打开/关闭历史对话面板"""
        if self.historyPanel.isVisible():
            self.historyPanel.hide()
        else:
            # 检查当前对话是否有消息
            current_has_messages = False
            if hasattr(self, 'current_conv_id') and self.current_conv_id:
                current_conv = db.get_conversation(self.current_conv_id)
                if current_conv and current_conv.get("messages"):
                    current_has_messages = True
            self.historyPanel.refresh(self.current_conv_id, current_has_messages)
            self.historyPanel.show()
    
    def load_conversation(self, conv_id: int):
        """加载指定对话"""
        # 检查当前对话是否有用户发送的问题（消息），如果有则提醒保存
        has_messages = False
        if hasattr(self, 'current_conv_id') and self.current_conv_id:
            current_conv = db.get_conversation(self.current_conv_id)
            if current_conv and current_conv.get("messages"):
                has_messages = True
        
        # 如果有消息，显示保存提醒；如果是空的，直接切换不提醒
        if has_messages:
            InfoBar.info(
                "切换提醒", 
                "当前对话已保存，正在切换到历史对话", 
                duration=2000, 
                parent=self
            )
        
        # 获取对话数据
        conv = db.get_conversation(conv_id)
        if not conv:
            InfoBar.error("错误", "无法加载该对话", duration=2000, parent=self)
            return
        
        # 设置为活跃对话
        db.set_active_conversation(conv_id)
        self.current_conv_id = conv_id
        
        # 清空当前界面
        self._clear_chat_content()
        
        # 加载消息
        messages = conv.get("messages", [])
        for msg in messages:
            self.add_message(
                msg.get("text", ""),
                is_user=msg.get("is_user", True),
                image_path=msg.get("image_path")
            )
        
        # 刷新历史面板（加载历史对话后，当前对话就是这个历史对话）
        self.historyPanel.refresh(self.current_conv_id, True)
        
        # 滚动到底部
        self.scroll_to_bottom()
        
        InfoBar.success("切换成功", f"已加载历史对话：{conv.get('title', '新对话')}", duration=2000, parent=self)
    
    def _ensure_conversation(self, title: str = ""):
        """确保当前界面绑定到一个有效对话"""
        current_id = getattr(self, 'current_conv_id', None)
        if current_id:
            return current_id

        conv_id = db.ensure_active_conversation(title or "新对话")
        self.current_conv_id = conv_id
        return conv_id

    def append_message_to_current_conversation(self, text: str, is_user: bool, image_path: str = None):
        """向当前对话追加消息，并在首次发送时创建对话"""
        text = str(text or "")
        title = text[:20] if text else "新对话"
        is_new_conversation = not bool(getattr(self, 'current_conv_id', None))
        conv_id = self._ensure_conversation(title)
        if not conv_id:
            return

        db.append_conversation_message(conv_id, text, is_user, image_path)

        if is_new_conversation:
            self.historyPanel.refresh(self.current_conv_id, True)

    def add_message_to_conversation(self, text: str, is_user: bool, image_path: str = None):
        """兼容旧调用，内部统一走追加逻辑"""
        self.append_message_to_current_conversation(text, is_user, image_path)

    def _save_current_conversation(self):
        """保存当前对话到数据库"""
        # 当前对话通过add_message_to_conversation已经实时保存了
        # 这个方法用于在切换对话时确保数据一致性
        pass
    
    def _clear_chat_content(self):
        """清空聊天界面内容"""
        while self.scrollLayout.count():
            item = self.scrollLayout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

class TaskPage(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("TaskPage")
        self.layout = QVBoxLayout(self)
        self.title = SubtitleLabel("待办任务列表", self)
        
        # Toolbar
        self.toolbar = QHBoxLayout()
        self.btnAdd = PrimaryPushButton("添加", self)
        self.btnEdit = PrimaryPushButton("编辑", self)
        self.btnDel = PrimaryPushButton("删除", self)
        self.btnRefresh = PrimaryPushButton("刷新", self)
        
        self.toolbar.addWidget(self.btnAdd)
        self.toolbar.addWidget(self.btnEdit)
        self.toolbar.addWidget(self.btnDel)
        self.toolbar.addWidget(self.btnRefresh)
        self.toolbar.addStretch(1)
        
        self.listWidget = ListWidget(self)
        self.layout.addWidget(self.title)
        self.layout.addLayout(self.toolbar)
        self.layout.addWidget(self.listWidget)
        
        self.btnAdd.clicked.connect(self.on_add)
        self.btnEdit.clicked.connect(self.on_edit)
        self.btnDel.clicked.connect(self.on_delete)
        self.btnRefresh.clicked.connect(self.refresh)
        
        self.refresh()

    def refresh(self):
        self.listWidget.clear()
        # tasks = db.get_tasks_in_range() # 可能会过滤掉一些任务
        # 使用 get_all_tasks 并排序
        tasks = db.get_all_tasks()
        print(f"[TaskPage] get_all_tasks returned {len(tasks)} tasks")
        # tasks: (id, time, content, status, timestamp)
        # 按时间排序（简单的字符串比较，可能不准确，但在大多数情况下 ISO 格式是可以的）
        # 这里最好在 DBManager 中按时间排序
        
        # 简单过滤 pending 状态并显示
        pending_tasks = [t for t in tasks if t[3] == 'pending']
        pending_tasks.sort(key=lambda x: x[1]) # 按时间排序
        print(f"[TaskPage] filtered {len(pending_tasks)} pending tasks")
        
        for t_id, t_time, content, status, ts in pending_tasks:
            item = QListWidgetItem(f"⏰ {t_time} | {content}")
            item.setData(Qt.UserRole, {"id": t_id, "time": t_time, "content": content})
            
            # 显式设置字体颜色，防止看不清
            is_dark = db.get_setting("dark_mode", "False") == "True"
            text_color = "white" if is_dark else "black"
            item.setForeground(QColor(text_color))
            
            self.listWidget.addItem(item)

    def on_add(self):
        print("[TaskPage] on_add clicked")
        dlg = QDialog(self)
        dlg.setWindowTitle("添加提醒")
        dlg.resize(400, 200)
        # 移除问号按钮
        dlg.setWindowFlags(dlg.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        
        layout = QVBoxLayout(dlg)
        
        form = QFormLayout()
        # 使用原生 QLineEdit 以确保兼容性
        et_time = NativeLineEdit()
        et_time.setPlaceholderText("例如：10分钟后、1小时后、明天下午3点、15:30")
        et_content = NativeLineEdit()
        et_content.setPlaceholderText("提醒内容")
        form.addRow("时间：", et_time)
        form.addRow("内容：", et_content)
        
        layout.addLayout(form)
        
        btns = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        layout.addWidget(btns)
        
        btns.accepted.connect(dlg.accept)
        btns.rejected.connect(dlg.reject)
        
        if dlg.exec_() == QDialog.Accepted:
            t_str = et_time.text().strip()
            content = et_content.text().strip()
            if not t_str or not content:
                InfoBar.warning("错误", "时间和内容不能为空", duration=2000, parent=self)
                return
            
            # 使用时间解析器转换自然语言时间
            try:
                dt = parse_natural_time_expression_to_datetime(t_str)
                final_time_str = dt.strftime("%Y-%m-%d %H:%M:%S")
            except Exception as e:
                print(f"Time parse error: {e}")
                final_time_str = t_str # Fallback
            if isinstance(dt, datetime.datetime) and dt <= datetime.datetime.now():
                InfoBar.error("错误", "提醒时间必须晚于当前时间", duration=2500, parent=self)
                return
            db.add_task(final_time_str, content)
            print(f"[TaskPage] db.add_task called with {final_time_str}, {content}")
            self.refresh()
            InfoBar.success("成功", f"提醒已添加：{final_time_str}", duration=2000, parent=self)

    def on_edit(self):
        item = self.listWidget.currentItem()
        if not item:
            InfoBar.warning("提示", "请先选择一项", duration=2000, parent=self)
            return
        data = item.data(Qt.UserRole)
        t_id = data['id']
        old_time = data['time']
        old_content = data['content']
        
        dlg = QDialog(self)
        dlg.setWindowTitle("编辑提醒")
        dlg.resize(400, 200)
        layout = QVBoxLayout(dlg)
        
        form = QFormLayout()
        et_time = LineEdit()
        et_time.setText(old_time)
        et_content = LineEdit()
        et_content.setText(old_content)
        form.addRow("时间：", et_time)
        form.addRow("内容：", et_content)
        
        layout.addLayout(form)
        
        btns = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        layout.addWidget(btns)
        
        btns.accepted.connect(dlg.accept)
        btns.rejected.connect(dlg.reject)
        
        if dlg.exec_() == QDialog.Accepted:
            new_time = et_time.text().strip()
            new_content = et_content.text().strip()
            if not new_time or not new_content:
                InfoBar.warning("错误", "时间和内容不能为空", duration=2000, parent=self)
                return
            
            # 使用时间解析器转换自然语言时间
            try:
                dt = parse_natural_time_expression_to_datetime(new_time)
                final_time_str = dt.strftime("%Y-%m-%d %H:%M:%S")
            except Exception as e:
                print(f"Time parse error: {e}")
                final_time_str = new_time
            if isinstance(dt, datetime.datetime) and dt <= datetime.datetime.now():
                InfoBar.error("错误", "提醒时间必须晚于当前时间", duration=2500, parent=self)
                return
            db.update_task(t_id, final_time_str, new_content)
            self.refresh()
            InfoBar.success("成功", f"提醒已更新：{final_time_str}", duration=2000, parent=self)

    def on_delete(self):
        item = self.listWidget.currentItem()
        if not item:
            InfoBar.warning("提示", "请先选择一项", duration=2000, parent=self)
            return
        data = item.data(Qt.UserRole)
        t_id = data['id']
        
        w = MessageBox("确认删除", "确定要删除这条提醒吗？", self)
        if w.exec():
            db.delete_task_with_log(t_id)
            self.refresh()
            InfoBar.success("成功", "提醒已删除", duration=2000, parent=self)


class MemoPage(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("MemoPage")
        self.layout = QVBoxLayout(self)
        self.title = SubtitleLabel("我的备忘录", self)
        
        # Toolbar
        self.toolbar = QHBoxLayout()
        self.btnAdd = PrimaryPushButton("添加", self)
        self.btnEdit = PrimaryPushButton("编辑", self)
        self.btnDel = PrimaryPushButton("删除", self)
        self.btnRefresh = PrimaryPushButton("刷新", self)
        
        self.toolbar.addWidget(self.btnAdd)
        self.toolbar.addWidget(self.btnEdit)
        self.toolbar.addWidget(self.btnDel)
        self.toolbar.addWidget(self.btnRefresh)
        self.toolbar.addStretch(1)
        
        self.listWidget = ListWidget(self)
        self.layout.addWidget(self.title)
        self.layout.addLayout(self.toolbar)
        self.layout.addWidget(self.listWidget)
        
        self.btnAdd.clicked.connect(self.on_add)
        self.btnEdit.clicked.connect(self.on_edit)
        self.btnDel.clicked.connect(self.on_delete)
        self.btnRefresh.clicked.connect(self.refresh)
        
        self.refresh()

    def refresh(self):
        self.listWidget.clear()
        memos = db.get_all_memos()
        for key, val, ts, ut in memos:
            item = QListWidgetItem(f"📌 {key}: {val}")
            item.setData(Qt.UserRole, {"key": key, "value": val})
            self.listWidget.addItem(item)
            
    def on_add(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("添加备忘录")
        dlg.resize(400, 200)
        # 移除问号按钮
        dlg.setWindowFlags(dlg.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        layout = QVBoxLayout(dlg)
        
        form = QFormLayout()
        et_key = NativeLineEdit()
        et_key.setPlaceholderText("关键词")
        et_value = NativeLineEdit()
        et_value.setPlaceholderText("内容")
        form.addRow("关键词：", et_key)
        form.addRow("内容：", et_value)
        
        layout.addLayout(form)
        
        btns = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        layout.addWidget(btns)
        
        btns.accepted.connect(dlg.accept)
        btns.rejected.connect(dlg.reject)
        
        if dlg.exec_() == QDialog.Accepted:
            key = et_key.text().strip()
            val = et_value.text().strip()
            if not key or not val:
                InfoBar.warning("错误", "关键词和内容不能为空", duration=2000, parent=self)
                return
            
            db.add_memo(key, val)
            self.refresh()
            InfoBar.success("成功", "备忘录已添加", duration=2000, parent=self)

    def on_edit(self):
        item = self.listWidget.currentItem()
        if not item:
            InfoBar.warning("提示", "请先选择一项", duration=2000, parent=self)
            return
        data = item.data(Qt.UserRole)
        old_key = data['key']
        old_val = data['value']
        
        dlg = QDialog(self)
        dlg.setWindowTitle("编辑备忘录")
        dlg.resize(400, 200)
        layout = QVBoxLayout(dlg)
        
        form = QFormLayout()
        et_key = LineEdit()
        et_key.setText(old_key)
        et_key.setReadOnly(True)
        et_value = LineEdit()
        et_value.setText(old_val)
        form.addRow("关键词：", et_key)
        form.addRow("内容：", et_value)
        
        layout.addLayout(form)
        
        btns = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        layout.addWidget(btns)
        
        btns.accepted.connect(dlg.accept)
        btns.rejected.connect(dlg.reject)
        
        if dlg.exec_() == QDialog.Accepted:
            new_val = et_value.text().strip()
            if not new_val:
                InfoBar.warning("错误", "内容不能为空", duration=2000, parent=self)
                return
            
            db.update_memo(old_key, new_val)
            self.refresh()
            InfoBar.success("成功", "备忘录已更新", duration=2000, parent=self)

    def on_delete(self):
        item = self.listWidget.currentItem()
        if not item:
            InfoBar.warning("提示", "请先选择一项", duration=2000, parent=self)
            return
        data = item.data(Qt.UserRole)
        key = data['key']
        
        w = MessageBox("确认删除", f"确定要删除备忘录“{key}”吗？", self)
        if w.exec():
            db.delete_memo_with_log(key)
            self.refresh()
            InfoBar.success("成功", "备忘录已删除", duration=2000, parent=self)


class CalendarView(QCalendarWidget):
    """ 自定义日历控件，显示任务标记 """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setGridVisible(True)
        self.setNavigationBarVisible(True)
        self.tasks_map = {}
        self.load_tasks()
        
    def load_tasks(self):
        """加载所有任务并映射到日期"""
        self.tasks_map = {}
        try:
            all_tasks = db.get_all_tasks()
            for t_id, t_time, content, status, timestamp in all_tasks:
                # 尝试从 t_time 提取日期 (YYYY-MM-DD)
                date_str = ""
                if len(t_time) >= 10 and "-" in t_time:
                    date_str = t_time[:10]
                
                if date_str:
                    if date_str not in self.tasks_map:
                        self.tasks_map[date_str] = []
                    self.tasks_map[date_str].append({"content": content, "status": status, "time": t_time})
        except Exception as e:
            print(f"Error loading tasks for calendar: {e}")
        self.update() # 触发重绘

    def paintCell(self, painter, rect, date):
        super().paintCell(painter, rect, date)
        date_str = date.toString("yyyy-MM-dd")
        
        if date_str in self.tasks_map:
            tasks = self.tasks_map[date_str]
            has_pending = any(t['status'] == 'pending' for t in tasks)
            
            painter.save()
            painter.setRenderHint(QPainter.Antialiasing)
            
            # 如果有待办任务，画红点；如果只有已完成任务，画绿点
            color = QColor(255, 0, 0) if has_pending else QColor(0, 200, 0)
            painter.setBrush(QBrush(color))
            painter.setPen(Qt.NoPen)
            
            # 在右上角画一个小圆点
            r = 3
            center = QPoint(rect.right() - r - 4, rect.top() + r + 4)
            painter.drawEllipse(center, r, r)
            
            painter.restore()

class ToolboxPage(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ToolboxPage")
        self.layout = QVBoxLayout(self)
        self._tool_buttons = []
        # self.title = SubtitleLabel("工具箱", self)
        # self.layout.addWidget(self.title)
        
        # 使用 Grid 布局放置工具卡片
        self.grid_layout = QGridLayout()
        self.grid_layout.setSpacing(20)
        self.layout.addLayout(self.grid_layout)
        
        # 定义工具列表
        tools = [
            {"name": "计算器", "icon": FIF.CONSTRACT, "func": self.open_calculator, "desc": "系统计算器"},
            # {"name": "日历提醒", "icon": FIF.CALENDAR, "func": self.open_calendar, "desc": "查看日程与提醒"},
            {"name": "地图", "icon": FIF.GLOBE, "func": self.open_map, "desc": "高德地图"},
            {"name": "天气", "icon": FIF.CLOUD, "func": self.open_weather, "desc": "中央气象台"},
            {"name": "小游戏", "icon": FIF.PLAY, "func": self.open_games, "desc": "休闲小游戏"},
            {"name": "情感分析", "icon": FIF.HEART, "func": self.open_emotion_analysis, "desc": "分析用户情绪状态"},
            {"name": "音乐模式", "icon": FIF.MUSIC, "func": self.open_music_mode, "desc": ""}
        ]
        
        row, col = 0, 0
        for tool in tools:
            card = self.create_tool_card(tool)
            self.grid_layout.addWidget(card, row, col)
            col += 1
            if col > 1: # 每行2个
                col = 0
                row += 1
                
        self.layout.addStretch(1)

    def _build_tool_card_style(self, is_dark: bool, is_music_mode: bool) -> str:
        if is_dark:
            base_bg = "rgba(22, 22, 22, 0.82)"
            hover_bg = "rgba(34, 34, 34, 0.92)"
            pressed_bg = "rgba(12, 12, 12, 0.96)"
            border = "1px solid rgba(255, 255, 255, 0.16)"
        else:
            base_bg = "rgba(255, 255, 255, 0.22)"
            hover_bg = "rgba(255, 255, 255, 0.32)"
            pressed_bg = "rgba(255, 255, 255, 0.12)"
            border = "1px solid rgba(0, 0, 0, 0.12)"

        if is_music_mode:
            return f"""
                QPushButton {{
                    background-color: {base_bg};
                    border: {border};
                    border-radius: 8px;
                    text-align: left;
                    padding: 10px;
                }}
            """

        return f"""
            QPushButton {{
                background-color: {base_bg};
                border: {border};
                border-radius: 8px;
                text-align: left;
                padding: 10px;
            }}
            QPushButton:hover {{
                background-color: {hover_bg};
            }}
            QPushButton:pressed {{
                background-color: {pressed_bg};
            }}
        """

    def refresh_card_styles(self):
        is_dark = db.get_setting("dark_mode", "False") == "True"
        for btn, is_music_mode in getattr(self, "_tool_buttons", []):
            try:
                btn.setStyleSheet(self._build_tool_card_style(is_dark, is_music_mode))
            except Exception:
                pass

    def create_tool_card(self, tool):
        """创建工具卡片"""
        # 使用 PushButton 整个作为卡片点击
        
        btn = QPushButton(self)
        btn.setFixedSize(200, 80)
        self._tool_buttons.append((btn, tool["name"] == "音乐模式"))
        
        # 根据当前主题设置文字颜色
        is_dark = db.get_setting("dark_mode", "False") == "True"
        text_color = "white" if is_dark else "black"
        desc_color = "rgba(255, 255, 255, 0.7)" if is_dark else "rgba(0, 0, 0, 0.6)"
        
        # 音乐模式不绑定点击事件，使用开关控制
        is_music_mode = tool["name"] == "音乐模式"
        btn.setStyleSheet(self._build_tool_card_style(is_dark, is_music_mode))
        
        # 内部布局
        layout = QHBoxLayout(btn)
        
        # 图标
        # 注意：FIF 是 FluentIcon 枚举
        from qfluentwidgets import IconWidget
        icon_w = IconWidget(tool["icon"], self)
        icon_w.setFixedSize(32, 32)
        
        text_layout = QVBoxLayout()
        title = QLabel(tool["name"])
        title.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {text_color}; background: transparent;")
        desc = QLabel(tool["desc"])
        desc.setStyleSheet(f"font-size: 12px; color: {desc_color}; background: transparent;")
        
        text_layout.addWidget(title)
        if tool["name"] != "音乐模式":
            text_layout.addWidget(desc)
        
        layout.addWidget(icon_w)
        layout.addLayout(text_layout)
        
        # 音乐模式特殊处理：右侧添加开关
        if tool["name"] == "音乐模式":
            if _MUSIC_MODE_AVAILABLE:
                switch = IOSToggleSwitch(btn)
                switch.setFixedSize(52, 30)
                
                # 获取当前音乐模式状态
                main_win = None
                p = self.parent()
                while p is not None:
                    if hasattr(p, '_music_mode_enabled'):
                        main_win = p
                        break
                    p = p.parent() if hasattr(p, 'parent') else None
                
                if main_win is None:
                    print("[Toolbox] 警告：未能找到 MainWindow，音乐模式开关可能无法正常工作")
                else:
                    print(f"[Toolbox] 找到 MainWindow，当前音乐模式状态: {main_win._music_mode_enabled}")
                
                # 设置开关初始状态
                if main_win is not None:
                    switch.setChecked(main_win._music_mode_enabled)
                
                # 开关事件 - 只控制音乐模式开关状态，动画由音频监测自动控制
                def _on_music_switch(checked):
                    print(f"[Toolbox] 音乐模式开关切换: {'开启' if checked else '关闭'}")
                    if main_win is not None and hasattr(main_win, 'set_music_mode_enabled'):
                        main_win.set_music_mode_enabled(checked)
                        print(f"[Toolbox] 已调用 set_music_mode_enabled({checked})")
                    else:
                        print(f"[Toolbox] 错误：无法找到 MainWindow 或 set_music_mode_enabled 方法")
                
                switch.toggled.connect(_on_music_switch)
                layout.addWidget(switch)
                layout.addSpacing(5)
            else:
                # 模块不可用显示提示
                label = QLabel("未安装")
                label.setStyleSheet(f"color: {desc_color}; font-size: 10px;")
                layout.addWidget(label)
        else:
            btn.clicked.connect(tool["func"])
        
        return btn

    def open_calculator(self):
        try:
            subprocess.Popen("calc")
        except Exception as e:
            print(f"Failed to open calculator: {e}")
            
    def open_calendar(self):
        # 创建日历对话框
        dialog = QDialog(self)
        dialog.setWindowTitle("日历与提醒")
        dialog.resize(500, 400)
        # 移除问号
        dialog.setWindowFlags(dialog.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        
        layout = QVBoxLayout(dialog)
        
        cal = CalendarView(dialog)
        layout.addWidget(cal)
        
        info_label = QLabel("点击日期查看详情")
        info_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(info_label)
        
        def on_date_clicked(date):
            date_str = date.toString("yyyy-MM-dd")
            tasks = cal.tasks_map.get(date_str, [])
            if tasks:
                msg = f"<b>{date_str} 的安排：</b><br>"
                for t in tasks:
                    status = "✅" if t['status'] == 'done' else "⏰"
                    msg += f"<br>{status} {t['time'][11:16]} {t['content']}"
                QMessageBox.information(dialog, "日程详情", msg)
            else:
                # 询问是否添加？暂时不搞那么复杂，只显示无
                pass # QMessageBox.information(dialog, "日程详情", f"{date_str} 无安排")
        
        cal.clicked.connect(on_date_clicked)
        
        dialog.exec_()

    def open_map(self):
        # 调用 Windows 自带地图应用
        try:
            subprocess.Popen(["explorer", "bingmaps:"])
        except Exception as e:
            print(f"[Toolbox] 打开地图失败: {e}")
            # 回退到网页版
            QDesktopServices.openUrl(QUrl("https://www.bing.com/maps"))
        
    def open_weather(self):
        # 调用 Windows 自带天气应用
        try:
            subprocess.Popen(["explorer", "msnweather:"])
        except Exception as e:
            print(f"[Toolbox] 打开天气失败: {e}")
            # 回退到网页版
            QDesktopServices.openUrl(QUrl("https://weather.cma.cn/"))
    
    def open_games(self):
        """小游戏 - 预留功能"""
        InfoBar.info(
            "功能开发中", 
            "小游戏功能即将上线，敬请期待！",
            duration=2000,
            parent=self
        )
        print("[Toolbox] 小游戏功能被点击（预留）")
    
    def open_emotion_analysis(self):
        """用户情感分析 - 预留功能"""
        InfoBar.info(
            "功能开发中", 
            "用户情感分析功能即将上线，敬请期待！",
            duration=2000,
            parent=self
        )
        print("[Toolbox] 用户情感分析功能被点击（预留）")
    
    def open_music_mode(self):
        """音乐模式 - 现在通过卡片上的开关直接控制，无需弹窗"""
        pass

class SettingsPage(ScrollArea):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("SettingsPage")
        self.scrollWidget = QWidget()
        self.expandLayout = ExpandLayout(self.scrollWidget)
        self.setWidget(self.scrollWidget)
        self.setWidgetResizable(True)
        
        self.chatApiGroup = SettingCardGroup("对话模型 API 配置", self.scrollWidget)
        self.chatVendorCard = OptionsSettingCard(FIF.SETTING, "模型厂商", "下拉选择厂商（自动填充 Base URL）")
        self.chatApiKeyCard = TextSettingCard(FIF.ALBUM, "API Key", "对话模型的密钥")
        self.chatBaseUrlCard = TextSettingCard(FIF.LINK, "Base URL", "对话模型的 API 基础地址")
        self.chatModelCard = TextSettingCard(FIF.DEVELOPER_TOOLS, "模型名称", "对话模型名称（例如 qwen-plus / gpt-4o / glm-4）")
        try:
            self.chatVendorCard.comboBox.addItems(_CHAT_VENDOR_OPTIONS)
        except Exception:
            for x in _CHAT_VENDOR_OPTIONS:
                self.chatVendorCard.comboBox.addItem(x)
        self.chatApiKeyCard.lineEdit.setPlaceholderText("在此输入你的 API Key")
        self.chatBaseUrlCard.lineEdit.setPlaceholderText("例如：https://api.openai.com/v1 或 https://dashscope.aliyuncs.com/compatible-mode/v1")
        self.chatModelCard.lineEdit.setPlaceholderText("例如：qwen-plus / gpt-4o / glm-4")
        self.chatApiGroup.addSettingCard(self.chatVendorCard)
        self.chatApiGroup.addSettingCard(self.chatApiKeyCard)
        self.chatApiGroup.addSettingCard(self.chatBaseUrlCard)
        self.chatApiGroup.addSettingCard(self.chatModelCard)
        self.expandLayout.addWidget(self.chatApiGroup)
        
        self.visionApiGroup = SettingCardGroup("图片识别模型 API 配置", self.scrollWidget)
        self.visionVendorCard = OptionsSettingCard(FIF.SETTING, "模型厂商", "下拉选择厂商（自动填充 Base URL）")
        self.visionApiKeyCard = TextSettingCard(FIF.ALBUM, "API Key", "图片识别模型的密钥")
        self.visionBaseUrlCard = TextSettingCard(FIF.LINK, "Base URL", "图片识别模型的 API 基础地址")
        self.visionModelCard = TextSettingCard(FIF.DEVELOPER_TOOLS, "模型名称", "图片识别模型名称（例如 gpt-4o-mini / qwen-vl-plus）")
        try:
            self.visionVendorCard.comboBox.addItems(_CHAT_VENDOR_OPTIONS)
        except Exception:
            for x in _CHAT_VENDOR_OPTIONS:
                self.visionVendorCard.comboBox.addItem(x)
        self.visionApiKeyCard.lineEdit.setPlaceholderText("在此输入你的 API Key")
        self.visionBaseUrlCard.lineEdit.setPlaceholderText("例如：https://api.openai.com/v1 或 https://dashscope.aliyuncs.com/compatible-mode/v1")
        self.visionModelCard.lineEdit.setPlaceholderText("例如：gpt-4o-mini / qwen-vl-plus / glm-4v")
        self.visionApiGroup.addSettingCard(self.visionVendorCard)
        self.visionApiGroup.addSettingCard(self.visionApiKeyCard)
        self.visionApiGroup.addSettingCard(self.visionBaseUrlCard)
        self.visionApiGroup.addSettingCard(self.visionModelCard)
        self.expandLayout.addWidget(self.visionApiGroup)

        self.saveAllBtn = PrimaryPushButton("保存设置", self.scrollWidget)
        self.saveAllBtn.clicked.connect(self.save_all_settings)
        self.expandLayout.addWidget(self.saveAllBtn)
        
        self.featureGroup = SettingCardGroup("功能设置", self.scrollWidget)
        self.ttsSwitch = SwitchSettingCard(FIF.VOLUME, "语音播报", "是否自动读出回复内容")
        self.volumeCard = SliderSettingCard(FIF.MUSIC, "语音音量", "调节语音播报的音量大小")
        self.soundSwitch = SwitchSettingCard(FIF.RINGER, "提醒音效", "任务到期时播放提示音")
        self.clipboardSwitch = SwitchSettingCard(FIF.PASTE, "剪切板功能", "开启后可读取剪贴板的文本/图片/文件路径")
        self.historyRetentionCard = OptionsSettingCard(FIF.HISTORY, "历史记录保留策略", "选择历史对话的自动清理规则")
        self.historyRetentionCard.comboBox.addItems(["7天自动删除", "永久不删除"])
        self.featureGroup.addSettingCard(self.ttsSwitch)
        self.featureGroup.addSettingCard(self.volumeCard)
        self.featureGroup.addSettingCard(self.soundSwitch)
        self.featureGroup.addSettingCard(self.clipboardSwitch)
        self.featureGroup.addSettingCard(self.historyRetentionCard)
        
        self.appearanceGroup = SettingCardGroup("个性化", self.scrollWidget)
        
        self.darkModeSwitch = SwitchSettingCard(FIF.BRUSH, "深色模式", "开启后字体变白；关闭则变黑")
        
        self.wallpaperCard = OptionsSettingCard(FIF.PHOTO, "壁纸设置", "选择内置壁纸或自定义图片")
        self.wallpaperCard.comboBox.addItems(["壁纸1", "壁纸2", "壁纸3", "自定义..."])
        
        self.appearanceGroup.addSettingCard(self.darkModeSwitch)
        self.appearanceGroup.addSettingCard(self.wallpaperCard)
        
        self.expandLayout.addWidget(self.featureGroup)
        self.expandLayout.addWidget(self.appearanceGroup)

        # 底部退出按钮区域
        self.exitGroup = SettingCardGroup("关于与退出", self.scrollWidget)
        self.btnExit = PrimaryPushButton("退出助手", self.scrollWidget)
        self.btnExit.clicked.connect(self.on_exit_app)
        self.exitGroup.addSettingCard(self.btnExit) # 注意：SettingCardGroup通常接受Card，这里可能需要包装一下或者直接放入布局
        # 由于 SettingCardGroup 设计上是添加 SettingCard，直接加 Button 可能样式不对
        # 我们用一个简单的 Card 包装它，或者直接放在 expandLayout 底部
        
        self.expandLayout.addWidget(self.exitGroup)
        # 修正：直接将按钮添加到布局底部，或者创建一个包含按钮的 Card
        # 这里创建一个自定义 Card 来放按钮
        self.exitCard = SettingCard(FIF.POWER_BUTTON, "退出程序", "彻底关闭桌面助手")
        self.exitCard.hBoxLayout.addWidget(self.btnExit, 0, Qt.AlignRight)
        self.exitCard.hBoxLayout.addSpacing(16)
        
        # 重新添加到 Group
        self.exitGroup = SettingCardGroup("系统操作", self.scrollWidget)
        self.exitGroup.addSettingCard(self.exitCard)
        self.expandLayout.addWidget(self.exitGroup)
        
        # 加载设置
        saved_vendor = db.get_setting("chat_vendor", "")
        base_url_now = db.get_setting("base_url", "")
        if not saved_vendor:
            saved_vendor = _guess_chat_vendor(base_url_now, "")
        if saved_vendor and saved_vendor in _CHAT_VENDOR_OPTIONS:
            self.chatVendorCard.comboBox.setCurrentText(saved_vendor)
        else:
            self.chatVendorCard.comboBox.setCurrentText("请选择厂商")

        vision_saved_vendor = db.get_setting("vision_vendor", "")
        vision_base_url_now = db.get_setting("vision_base_url", "")
        if not vision_saved_vendor:
            vision_saved_vendor = _guess_chat_vendor(vision_base_url_now, "")
        if vision_saved_vendor and vision_saved_vendor in _CHAT_VENDOR_OPTIONS:
            self.visionVendorCard.comboBox.setCurrentText(vision_saved_vendor)
        else:
            self.visionVendorCard.comboBox.setCurrentText("请选择厂商")
        self.chatApiKeyCard.lineEdit.setText(db.get_setting("api_key", ""))
        self.chatBaseUrlCard.lineEdit.setText(db.get_setting("base_url", ""))
        self.chatModelCard.lineEdit.setText(db.get_setting("model_name", ""))
        self.visionApiKeyCard.lineEdit.setText(db.get_setting("vision_api_key", ""))
        self.visionBaseUrlCard.lineEdit.setText(db.get_setting("vision_base_url", ""))
        self.visionModelCard.lineEdit.setText(db.get_setting("vision_model_name", ""))
        self.ttsSwitch.switchButton.setChecked(db.get_setting("use_tts", "True") == "True")
        
        # 加载音量
        try:
            vol_init = float(db.get_setting("tts_volume", "1.0"))
            self.volumeCard.slider.setValue(int(vol_init * 100))
        except:
            self.volumeCard.slider.setValue(100)
            
        self.soundSwitch.switchButton.setChecked(db.get_setting("sound_notify", "True") == "True")
        self.darkModeSwitch.switchButton.setChecked(db.get_setting("dark_mode", "False") == "True")
        self.clipboardSwitch.switchButton.setChecked(db.get_setting("clipboard_enabled", "False") == "True")
        
        wp = db.get_setting("wallpaper", "壁纸1")
        if wp in ["壁纸1", "壁纸2", "壁纸3"]:
            self.wallpaperCard.comboBox.setCurrentText(wp)
        else:
            self.wallpaperCard.comboBox.setCurrentText("自定义...")
        
        # 加载历史记录保留策略
        retention = db.get_setting("history_retention", "7天自动删除")
        if retention == "7days":
            self.historyRetentionCard.comboBox.setCurrentText("7天自动删除")
        else:
            self.historyRetentionCard.comboBox.setCurrentText("永久不删除")
            
        # 绑定保存
        self.ttsSwitch.switchButton.checkedChanged.connect(lambda c: db.set_setting("use_tts", str(c)))
        self.historyRetentionCard.comboBox.currentTextChanged.connect(self._on_history_retention_changed)
        
        # 音量变更
        self.volumeCard.slider.valueChanged.connect(self._on_volume_changed)
        
        self.soundSwitch.switchButton.checkedChanged.connect(lambda c: db.set_setting("sound_notify", str(c)))
        self.darkModeSwitch.switchButton.checkedChanged.connect(self._on_dark_mode_changed)
        self.clipboardSwitch.switchButton.checkedChanged.connect(self._on_clipboard_changed)
        
        self.wallpaperCard.comboBox.currentTextChanged.connect(self._on_wallpaper_changed)
        try:
            self.chatVendorCard.comboBox.currentTextChanged.connect(self._on_chat_vendor_changed)
        except Exception:
            pass
        try:
            self.visionVendorCard.comboBox.currentTextChanged.connect(self._on_vision_vendor_changed)
        except Exception:
            pass

    def _on_volume_changed(self, value):
        vol = value / 100.0
        db.set_setting("tts_volume", str(vol))
        # 实时更新 TTS 引擎音量
        if hasattr(self.window(), 'tts'):
            self.window().tts.set_volume(vol)

    def _on_chat_vendor_changed(self, vendor: str):
        v = str(vendor or "").strip()
        if not v or v == "请选择厂商":
            return
        default_base = _CHAT_VENDOR_DEFAULT_BASE_URL.get(v, "")
        if default_base:
            try:
                self.chatBaseUrlCard.lineEdit.setText(default_base)
            except Exception:
                pass

    def _on_vision_vendor_changed(self, vendor: str):
        v = str(vendor or "").strip()
        if not v or v == "请选择厂商" or v == "自定义模型":
            return
        default_base = _VISION_VENDOR_DEFAULT_BASE_URL.get(v, "")
        if default_base:
            try:
                self.visionBaseUrlCard.lineEdit.setText(default_base)
            except Exception:
                pass

    def _on_history_retention_changed(self, text: str):
        """历史记录保留策略变更"""
        t = str(text or "").strip()
        if t == "7天自动删除":
            db.set_setting("history_retention", "7days")
        else:
            db.set_setting("history_retention", "forever")

    def save_all_settings(self):
        chat_vendor = str(self.chatVendorCard.comboBox.currentText() or "").strip()
        if chat_vendor not in _CHAT_VENDOR_OPTIONS:
            chat_vendor = "请选择厂商"
        chat_api_key = self.chatApiKeyCard.lineEdit.text().strip()
        chat_base_url = _clean_base_url(self.chatBaseUrlCard.lineEdit.text())
        chat_model_name = self.chatModelCard.lineEdit.text().strip()

        vision_vendor = str(self.visionVendorCard.comboBox.currentText() or "").strip()
        if vision_vendor not in _CHAT_VENDOR_OPTIONS:
            vision_vendor = "请选择厂商"
        vision_api_key = self.visionApiKeyCard.lineEdit.text().strip()
        vision_base_url = _clean_base_url(self.visionBaseUrlCard.lineEdit.text())
        vision_model_name = self.visionModelCard.lineEdit.text().strip()

        db.set_setting("chat_vendor", chat_vendor)
        db.set_setting("api_key", chat_api_key)
        db.set_setting("base_url", chat_base_url)
        db.set_setting("model_name", chat_model_name)
        db.set_setting("vision_vendor", vision_vendor)
        db.set_setting("vision_api_key", vision_api_key)
        db.set_setting("vision_base_url", vision_base_url)
        db.set_setting("vision_model_name", vision_model_name)

        try:
            self.chatBaseUrlCard.lineEdit.setText(chat_base_url)
        except Exception:
            pass
        try:
            self.visionBaseUrlCard.lineEdit.setText(vision_base_url)
        except Exception:
            pass
        InfoBar.success("保存成功", "设置已更新", duration=2000, position=InfoBarPosition.TOP, parent=self)

    def _on_dark_mode_changed(self, is_dark):
        db.set_setting("dark_mode", str(is_dark))
        
        # --- 新增核心代码 ---
        # 告诉 qfluentwidgets 库切换主题，这样卡片才会变黑
        if is_dark:
            setTheme(Theme.DARK)
        else:
            setTheme(Theme.LIGHT)
        # ------------------
        
        self.window().update_theme_mode()

    def _on_clipboard_changed(self, enabled: bool):
        db.set_setting("clipboard_enabled", str(bool(enabled)))
        try:
            w = self.window()
            if w and hasattr(w, "set_clipboard_enabled"):
                w.set_clipboard_enabled(bool(enabled))
        except Exception:
            pass

    def _on_combo_item_pressed(self, index):
        """ 处理下拉框点击，如果是“自定义...”则弹出文件选择 """
        if self.wallpaperCard.comboBox.itemText(index.row()) == "自定义...":
            QTimer.singleShot(100, self._pick_custom_wallpaper)

    def _pick_custom_wallpaper(self):
        path, _ = QFileDialog.getOpenFileName(self, "选择壁纸", "", "图片文件 (*.png *.jpg *.jpeg *.bmp)")
        if path:
            db.set_setting("wallpaper", path)
            self.window().update_wallpaper()
        else:
            # 如果取消选择，恢复之前的值
            wp = db.get_setting("wallpaper", "壁纸1")
            self.wallpaperCard.comboBox.setCurrentText(wp if wp in ["壁纸1", "壁纸2", "壁纸3"] else "自定义...")

    def _on_wallpaper_changed(self, text):
        if text == "自定义...":
            self._pick_custom_wallpaper()
        else:
            db.set_setting("wallpaper", text)
            self.window().update_wallpaper()

    def on_exit_app(self):
        """ 退出程序 """
        # 这里需要调用全局的退出
        w = MessageBox("确认退出", "确定要完全退出桌面助手吗？\n提醒功能将停止工作。", self.window())
        if w.exec():
            QApplication.quit()

def _looks_like_image_follow_up(text: str) -> bool:
    s = _normalize_for_match(text)
    if not s:
        return False
    if any(k in s for k in ("图片", "照片", "图里", "图中", "这张", "上一张", "刚才那张", "头像", "这个人", "那个人", "男", "女", "性别", "几岁", "年龄", "他", "她", "真人", "真实", "画的", "插画", "动漫", "二次元", "摄影")):
        return True
    return False


class MainWindow(FluentWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("皮皮桌面助手")
        
        # 加载图标和 Logo
        logo_path = get_resource_path(os.path.join("public", "logo.png"))
        if os.path.exists(logo_path):
            self.setWindowIcon(QIcon(logo_path))
        else:
            self.setWindowIcon(QIcon(FIF.HOME.path()))
        
        # 初始化壁纸 Label
        self.wallpaperLabel = QLabel(self)
        self.wallpaperLabel.setScaledContents(True)
        self.wallpaperLabel.lower() # 放在最底层
        self.wallpaperLabel.setAttribute(Qt.WA_TransparentForMouseEvents, True)

        # 设置壁纸透明度效果
        self.wallpaperOpacityEffect = QGraphicsOpacityEffect(self)
        self.wallpaperLabel.setGraphicsEffect(self.wallpaperOpacityEffect)
        
        # ============ 音乐模式初始化（必须在工具箱之前）============
        # 音乐模式开关状态（默认关闭）
        # 从数据库加载音乐模式状态
        try:
            self._music_mode_enabled = db.get_setting("music_mode_enabled", "False") == "True"
            print(f"[MainWindow] 从数据库加载音乐模式状态: {'开启' if self._music_mode_enabled else '关闭'}")
        except Exception as e:
            self._music_mode_enabled = False
            print(f"[MainWindow] 加载音乐模式状态失败: {e}")
        
        # 音频监控器（延迟初始化，按需启动）
        self._audio_monitor = None
        # 音乐动画覆盖层
        self._music_aura_overlay = None
        self._music_is_playing = False
        self._last_music_volume = 0.0
        self._startup_music_quick_check = False
        
        if not _MUSIC_MODE_AVAILABLE:
            print("[MainWindow] 音乐模式模块不可用，跳过初始化")
        else:
            print("[MainWindow] 音乐模式模块已加载，将在窗口隐藏时按需启动")
        
        # 初始化子页面
        self.chatPage = ChatPage(self)
        self.taskPage = TaskPage(self)
        self.memoPage = MemoPage(self)
        self.toolboxPage = ToolboxPage(self)
        self.settingsPage = SettingsPage(self)
        
        # 连接输入框粘贴图片信号
        try:
            self.chatPage.lineEdit.image_pasted.connect(lambda path: self.attach_image_to_input(path, source="clipboard"))
            self.chatPage.lineEdit.clipboard_paste_requested.connect(self.handle_clipboard_insert)
            self.chatPage.lineEdit.set_clipboard_enabled_checker(lambda: getattr(self, '_clipboard_enabled', False))
        except Exception as e:
            print(f"[MainWindow] 连接粘贴图片信号失败: {e}")
        
        # 为主内容区域添加半透明蒙层（模拟毛玻璃感）
        # 初始透明度由 update_mask_opacity 在 MainWindow 初始化时设置
        
        self.initNavigation()
        
        # 【新增】强制设置导航栏为透明背景属性，禁止它自动绘制深色底色
        self.navigationInterface.setAttribute(Qt.WA_TranslucentBackground)
        
        self.initWindow()
        self.update_wallpaper() # 初始化壁纸
        
        # 恢复壁纸透明度 (固定 55%)
        self.set_wallpaper_opacity(0.55)
        
        # 应用内容区模式 (全透明背景，仅处理文字颜色)
        self.update_mask_opacity()
        
        # 逻辑组件初始化
        self.tts = TTSWorker()
        self.voice = VoiceThread()
        self.wx_monitor = WeChatStatusThread(interval_online=60, interval_offline=10)
        self.wx_logout_watcher = WeChatLogoutWatcher()
        self.wx_online = False
        
        if not hasattr(self, '_stream_reply_target'):
            self._stream_reply_target = None
        if not hasattr(self, '_stream_reply_text'):
            self._stream_reply_text = ""
        if not hasattr(self, '_stream_started'):
            self._stream_started = False

        # 提醒音效播放器
        self.player = QMediaPlayer(self)
        if os.path.exists(ALARM_FILE):
            self.player.setMedia(QMediaContent(QUrl.fromLocalFile(ALARM_FILE)))
        
        self.checkTimer = QTimer(self)
        self.checkTimer.timeout.connect(self.check_tasks)
        self.checkTimer.start(30000)

        # 信号绑定
        self.chatPage.sendBtn.clicked.connect(self.handle_send)
        self.chatPage.lineEdit.returnPressed.connect(self.handle_send)
        self.chatPage.imageBtn.clicked.connect(self.pick_and_recognize_image)
        try:
            self.chatPage.snipBtn.clicked.connect(self.start_screen_snip)
        except Exception:
            pass
        self.chatPage.voiceBtn.clicked.connect(self.toggle_voice)
        self.chatPage.refreshBtn.clicked.connect(self.manual_check_wx)
        
        # 新建对话和历史对话按钮
        self.chatPage.newChatBtn.clicked.connect(self.chatPage.new_conversation)
        self.chatPage.historyBtn.clicked.connect(self.chatPage.open_history_panel)
        self.chatPage.historyPanel.load_conversation.connect(self.chatPage.load_conversation)
        
        # 初始化当前对话
        self._init_conversation()
        self.voice.text_received.connect(self.handle_voice_text)
        self.wx_monitor.status_changed.connect(self.on_wx_status)
        self.wx_logout_watcher.status_changed.connect(self.on_wx_logout)
        
        # TTS 结束信号绑定
        self.tts.finished.connect(self.on_tts_finished)
        self.current_speaking_bubble = None
        
        # 初始启动监控
        self.wx_monitor.start()
        
        # 初始化托盘
        self.initTray()
        
        # 记录当前导航栏模式
        self._current_nav_mode = NavigationDisplayMode.EXPAND
        
        # 导航栏显示模式改变信号
        self.navigationInterface.displayModeChanged.connect(self.on_nav_mode_changed)
        # 默认初始化为展开状态
        self.on_nav_mode_changed(NavigationDisplayMode.EXPAND) 

        self._clipboard = QApplication.clipboard()
        self._clipboard_enabled = db.get_setting("clipboard_enabled", "False") == "True"
        self._clipboard_snapshot = None
        self._clipboard_shortcut_insert = QShortcut(QKeySequence("Ctrl+Alt+V"), self)
        self._clipboard_shortcut_insert.activated.connect(self.handle_clipboard_insert)
        self._clipboard_shortcut_send = QShortcut(QKeySequence("Ctrl+Shift+V"), self)
        self._clipboard_shortcut_send.activated.connect(self.handle_clipboard_send)
        self.set_clipboard_enabled(self._clipboard_enabled)

        self._pending_image_path = None
        self._pending_image_source = "ui"
        self._awaiting_screen_snip = False
        self._voice_wait_widget = None
        try:
            self.chatPage.attachmentRemoveBtn.clicked.connect(self.clear_pending_image)
        except Exception:
            pass
        
    def _ensure_audio_monitor(self):
        """确保音频监控器已创建（懒加载）"""
        if not _MUSIC_MODE_AVAILABLE:
            return False
        
        # 如果线程已存在但已结束，需要重新创建（QThread不能restart）
        if self._audio_monitor is not None and self._audio_monitor.isFinished():
            print("[Music] 音频监控器已结束，准备重新创建")
            self._audio_monitor.deleteLater()
            self._audio_monitor = None
        
        if self._audio_monitor is None:
            try:
                self._audio_monitor = AudioMonitorThread(check_enabled_callback=self._is_music_mode_enabled)
                self._audio_monitor.music_status_changed.connect(self._on_music_playing_changed)
                self._audio_monitor.volume_changed.connect(self._on_music_volume_changed)
                self._audio_monitor.error_occurred.connect(self._on_audio_monitor_error)
                print("[Music] 音频监控器已创建")
            except Exception as e:
                print(f"[Music] 创建音频监控器失败: {e}")
                return False
        return True

    def _start_audio_monitoring(self):
        """启动音频监测（当窗口隐藏且音乐模式开启时调用）"""
        print(f"[Music] 尝试启动音频监测，当前音乐模式状态: {self._music_mode_enabled}")
        if not self._music_mode_enabled:
            print("[Music] 音乐模式未开启，跳过音频监测启动")
            return
        
        if not self._ensure_audio_monitor():
            print("[Music] 音频监控器创建失败")
            return
        
        # 检查线程状态
        if self._audio_monitor.isRunning():
            print("[Music] 音频监测已在运行中，无需重复启动")
            return
        
        if self._audio_monitor.isFinished():
            print("[Music] 警告：音频监控器已结束，尝试重新创建...")
            # 强制重新创建
            self._audio_monitor.deleteLater()
            self._audio_monitor = None
            if not self._ensure_audio_monitor():
                return
        
        try:
            self._startup_music_quick_check = True
            self._audio_monitor.start()
            print("[Music] 音频监测已启动，正在监听系统音频输出...")
        except Exception as e:
            print(f"[Music] 启动音频监测失败: {e}")
            # 如果启动失败，重置线程对象
            self._audio_monitor = None

    def _stop_audio_monitoring(self):
        """停止音频监测并释放资源（当窗口显示或程序退出时调用）"""
        if self._audio_monitor and self._audio_monitor.isRunning():
            self._audio_monitor.stop()
            print("[Music] 音频监测已停止")
        
        # 停止动画
        self._startup_music_quick_check = False
        if self._music_aura_overlay:
            self._music_aura_overlay.stop()

    def _cleanup_music_resources(self):
        """清理所有音乐相关资源"""
        self._stop_audio_monitoring()
        
        # 释放音频监控器
        if self._audio_monitor:
            self._audio_monitor.wait(1000)
            self._audio_monitor.deleteLater()
            self._audio_monitor = None
            print("[Music] 音频监控器资源已释放")
        
        # 释放动画覆盖层
        if self._music_aura_overlay:
            self._music_aura_overlay.stop()
            self._music_aura_overlay.deleteLater()
            self._music_aura_overlay = None

    def _is_music_mode_enabled(self):
        """检查音乐模式是否开启（供 AudioMonitor 回调使用）"""
        return getattr(self, '_music_mode_enabled', False)
    
    def _on_music_volume_changed(self, volume):
        """音乐音量变化时的快速启动检查"""
        try:
            self._last_music_volume = float(volume or 0.0)
        except Exception:
            self._last_music_volume = 0.0

        if not getattr(self, "_startup_music_quick_check", False):
            return
        if not self._is_music_mode_enabled():
            return

        try:
            if self._last_music_volume > 0.001:
                print(f"[Music] 启动快速检查命中，当前音量={self._last_music_volume:.4f}，立即显示动画")
                self._startup_music_quick_check = False
                self._on_music_playing_changed(True)
        except Exception:
            pass

    def _on_music_playing_changed(self, is_playing):
        """音乐播放状态变化时的处理"""
        window_visible = False
        try:
            window_visible = self.isVisible()
        except Exception:
            window_visible = False

        print(f"[Music] 音乐播放状态变化: is_playing={is_playing}, 音乐模式={self._is_music_mode_enabled()}, 窗口可见={window_visible}")
        self._music_is_playing = bool(is_playing)
        if is_playing and self._is_music_mode_enabled() and not window_visible:
            # 检测到有音乐且音乐模式开启，并且当前处于悬浮球模式，播放动画
            if hasattr(self, '_music_aura_overlay') and self._music_aura_overlay:
                print("[Music] 条件满足，准备启动动画...")
                self._music_aura_overlay.start()
                print("[Music] 检测到音乐播放，动画已启动")
            else:
                print(f"[Music] 错误: 动画覆盖层不存在 (_music_aura_overlay={getattr(self, '_music_aura_overlay', None)})")
        else:
            # 主窗口可见、音乐停止或音乐模式关闭时，都停止动画
            if hasattr(self, '_music_aura_overlay') and self._music_aura_overlay:
                print("[Music] 条件不满足，准备停止动画...")
                self._music_aura_overlay.stop()
                if window_visible:
                    print("[Music] 主窗口已显示，动画已停止")
                elif is_playing:
                    print("[Music] 检测到音乐但音乐模式已关闭，动画未启动")
                else:
                    print("[Music] 音乐停止，动画已停止")
    
    def set_music_mode_enabled(self, enabled):
        """设置音乐模式开关状态"""
        self._music_mode_enabled = enabled
        print(f"[Music] 音乐模式已{'开启' if enabled else '关闭'}")
        
        # 保存到数据库
        try:
            db.set_setting("music_mode_enabled", str(enabled))
            print(f"[Music] 音乐模式状态已保存到数据库")
        except Exception as e:
            print(f"[Music] 保存音乐模式状态到数据库失败: {e}")
        
        # 如果关闭音乐模式，立即停止音频监测和动画
        if not enabled:
            self._startup_music_quick_check = False
            if hasattr(self, '_music_aura_overlay') and self._music_aura_overlay:
                self._music_aura_overlay.stop()
            # 停止音频监测线程
            if self._audio_monitor and self._audio_monitor.isRunning():
                self._audio_monitor.stop()
                print("[Music] 音乐模式关闭，音频监测已停止")
        else:
            # 开启音乐模式时，如果窗口已经隐藏（悬浮窗模式），立即启动音频监测
            if not self.isVisible():
                print("[Music] 音乐模式开启，窗口已隐藏，立即启动音频监测")
                self._start_audio_monitoring()

    def _on_audio_monitor_error(self, error_msg):
        """音频监控错误处理"""
        print(f"[Music] 音频监控错误: {error_msg}")
        # 可以选择显示提示给用户
        # InfoBar.warning("音乐模式", f"音频监测错误: {error_msg}", duration=3000, parent=self)

    def set_clipboard_enabled(self, enabled: bool):
        enabled = bool(enabled)
        self._clipboard_enabled = enabled
        try:
            self._clipboard.dataChanged.disconnect(self._on_clipboard_data_changed)
        except Exception:
            pass
        if enabled:
            try:
                self._clipboard.dataChanged.connect(self._on_clipboard_data_changed)
            except Exception:
                pass
        else:
            self._clipboard_snapshot = None

    def _on_clipboard_data_changed(self):
        if not getattr(self, "_clipboard_enabled", False):
            return
        try:
            md = self._clipboard.mimeData()
            if md is None:
                self._clipboard_snapshot = None
                return
            if md.hasImage():
                self._clipboard_snapshot = {"type": "image"}
                return
            if md.hasUrls():
                paths = []
                for u in md.urls() or []:
                    try:
                        if u.isLocalFile():
                            p = u.toLocalFile()
                            if p:
                                paths.append(p)
                    except Exception:
                        continue
                if paths:
                    self._clipboard_snapshot = {"type": "files", "paths": paths}
                    return
            if md.hasText():
                t = md.text() or ""
                if t:
                    self._clipboard_snapshot = {"type": "text", "text": t}
                    return
            self._clipboard_snapshot = None
        except Exception:
            self._clipboard_snapshot = None

    def _read_clipboard_payload(self):
        try:
            md = self._clipboard.mimeData()
        except Exception:
            md = None
        if md is None:
            return None

        snapshot = self._clipboard_snapshot if isinstance(getattr(self, "_clipboard_snapshot", None), dict) else None
        preferred_type = snapshot.get("type") if snapshot else None

        if preferred_type == "image":
            try:
                if md.hasImage():
                    img = self._clipboard.image()
                    saved = _save_qimage_to_clipboard_cache(img)
                    if saved:
                        return {"type": "image", "path": saved, "source": "clipboard"}
            except Exception:
                pass

        if preferred_type == "files":
            try:
                if md.hasUrls():
                    paths = []
                    for u in md.urls() or []:
                        try:
                            if u.isLocalFile():
                                p = u.toLocalFile()
                                if p:
                                    paths.append(p)
                        except Exception:
                            continue
                    paths = [p for p in paths if isinstance(p, str) and p.strip()]
                    if paths:
                        if len(paths) == 1 and os.path.isfile(paths[0]) and _is_image_file_path(paths[0]):
                            return {"type": "image", "path": paths[0], "source": "clipboard_file"}
                        return {"type": "files", "paths": paths, "source": "clipboard"}
            except Exception:
                pass

        if preferred_type == "text":
            try:
                if md.hasText():
                    t = (md.text() or "")
                    if t:
                        return {"type": "text", "text": t, "source": "clipboard"}
            except Exception:
                pass

        try:
            if md.hasImage():
                img = self._clipboard.image()
                saved = _save_qimage_to_clipboard_cache(img)
                if saved:
                    return {"type": "image", "path": saved, "source": "clipboard"}
        except Exception:
            pass

        try:
            if md.hasUrls():
                paths = []
                for u in md.urls() or []:
                    try:
                        if u.isLocalFile():
                            p = u.toLocalFile()
                            if p:
                                paths.append(p)
                    except Exception:
                        continue
                paths = [p for p in paths if isinstance(p, str) and p.strip()]
                if paths:
                    if len(paths) == 1 and os.path.isfile(paths[0]) and _is_image_file_path(paths[0]):
                        return {"type": "image", "path": paths[0], "source": "clipboard_file"}
                    return {"type": "files", "paths": paths, "source": "clipboard"}
        except Exception:
            pass

        try:
            if md.hasText():
                t = (md.text() or "")
                if t:
                    return {"type": "text", "text": t, "source": "clipboard"}
        except Exception:
            pass

        return None

    def attach_image_to_input(self, path: str, source: str = "ui"):
        if not path or not os.path.exists(str(path)):
            InfoBar.warning("图片", "图片路径无效或文件不存在", duration=2000, position=InfoBarPosition.TOP, parent=self)
            return
        self._pending_image_path = str(path)
        self._pending_image_source = str(source or "ui")
        try:
            self.chatPage.set_pending_image(self._pending_image_path)
        except Exception:
            pass
        try:
            if str(self._pending_image_source).startswith("clipboard"):
                db.add_chat_pair(f"[剪贴板][图片] {os.path.basename(self._pending_image_path)}", "", user_type="clipboard_image", ai_type="meta")
        except Exception:
            pass

    def clear_pending_image(self):
        self._pending_image_path = None
        self._pending_image_source = "ui"
        try:
            self.chatPage.set_pending_image(None)
        except Exception:
            pass

    def start_screen_snip(self):
        if getattr(self, "_awaiting_screen_snip", False):
            return
        self._awaiting_screen_snip = True
        self._screen_snip_started_at = time.time()
        try:
            print("[ScreenSnip] start")
        except Exception:
            pass
        try:
            self._clipboard.dataChanged.disconnect(self._on_screen_snip_clipboard_changed)
        except Exception:
            pass
        try:
            self._clipboard.dataChanged.connect(self._on_screen_snip_clipboard_changed)
        except Exception:
            pass
        try:
            self.hide()
        except Exception:
            pass
        QTimer.singleShot(80, self._do_trigger_screen_snip)
        QTimer.singleShot(12000, self._screen_snip_timeout)

    def _do_trigger_screen_snip(self):
        ok = _trigger_windows_screen_snip()
        try:
            print(f"[ScreenSnip] trigger={'ok' if ok else 'fail'}")
        except Exception:
            pass
        if not ok:
            self._finish_screen_snip(success=False)

    def _screen_snip_timeout(self):
        if not getattr(self, "_awaiting_screen_snip", False):
            return
        self._finish_screen_snip(success=False)

    def _finish_screen_snip(self, success: bool):
        if not getattr(self, "_awaiting_screen_snip", False):
            return
        self._awaiting_screen_snip = False
        try:
            self._clipboard.dataChanged.disconnect(self._on_screen_snip_clipboard_changed)
        except Exception:
            pass
        try:
            self.show()
            self.raise_()
            self.activateWindow()
        except Exception:
            pass
        try:
            self.chatPage.lineEdit.setFocus()
        except Exception:
            pass
        try:
            print(f"[ScreenSnip] done success={success}")
        except Exception:
            pass

    def _on_screen_snip_clipboard_changed(self):
        if not getattr(self, "_awaiting_screen_snip", False):
            return
        try:
            md = self._clipboard.mimeData()
            if md is None or (not md.hasImage()):
                return
        except Exception:
            return
        payload = self._read_clipboard_payload()
        if not payload or payload.get("type") != "image":
            return
        path = payload.get("path", "")
        if path:
            self.attach_image_to_input(path, source="screenshot")
            self._finish_screen_snip(success=True)

    def handle_clipboard_insert(self):
        if not getattr(self, "_clipboard_enabled", False):
            InfoBar.warning("剪切板", "剪切板功能未开启", duration=2000, position=InfoBarPosition.TOP, parent=self)
            return
        payload = self._read_clipboard_payload()
        if not payload:
            InfoBar.warning("剪切板", "未检测到可读取内容", duration=2000, position=InfoBarPosition.TOP, parent=self)
            return

        if payload.get("type") == "image":
            self.attach_image_to_input(payload.get("path", ""), source=payload.get("source", "clipboard"))
            return

        if payload.get("type") == "files":
            paths = payload.get("paths") or []
            text = "剪贴板文件路径：\n" + "\n".join([str(p) for p in paths if str(p).strip()])
            try:
                self.chatPage.lineEdit.setFocus()
                self.chatPage.lineEdit.insert(text)
            except Exception:
                try:
                    self.chatPage.lineEdit.setText(text)
                except Exception:
                    pass
            try:
                db.add_chat_pair("[剪贴板][文件路径]\n" + text, "", user_type="clipboard_files", ai_type="meta")
            except Exception:
                pass
            return

        if payload.get("type") == "text":
            text = payload.get("text", "")
            try:
                self.chatPage.lineEdit.setFocus()
                self.chatPage.lineEdit.insert(text)
            except Exception:
                try:
                    self.chatPage.lineEdit.setText(text)
                except Exception:
                    pass
            try:
                db.add_chat_pair("[剪贴板][文本]\n" + text, "", user_type="clipboard_text", ai_type="meta")
            except Exception:
                pass
            return

    def handle_clipboard_send(self):
        if not getattr(self, "_clipboard_enabled", False):
            InfoBar.warning("剪切板", "剪切板功能未开启", duration=2000, position=InfoBarPosition.TOP, parent=self)
            return
        payload = self._read_clipboard_payload()
        if not payload:
            InfoBar.warning("剪切板", "未检测到可读取内容", duration=2000, position=InfoBarPosition.TOP, parent=self)
            return

        if payload.get("type") == "image":
            self.attach_image_to_input(payload.get("path", ""), source=payload.get("source", "clipboard"))
            self.handle_send()
            return

        if payload.get("type") == "files":
            paths = payload.get("paths") or []
            text = "剪贴板文件路径：\n" + "\n".join([str(p) for p in paths if str(p).strip()])
            self.handle_send(text)
            return

        if payload.get("type") == "text":
            self.handle_send(payload.get("text", ""))
            return

    def on_nav_mode_changed(self, mode):
        """ 
        导航栏样式更新 
        核心逻辑：背景全透明，让底层的壁纸透出来 
        """
        self._current_nav_mode = mode
        
        is_dark = db.get_setting("dark_mode", "False") == "True"
        text_color = "white" if is_dark else "black"
        
        if is_dark:
            border_style = "1px solid rgba(255, 255, 255, 40)"
        else:
            border_style = "1px solid rgba(0, 0, 0, 20)"

        # 【核心修改】
        # 1. 使用 background: transparent (简写) 以覆盖所有背景属性
        # 2. 增加 NavigationPanel 选择器，防止内部容器有背景色
        # 3. 增加 QWidget 通配，确保没有子控件挡住
        
        self.navigationInterface.setStyleSheet(f"""
            NavigationInterface {{
                background: transparent;
                background-color: transparent;
                border: none;
                border-right: {border_style};
            }}
            
            NavigationPanel {{
                background: transparent;
                background-color: transparent;
                border: none;
            }}
            
            QToolButton {{
                color: {text_color};
                font-weight: 500;
                font-size: 14px;
                border: none;
                margin: 0px;
                background-color: transparent;
            }}
            
            QToolButton:hover {{
                background-color: {"rgba(255, 255, 255, 20)" if is_dark else "rgba(0, 0, 0, 10)"};
                border-radius: 4px;
            }}
            
            QLabel {{
                color: {text_color};
                font-size: 14px;
            }}
        """)
        
        self.navigationInterface.update()

    def initTray(self):
        self.tray_icon = QSystemTrayIcon(self)
        if self.windowIcon():
            self.tray_icon.setIcon(self.windowIcon())
        else:
            self.tray_icon.setIcon(QIcon(FIF.HOME.path()))
            
        menu = QMenu()
        show_action = menu.addAction("显示主界面")
        show_action.triggered.connect(self.show)
        
        hide_action = menu.addAction("隐藏主界面")
        hide_action.triggered.connect(self.hide)
        
        menu.addSeparator()
        
        exit_action = menu.addAction("退出程序")
        exit_action.triggered.connect(self.quit_app)
        
        self.tray_icon.setContextMenu(menu)
        self.tray_icon.activated.connect(self.on_tray_activated)
        self.tray_icon.show()

    def on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.DoubleClick:
            if self.isVisible():
                self.hide()
            else:
                self.show()
                self.activateWindow()

    def quit_app(self):
        # 停止定时器
        if hasattr(self, 'checkTimer'): self.checkTimer.stop()
        try:
            db.clear_chat_history()
        except Exception:
            pass
        
        # 收集所有需要停止的线程
        threads = []
        if hasattr(self, 'voice'): threads.append(self.voice)
        if hasattr(self, 'wx_monitor'): threads.append(self.wx_monitor)
        if hasattr(self, 'wx_logout_watcher'): threads.append(self.wx_logout_watcher)
        if hasattr(self, 'tts'): threads.append(self.tts)
        if hasattr(self, 'ai_worker') and self.ai_worker and self.ai_worker.isRunning(): 
             threads.append(self.ai_worker)

        # 发送停止信号
        for t in threads:
            if hasattr(t, 'stop'):
                t.stop()
            elif hasattr(t, 'requestInterruption'):
                t.requestInterruption()

        # 等待线程结束 (最多等待 2 秒)
        for t in threads:
            if t.isRunning():
                t.wait(2000)
                if t.isRunning():
                    # 如果还在运行，强制终止（避免程序卡死无法退出）
                    t.terminate()
        
        QApplication.quit()

    def initNavigation(self):
        self.addSubInterface(self.chatPage, FIF.CHAT, "智能对话")
        self.addSubInterface(self.taskPage, FIF.CALENDAR, "提醒待办")
        self.addSubInterface(self.memoPage, FIF.DOCUMENT, "备忘笔记")
        self.addSubInterface(self.toolboxPage, FIF.TILES, "工具箱")
        self.addSubInterface(self.settingsPage, FIF.SETTING, "系统设置", NavigationItemPosition.BOTTOM)

    def _switch_to_page(self, page_widget):
        if page_widget is None:
            return False
        try:
            if hasattr(self, "switchTo"):
                self.switchTo(page_widget)
                return True
        except Exception:
            pass
        try:
            if hasattr(self, "stackedWidget"):
                self.stackedWidget.setCurrentWidget(page_widget)
                return True
        except Exception:
            pass
        return False

    def open_memo_page(self):
        try:
            self.memoPage.refresh()
        except Exception:
            pass
        self._switch_to_page(self.memoPage)
        try:
            if hasattr(self, "chatPage") and self.chatPage is not None:
                self.chatPage.scroll_to_bottom()
        except Exception:
            pass

    def open_task_page(self):
        try:
            self.taskPage.refresh()
        except Exception:
            pass
        self._switch_to_page(self.taskPage)

    def open_chat_page(self):
        self._switch_to_page(self.chatPage)
        try:
            self.chatPage.scroll_to_bottom()
        except Exception:
            pass

    def initWindow(self):
        self.resize(700, 800)
        desktop = QApplication.desktop().availableGeometry()
        self.move(desktop.width() - self.width() - 50, (desktop.height() - self.height()) // 2)

    def update_mask_opacity(self):
        """ 设置内容区透明度及配色 """
        is_dark = db.get_setting("dark_mode", "False") == "True"
        text_color = "white" if is_dark else "black"
        
        # 1. 窗口背景色：深色模式用纯黑，浅色模式用透明以便看清壁纸
        # 微信风格建议：深色模式下背景可以带一点点灰度，或者纯黑配合半透明
        if is_dark:
            self.setStyleSheet("MainWindow { background-color: #191919; }") # 微信深色背景偏向深灰黑
        else:
            self.setStyleSheet("MainWindow { background-color: transparent; }")

        # 2. 容器透明化
        if hasattr(self, 'stackedWidget'):
            self.stackedWidget.setStyleSheet("background: transparent;")

        # 3. 设置子页面通用样式
        # 注意：这里只设置文字颜色，不要强行设置 background: transparent 给所有组件，
        # 否则 SettingCard 变黑后的背景色会被覆盖掉。
        # 我们只给最外层的 Page 设透明。
        
        page_style = f"background-color: transparent; color: {text_color}; border: none;"
        
        self.chatPage.setStyleSheet(page_style)
        self.taskPage.setStyleSheet(page_style)
        self.memoPage.setStyleSheet(page_style)
        self.settingsPage.scrollWidget.setStyleSheet(page_style)
        
        # 4. 优化输入框颜色 (仿微信)
        if is_dark:
            # 微信深色模式输入框是深灰色的 (#2e2e2e)
            input_bg = "rgba(46, 46, 46, 200)" 
            input_border = "1px solid #3e3e3e"
            input_text = "white"
        else:
            input_bg = "rgba(255, 255, 255, 200)"
            input_border = "1px solid rgba(0,0,0,0.1)"
            input_text = "black"

        input_style = f"""
            TextEdit {{
                background: {input_bg};
                color: {input_text};
                border: {input_border};
                border-radius: 8px;
                padding: 8px 10px;
            }}
        """
        self.chatPage.lineEdit.setStyleSheet(input_style)
        
        # 5. 更新导航栏模式
        if hasattr(self, '_current_nav_mode'):
            self.on_nav_mode_changed(self._current_nav_mode)

    def update_wallpaper(self):
        wp = db.get_setting("wallpaper", "壁纸1")
        if wp == "壁纸1": path = get_resource_path(os.path.join("public", "壁纸1.png"))
        elif wp == "壁纸2": path = get_resource_path(os.path.join("public", "壁纸2.png"))
        elif wp == "壁纸3": path = get_resource_path(os.path.join("public", "壁纸3.png"))
        else: path = wp # 自定义路径

        if os.path.exists(path):
            self.wallpaperLabel.setPixmap(QPixmap(path))
            self.wallpaperLabel.setGeometry(self.rect())
            self.wallpaperLabel.show()
        else:
            self.wallpaperLabel.hide()

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self.wallpaperLabel.setGeometry(self.rect())
        try:
            if hasattr(self, "chatPage") and self.chatPage is not None:
                self.chatPage.update_bubble_widths()
        except Exception:
            pass

    def update_theme_mode(self):
        """ 全局切换深色/浅色模式 """
        self.update_mask_opacity()
        try:
            if hasattr(self, "chatPage") and hasattr(self.chatPage, "update_message_theme"):
                self.chatPage.update_message_theme()
        except Exception:
            pass
        try:
            if hasattr(self, "toolboxPage") and hasattr(self.toolboxPage, "refresh_card_styles"):
                self.toolboxPage.refresh_card_styles()
        except Exception:
            pass

    def set_wallpaper_opacity(self, opacity):
        """ 设置壁纸透明度 """
        if hasattr(self, 'wallpaperOpacityEffect'):
            self.wallpaperOpacityEffect.setOpacity(opacity)

    def pick_and_recognize_image(self):
        path, _ = QFileDialog.getOpenFileName(self, "选择图片", "", "图片文件 (*.png *.jpg *.jpeg *.bmp *.webp)")
        if not path:
            return
        self.attach_image_to_input(path, source="ui")

    def _start_multimodal_flow(self, user_text: str, image_path: str, source: str, user_msg_widget, placeholder_widget):
        try:
            if placeholder_widget is not None and hasattr(placeholder_widget, "start_waiting"):
                placeholder_widget.start_waiting()
        except Exception:
            pass
        
        emotion_data = None
        if _EMOTION_AVAILABLE and user_text:
            try:
                emotion_data = analyze_user_emotion(user_text)
                print(f"[情感分析] 用户发送图片消息 - 主导情感: {emotion_data.get('dominant_emotion')} (得分: {emotion_data.get('dominant_score')})")
            except Exception as e:
                print(f"[情感分析] 分析失败: {e}")
        
        self._current_emotion_data = emotion_data
        
        self.image_worker = ImageRecognitionWorker(image_path, source=source)
        self.image_worker.result_ready.connect(
            lambda saved_path, recognized_text, rec_id: self._on_multimodal_image_ready(
                user_text, image_path, source, user_msg_widget, placeholder_widget, saved_path, recognized_text, rec_id
            )
        )
        self.image_worker.error_ready.connect(
            lambda err: self._on_multimodal_image_error(user_text, image_path, source, user_msg_widget, placeholder_widget, err)
        )
        self.image_worker.start()

    def _on_multimodal_image_ready(
        self,
        user_text: str,
        image_path: str,
        source: str,
        user_msg_widget,
        placeholder_widget,
        saved_path: str,
        recognized_text: str,
        rec_id: int,
    ):
        text = (recognized_text or "").strip()
        if not text:
            text = "（未识别到内容）"
        try:
            self._last_image_for_followup = str(saved_path)
            self._last_image_for_followup_ts = time.time()
            self._last_image_context_for_followup = str(text)  # 存储识别内容用于追问
        except Exception:
            pass
        try:
            if user_msg_widget is not None and hasattr(user_msg_widget, "set_image"):
                user_msg_widget.set_image(saved_path)
        except Exception:
            pass
        rel = ""
        try:
            rel = os.path.relpath(str(saved_path), APP_DATA_DIR)
        except Exception:
            rel = ""

        if not (user_text or "").strip():
            try:
                if placeholder_widget is not None and hasattr(placeholder_widget, "stop_waiting"):
                    placeholder_widget.stop_waiting()
            except Exception:
                pass
            try:
                if placeholder_widget is not None and hasattr(placeholder_widget, "label"):
                    placeholder_widget.label.setText(text)
                    try:
                        self.chatPage.set_message_alignment(placeholder_widget, Qt.AlignLeft)
                    except Exception:
                        pass
                else:
                    self.chatPage.add_message(text, False)
            except Exception:
                self.chatPage.add_message(text, False)
            try:
                self.chatPage.scroll_to_bottom()
            except Exception:
                pass
            try:
                db.add_chat_pair(f"[图片] {os.path.basename(saved_path)}", text, user_type="image", ai_type="text")
            except Exception:
                pass
            return

        llm_text = (user_text or "").strip()
        if not llm_text:
            llm_text = "请对以下内容进行自然描述："

        user_for_history = f"[图片] {os.path.basename(saved_path)}"
        if (user_text or "").strip():
            user_for_history = user_for_history + "\n" + (user_text or "").strip()

        emotion_data = getattr(self, "_current_emotion_data", None)

        self._prepare_streaming_placeholder(placeholder_widget)
        self._bind_ai_worker(
            AIWorker(
                user_text=user_for_history,
                llm_text=llm_text,
                image_context=text,
                user_type="image",
                user_media_rel_path=rel,
                reply_target=placeholder_widget,
                emotion_data=emotion_data,
            )
        )
        self.ai_worker.start()

    def _init_conversation(self):
        """初始化对话系统 - 每次启动都进入新对话"""
        # 取消之前的活跃对话标记
        try:
            db.clear_active_conversation()
        except:
            pass
        
        # 不加载任何历史对话，直接进入新对话状态
        self.chatPage.current_conv_id = None
        
        # 启动自动清理定时器
        self._start_cleanup_timer()

    def _start_cleanup_timer(self):
        """启动自动清理定时器"""
        # 每小时检查一次
        self.cleanup_timer = QTimer(self)
        self.cleanup_timer.timeout.connect(self._cleanup_old_conversations)
        self.cleanup_timer.start(3600000)  # 1小时 = 3600000毫秒
        
        # 立即执行一次清理
        self._cleanup_old_conversations()

    def _cleanup_old_conversations(self):
        """清理过期对话"""
        try:
            # 获取当前活跃对话ID和是否有消息
            active_id = getattr(self.chatPage, 'current_conv_id', None)
            current_has_messages = False
            if active_id:
                current_conv = db.get_conversation(active_id)
                if current_conv and current_conv.get("messages"):
                    current_has_messages = True
            deleted = db.cleanup_old_conversations(active_id)
            if deleted > 0:
                print(f"[System] 自动清理了 {deleted} 条过期对话")
                # 刷新历史面板
                self.chatPage.historyPanel.refresh(active_id, current_has_messages)
        except Exception as e:
            print(f"[System] 自动清理失败: {e}")

    def _on_multimodal_image_error(
        self,
        user_text: str,
        image_path: str,
        source: str,
        user_msg_widget,
        placeholder_widget,
        err: str,
    ):
        msg = (err or "").strip()
        if not msg:
            msg = "⚠️ 图片识别模型调用失败，请检查配置"
        elif "⚠️" not in msg:
            msg = "⚠️ 图片识别模型调用失败，请检查配置"
        try:
            print(f"[MultiModal] 图片识别失败: {msg} | source={source} | image_path={image_path}")
        except Exception:
            pass
        llm_text = (user_text or "").strip()
        if llm_text:
            self._prepare_streaming_placeholder(placeholder_widget)
            self._bind_ai_worker(
                AIWorker(
                    user_text=llm_text,
                    llm_text=llm_text,
                    image_context="",
                    user_type="text",
                    user_media_rel_path="",
                    reply_target=placeholder_widget,
                )
            )
            self.ai_worker.start()
            return
        try:
            if placeholder_widget is not None and hasattr(placeholder_widget, "label"):
                try:
                    if hasattr(placeholder_widget, "stop_waiting"):
                        placeholder_widget.stop_waiting()
                except Exception:
                    pass
                placeholder_widget.label.setText(msg)
                try:
                    self.chatPage.set_message_alignment(placeholder_widget, Qt.AlignLeft)
                except Exception:
                    pass
            else:
                self.chatPage.add_message(msg, False)
        except Exception:
            self.chatPage.add_message(msg, False)
        try:
            self.chatPage.scroll_to_bottom()
        except Exception:
            pass
        try:
            db.add_chat_pair(f"[图片] {os.path.basename(image_path)}", msg, user_type="image", ai_type="text")
        except Exception:
            pass

    def handle_send(self, text=None):
        # 如果 text 不是字符串（比如是点击信号传递的 bool），则从输入框获取
        if not isinstance(text, str):
            text = self.chatPage.lineEdit.text().strip()
            
        pending_img = getattr(self, "_pending_image_path", None)
        pending_source = getattr(self, "_pending_image_source", "ui")
        if (not text) and (not pending_img):
            return
            
        self.chatPage.lineEdit.clear()
        self.chatPage.lineEdit.setFocus()
        self.clear_pending_image()

        if pending_img:
            user_title = text.strip() if text.strip() else os.path.basename(pending_img)
            user_msg = self.chatPage.add_message(user_title, True, image_path=pending_img)
            # 保存到当前对话
            self.chatPage.add_message_to_conversation(user_title, True, pending_img)
            placeholder = self.chatPage.add_message("", False, center=True)
            try:
                placeholder.start_waiting()
            except Exception:
                pass
            console_chat_log("USER", user_title)
            self._start_multimodal_flow(text.strip(), pending_img, pending_source, user_msg, placeholder)
            return

        self.chatPage.add_message(text, True)
        # 保存到当前对话
        self.chatPage.add_message_to_conversation(text, True)
        console_chat_log("USER", text)

        try:
            s = _normalize_for_match(text)
        except Exception:
            s = str(text or "").strip()
        if s:
            if any(k in s for k in ("查看备忘录", "打开备忘录", "备忘录列表", "列出备忘录", "显示备忘录")):
                self.open_memo_page()
                msg_widget = self.chatPage.add_message("已为你打开备忘录。", False)
                console_chat_log("AI", "已为你打开备忘录。")
                try:
                    db.add_chat_pair(text, "已为你打开备忘录。")
                except Exception:
                    pass
                if db.get_setting("use_tts", "True") == "True":
                    if self.current_speaking_bubble:
                        self.current_speaking_bubble.hide_stop_button()
                    self.current_speaking_bubble = msg_widget
                    msg_widget.show_stop_button()
                    msg_widget.stop_signal.connect(self.tts.stop_speaking)
                    self.tts.say("已为你打开备忘录。")
                    # TTS 播报时，按钮保持禁用，TTS 完成后在 on_tts_finished 中启用
                else:
                    # 【关键】快捷回复完成，恢复语音输入按钮
                    self.chatPage.voiceBtn.setEnabled(True)
                return
            if any(k in s for k in ("查看提醒", "打开提醒", "提醒列表", "待办列表", "查看待办", "打开待办")):
                self.open_task_page()
                msg_widget = self.chatPage.add_message("已为你打开提醒待办。", False)
                console_chat_log("AI", "已为你打开提醒待办。")
                try:
                    db.add_chat_pair(text, "已为你打开提醒待办。")
                except Exception:
                    pass
                if db.get_setting("use_tts", "True") == "True":
                    if self.current_speaking_bubble:
                        self.current_speaking_bubble.hide_stop_button()
                    self.current_speaking_bubble = msg_widget
                    msg_widget.show_stop_button()
                    msg_widget.stop_signal.connect(self.tts.stop_speaking)
                    self.tts.say("已为你打开提醒待办。")
                    # TTS 播报时，按钮保持禁用，TTS 完成后在 on_tts_finished 中启用
                else:
                    # 【关键】快捷回复完成，恢复语音输入按钮
                    self.chatPage.voiceBtn.setEnabled(True)
                return

        local_reply = _history_recall_reply(text)
        if local_reply is not None:
            msg_widget = self.chatPage.add_message(local_reply, False)
            console_chat_log("AI", local_reply)
            try:
                db.add_chat_pair(text, local_reply)
            except Exception:
                pass
            if db.get_setting("use_tts", "True") == "True":
                if self.current_speaking_bubble:
                    self.current_speaking_bubble.hide_stop_button()
                self.current_speaking_bubble = msg_widget
                msg_widget.show_stop_button()
                msg_widget.stop_signal.connect(self.tts.stop_speaking)
                self.tts.say(local_reply)
                # TTS 播报时，按钮保持禁用，TTS 完成后在 on_tts_finished 中启用
            else:
                # 【关键】快捷回复完成，恢复语音输入按钮
                self.chatPage.voiceBtn.setEnabled(True)
            return

        placeholder = self.chatPage.add_message("", False, center=True)
        try:
            placeholder.start_waiting()
        except Exception:
            pass
        
        # 检查是否是追问：如果是追问且上一张图片在有效期内（5分钟），保留图片上下文
        image_context_for_followup = ""
        try:
            if _looks_like_follow_up(text):
                last_ts = getattr(self, "_last_image_for_followup_ts", None)
                last_ctx = getattr(self, "_last_image_context_for_followup", None)
                if last_ts and last_ctx:
                    if time.time() - last_ts < 300:  # 5分钟内
                        image_context_for_followup = str(last_ctx)
                        print(f"[FollowUp] 检测到追问，保留图片上下文")
        except Exception as e:
                print(f"[FollowUp] 检查追问上下文时出错: {e}")
        
        emotion_data = None
        if _EMOTION_AVAILABLE and text:
            try:
                emotion_data = analyze_user_emotion(text)
                print(f"[情感分析] 用户发送消息 - 主导情感: {emotion_data.get('dominant_emotion')} (得分: {emotion_data.get('dominant_score')})")
            except Exception as e:
                print(f"[情感分析] 分析失败: {e}")
        
        self._prepare_streaming_placeholder(placeholder)
        self._bind_ai_worker(
            AIWorker(
                user_text=text, 
                llm_text=text,
                image_context=image_context_for_followup,
                reply_target=placeholder,
                emotion_data=emotion_data
            )
        )
        self.ai_worker.start()

    def on_tts_finished(self):
        """TTS 播报结束（自然结束或被打断）"""
        if self.current_speaking_bubble:
            self.current_speaking_bubble.hide_stop_button()
            self.current_speaking_bubble = None
        
        # 【关键】TTS 播报完全结束后，自动恢复语音输入按钮
        self.chatPage.voiceBtn.setEnabled(True)

    def on_ai_response(self, full_text, action_json):
        sender = None
        user_text = ""
        user_type = "text"
        user_media_rel_path = ""
        reply_target = None
        try:
            sender = self.sender()
            if sender is not None:
                user_text = getattr(sender, "user_text", "") or getattr(sender, "text", "") or ""
                user_type = getattr(sender, "user_type", "text") or "text"
                user_media_rel_path = getattr(sender, "user_media_rel_path", "") or ""
                reply_target = getattr(sender, "reply_target", None)
        except Exception:
            user_text = ""
        streamed_reply = self._consume_streamed_reply(reply_target)
        try:
            actions, visible = _parse_internal_actions_and_reply(full_text)
            reply_lines = []
            need_fallback = not bool((visible or "").strip())

            for action in actions:
                if not isinstance(action, dict):
                    continue
                type_ = action.get("type")

                if type_ == "set_memo":
                    key = str(action.get("key", "") or "").strip()
                    val_raw = str(action.get("value", "") or "").strip()
                    if not key or not val_raw:
                        continue
                    val = normalize_birthday_value(val_raw) if key.lower() in ("生日", "生 日") else val_raw
                    db.add_memo(key, val)
                    try:
                        self.memoPage.refresh()
                    except Exception:
                        pass
                    if need_fallback:
                        reply_lines.append(f"✅ 已为你记录备忘录：{key} - {val}。")
                    continue

                if type_ == "get_memo":
                    key = str(action.get("key", "") or "").strip()
                    if not key:
                        continue
                    val = db.get_memo(key)
                    if val is None:
                        fuzzy = db.find_memos_by_keyword_fuzzy(key)
                        if fuzzy:
                            k0, v0, _ts = fuzzy[0]
                            reply_lines.append(f"我找到最接近的一条：{k0} - {v0}。")
                        else:
                            reply_lines.append("我没找到对应的备忘录。")
                    else:
                        reply_lines.append(f"{key} - {val}。")
                    continue

                if type_ == "list_memos":
                    memos = db.get_all_memos()
                    if not memos:
                        reply_lines.append("暂时还没有备忘录。")
                    else:
                        reply_lines.append("备忘录如下。")
                        for k, v, _ts, _id in memos:
                            kk = str(k or "").strip()
                            vv = str(v or "").strip()
                            if kk and vv:
                                reply_lines.append(f"{kk} - {vv}。")
                    continue

                if type_ == "task":
                    raw_time = str(action.get("time", "") or "").strip()
                    content = str(action.get("content", "") or "").strip()
                    if not raw_time or not content:
                        continue
                    raw_time = normalize_decimal_hours_time_expr(raw_time)
                    try:
                        if re.match(r"^\d{4}-\d{2}-\d{2}\s+\d{1,2}:\d{2}:\d{2}$", raw_time):
                            dt = datetime.datetime.strptime(raw_time, "%Y-%m-%d %H:%M:%S")
                        else:
                            dt = parse_natural_time_expression_to_datetime(raw_time)
                    except Exception:
                        dt = None
                    if not isinstance(dt, datetime.datetime):
                        reply_lines.append("⚠️ 我没听清提醒时间。")
                        continue
                    time_str = dt.strftime("%Y-%m-%d %H:%M:%S")
                    if dt <= datetime.datetime.now():
                        reply_lines.append("⚠️ 提醒时间要晚于现在哦。")
                    else:
                        db.add_task(time_str, content)
                        try:
                            self.taskPage.refresh()
                        except Exception:
                            pass
                        if need_fallback:
                            reply_lines.append(f"⏰ 已为你设置提醒：{raw_time}。")
                    continue

                if type_ == "list_tasks":
                    tasks = db.get_tasks_in_range(status="pending")
                    if not tasks:
                        reply_lines.append("暂时还没有待办提醒。")
                    else:
                        reply_lines.append("待办提醒如下。")
                        for _id, t_time, t_content, _status in tasks:
                            tt = str(t_time or "").strip()
                            cc = str(t_content or "").strip()
                            if tt and cc:
                                reply_lines.append(f"{tt} - {cc}。")
                    continue

                if type_ == "launch_app":
                    app_name = str(action.get("app", "") or "").strip()
                    if not app_name:
                        continue
                    res = app_launcher.launch_app(app_name)
                    if need_fallback:
                        reply_lines.append(f"已尝试打开 {app_name}。")
                    continue

                if type_ == "close_app":
                    app_name = str(action.get("app", "") or "").strip()
                    if not app_name:
                        continue
                    self_names = ["皮皮", "桌面助手", "皮皮桌面助手", "助手", "DesktopPet", "PiPi"]
                    if any(n.lower() in app_name.lower() for n in self_names):
                        QTimer.singleShot(100, self.quit_app)
                        if need_fallback:
                            reply_lines.append("🛑 正在退出助手。")
                    else:
                        app_launcher.close_app(app_name)
                        if need_fallback:
                            reply_lines.append(f"已尝试关闭 {app_name}。")
                    continue

                if type_ == "kb_query":
                    q = str(action.get("question", "") or "").strip()
                    if not q:
                        continue
                    answer = kb_engine.query(q)
                    reply_lines.append(str(answer or "这个问题我还不太了解，让我根据已有信息来回答你。").strip())
                    continue

            if visible:
                reply_lines.append(visible)

            reply = _format_ai_reply_text("\n".join([x for x in reply_lines if str(x or "").strip()]))
            if not reply and streamed_reply:
                reply = _format_ai_reply_text(streamed_reply)
            if not reply:
                reply = "⚠️ 操作失败，请重试。"

            msg_widget = None
            try:
                if reply_target is not None and hasattr(reply_target, "label"):
                    try:
                        if hasattr(reply_target, "stop_waiting"):
                            reply_target.stop_waiting()
                    except Exception:
                        pass
                    if hasattr(reply_target, "set_text"):
                        reply_target.set_text(reply)
                    else:
                        reply_target.label.setText(reply)
                    msg_widget = reply_target
                    try:
                        self.chatPage.set_message_alignment(reply_target, Qt.AlignLeft)
                    except Exception:
                        pass
            except Exception:
                msg_widget = None
            if msg_widget is None:
                msg_widget = self.chatPage.add_message(reply, False)
            try:
                self.chatPage.scroll_to_bottom()
            except Exception:
                pass
            console_chat_log("AI", reply)
            # 保存到当前对话
            self.chatPage.add_message_to_conversation(reply, False)
            if user_text:
                try:
                    db.add_chat_pair(user_text, reply, user_type=user_type, ai_type="text", user_media_rel_path=user_media_rel_path)
                except Exception:
                    pass
            if db.get_setting("use_tts", "True") == "True":
                if self.current_speaking_bubble:
                    self.current_speaking_bubble.hide_stop_button()
                self.current_speaking_bubble = msg_widget
                msg_widget.show_stop_button()
                msg_widget.stop_signal.connect(self.tts.stop_speaking)
                self.tts.say(reply)
                # TTS 播报时，按钮保持禁用
                # 当 TTS 完成时，在 on_tts_finished 中启用按钮
            else:
                # 【关键】AI 完整输出回答、结束本轮对话后，自动恢复语音输入按钮
                self.chatPage.voiceBtn.setEnabled(True)
        except Exception:
            msg = "⚠️ 操作失败，请重试。"
            msg_widget = None
            try:
                if reply_target is not None and hasattr(reply_target, "label"):
                    try:
                        if hasattr(reply_target, "stop_waiting"):
                            reply_target.stop_waiting()
                    except Exception:
                        pass
                    if hasattr(reply_target, "set_text"):
                        reply_target.set_text(reply)
                    else:
                        reply_target.label.setText(reply)
                    msg_widget = reply_target
                    try:
                        self.chatPage.set_message_alignment(reply_target, Qt.AlignLeft)
                    except Exception:
                        pass
            except Exception:
                msg_widget = None
            if msg_widget is None:
                msg_widget = self.chatPage.add_message(msg, False)
            try:
                self.chatPage.scroll_to_bottom()
            except Exception:
                pass
            console_chat_log("AI", msg)
            
            # 【关键】异常情况下也要恢复按钮，允许用户重试
            self.chatPage.voiceBtn.setEnabled(True)

    def toggle_voice(self):
        # 防重复点击：如果按钮已禁用，直接返回
        if not self.chatPage.voiceBtn.isEnabled():
            return
            
        # 用户点击开始语音输入时，停止 TTS 播报
        if self.tts.isRunning():
            self.tts.stop_speaking()
            
        if self.voice.running:
            # 不允许中途停止语音输入（按钮已禁用，此分支不会执行）
            self.voice.stop()
            self.chatPage.voiceBtn.setIcon(FIF.MICROPHONE)
            try:
                if self._voice_wait_widget is not None:
                    try:
                        if hasattr(self._voice_wait_widget, "stop_waiting"):
                            self._voice_wait_widget.stop_waiting()
                    except Exception:
                        pass
                    self._voice_wait_widget.hide()
                    self._voice_wait_widget.deleteLater()
                    self._voice_wait_widget = None
            except Exception:
                self._voice_wait_widget = None
            InfoBar.info("语音识别", "已停止监听", duration=2000, position=InfoBarPosition.TOP, parent=self)
        else:
            if not VOICE_SUPPORT or not getattr(self.voice, "model", None):
                InfoBar.error("语音识别", "语音模型未就绪，已自动禁用语音输入", duration=3000, position=InfoBarPosition.TOP, parent=self)
                return
            
            # 【关键】用户点击开始语音输入后，立即禁用按钮
            # 禁用状态持续到 AI 完成回答为止
            self.chatPage.voiceBtn.setEnabled(False)
            self.chatPage.voiceBtn.setIcon(FIF.PAUSE)
            
            self.voice.start()
            try:
                if self._voice_wait_widget is not None:
                    try:
                        if hasattr(self._voice_wait_widget, "stop_waiting"):
                            self._voice_wait_widget.stop_waiting()
                    except Exception:
                        pass
                    self._voice_wait_widget.hide()
                    self._voice_wait_widget.deleteLater()
            except Exception:
                pass
            try:
                self._voice_wait_widget = self.chatPage.add_message("正在聆听中...", False, center=True)
                if hasattr(self._voice_wait_widget, "start_waiting"):
                    self._voice_wait_widget.start_waiting(keep_text=True)
            except Exception:
                self._voice_wait_widget = None
            InfoBar.info("语音识别", "正在聆听中...", duration=2000, position=InfoBarPosition.TOP, parent=self)

    def handle_voice_text(self, text):
        text = normalize_voice_text(text)
        try:
            if self._voice_wait_widget is not None:
                try:
                    if hasattr(self._voice_wait_widget, "stop_waiting"):
                        self._voice_wait_widget.stop_waiting()
                except Exception:
                    pass
                self._voice_wait_widget.hide()
                self._voice_wait_widget.deleteLater()
                self._voice_wait_widget = None
        except Exception:
            self._voice_wait_widget = None
        
        # 【关键】语音识别完成，发送给 AI 处理
        # 按钮保持禁用状态，直到 AI 完成回答
        self.handle_send(text)

    def _bind_ai_worker(self, worker):
        self.ai_worker = worker
        self.ai_worker.response_chunk.connect(self.on_ai_response_chunk)
        self.ai_worker.response_ready.connect(self.on_ai_response)

    def _prepare_streaming_placeholder(self, placeholder):
        self._stream_reply_target = placeholder
        self._stream_reply_text = ""
        self._stream_started = False
        if placeholder is None:
            return
        try:
            if hasattr(placeholder, "set_text"):
                placeholder.set_text("")
        except Exception:
            pass
        try:
            if hasattr(placeholder, "start_waiting"):
                placeholder.start_waiting()
        except Exception:
            pass
        try:
            self.chatPage.set_message_alignment(placeholder, Qt.AlignHCenter)
        except Exception:
            pass
        try:
            self.chatPage.scroll_to_bottom()
        except Exception:
            pass

    def _append_stream_chunk(self, chunk: str):
        part = str(chunk or "")
        if not part:
            return
        target = getattr(self, "_stream_reply_target", None)
        if not getattr(self, "_stream_started", False):
            self._stream_started = True
            if target is not None:
                try:
                    if hasattr(target, "stop_waiting"):
                        target.stop_waiting()
                except Exception:
                    pass
                try:
                    if hasattr(target, "set_text"):
                        target.set_text("")
                except Exception:
                    pass
                try:
                    self.chatPage.set_message_alignment(target, Qt.AlignLeft)
                except Exception:
                    pass
        self._stream_reply_text = getattr(self, "_stream_reply_text", "") + part
        if target is not None and hasattr(target, "append_text"):
            try:
                target.append_text(part)
            except Exception:
                pass
        try:
            self.chatPage.scroll_to_bottom()
        except Exception:
            pass

    def on_ai_response_chunk(self, chunk: str):
        self._append_stream_chunk(chunk)

    def _consume_streamed_reply(self, reply_target):
        target = getattr(self, "_stream_reply_target", None)
        if reply_target is not None and target is not None and reply_target is not target:
            return ""
        streamed = getattr(self, "_stream_reply_text", "")
        if reply_target is None and target is not None:
            return ""
        self._stream_reply_target = None
        self._stream_reply_text = ""
        self._stream_started = False
        return str(streamed or "")

    def manual_check_wx(self):
        """手动刷新微信状态"""
        print("[MainWindow] 用户点击刷新，开始手动检查")
        self.chatPage.start_loading_animation()
        self.chatPage.statusLabel.setText("正在检查...")
        self.chatPage.statusIcon.setStyleSheet("border-radius: 8px; background-color: #FFA500;") # Orange
        
        self.wx_check_worker = WxCheckWorker()
        self.wx_check_worker.result_ready.connect(self.on_manual_check_result)
        self.wx_check_worker.start()

    def on_manual_check_result(self, is_online, msg):
        print(f"[MainWindow] 手动检查结果: {is_online}, {msg}")
        self.chatPage.stop_loading_animation()
        # 复用状态更新逻辑
        self.on_wx_status(is_online)
        
        if is_online:
            InfoBar.success("微信检测", msg, duration=2000, position=InfoBarPosition.TOP, parent=self)
        else:
            InfoBar.error("微信检测", msg, duration=3000, position=InfoBarPosition.TOP, parent=self)

    def on_wx_status(self, is_online):
        """微信状态变更回调"""
        print(f"[MainWindow] 收到微信状态变更: {is_online}")
        self.wx_online = is_online
        if is_online:
            # 登录成功：停止状态轮询，启动轻量级退出监控
            if self.wx_monitor.isRunning():
                self.wx_monitor.stop()
            
            if not self.wx_logout_watcher.isRunning():
                self.wx_logout_watcher.start()
                
            InfoBar.success("微信监控", "微信已登录", duration=2000, position=InfoBarPosition.TOP, parent=self)
            self.chatPage.statusLabel.setText("微信已登录")
            self.chatPage.statusIcon.setStyleSheet("border-radius: 8px; background-color: #00ff00;") # Green
        else:
            # 登录失败或未登录：保持 monitor 运行
            if not self.wx_monitor.isRunning():
                self.wx_monitor.start()
            
            # 提示用户
            InfoBar.warning("微信监控", "当前未登录微信，部分功能受限", duration=3000, position=InfoBarPosition.TOP, parent=self)
            
            self.chatPage.statusLabel.setText("微信未登录")
            self.chatPage.statusIcon.setStyleSheet("border-radius: 8px; background-color: gray;")

    def on_wx_logout(self, is_online):
        """微信退出回调（由 watcher 触发）"""
        print(f"[MainWindow] 收到微信退出信号")
        self.wx_online = False
        if not is_online:
            # 检测到退出：停止 watcher，重启 monitor 等待重新登录
            self.wx_logout_watcher.stop()
            if not self.wx_monitor.isRunning():
                self.wx_monitor.start()
            
            InfoBar.warning("微信监控", "微信已退出", duration=2000, position=InfoBarPosition.TOP, parent=self)
            self.chatPage.statusLabel.setText("微信未连接")
            self.chatPage.statusIcon.setStyleSheet("border-radius: 8px; background-color: gray;")

    def check_tasks(self):
        tasks = db.get_pending_tasks()
        for t_id, content in tasks:
            db.mark_done(t_id)
            msg = f"🔔 提醒时间到：{content}"
            self.chatPage.add_message(msg, False)
            console_chat_log("AI", msg)
            self.tts.say(f"主人，提醒时间到了：{content}")
            
            # 微信提醒逻辑
            if self.wx_online and WX_SUPPORT:
                try:
                    # 尝试发送到文件传输助手
                    pythoncom.CoInitialize()
                    wx = WeChat()
                    wx.SendMsg(f"🔔 [皮皮助手] 提醒时间到：{content}", '文件传输助手')
                    pythoncom.CoUninitialize()
                except Exception as e:
                    print(f"微信提醒发送失败: {e}")

            # 提示音逻辑
            if db.get_setting("sound_notify", "True") == "True":
                if self.player.mediaStatus() != QMediaPlayer.NoMedia:
                    self.player.play()

            self.taskPage.refresh()

class FloatingBall(QWidget):
    clicked = pyqtSignal()
    pos_changed = pyqtSignal(int, int)
    visibility_changed = pyqtSignal(bool)

    HOST_SIZE = 150
    AVATAR_SIZE = 64
    
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(self.HOST_SIZE, self.HOST_SIZE)
        
        self.is_moving = False
        self._press_pos = QPoint()
        self._start_pos = QPoint()
        self._drag_threshold = 6
        
        self.setCursor(Qt.OpenHandCursor)
        self._margin = 10
        self.setWindowOpacity(0.9)
        
        # 设置初始位置：屏幕右下角
        self._set_initial_position()
        
    def _set_initial_position(self):
        """设置悬浮球初始位置在屏幕中间"""
        try:
            screen = QApplication.primaryScreen()
            if screen:
                rect = screen.availableGeometry()
                x = rect.center().x() - self.width() // 2
                y = rect.center().y() - self.height() // 2
                self.move(x, y)
                try:
                    self.pos_changed.emit(int(x), int(y))
                except Exception:
                    pass
        except Exception as e:
            print(f"[FloatingBall] 设置初始位置失败: {e}")

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        avatar_x = int((self.width() - self.AVATAR_SIZE) / 2)
        avatar_y = int((self.height() - self.AVATAR_SIZE) / 2)

        # 绘制图片
        img_path = get_resource_path(os.path.join("public", "皮皮.png"))
        if os.path.exists(img_path):
            pixmap = QPixmap(img_path)
            scaled_pixmap = pixmap.scaled(self.AVATAR_SIZE, self.AVATAR_SIZE, Qt.KeepAspectRatio, Qt.SmoothTransformation)

            path = QPainterPath()
            path.addEllipse(avatar_x, avatar_y, self.AVATAR_SIZE, self.AVATAR_SIZE)
            p.setClipPath(path)

            x = avatar_x + (self.AVATAR_SIZE - scaled_pixmap.width()) / 2
            y = avatar_y + (self.AVATAR_SIZE - scaled_pixmap.height()) / 2
            p.drawPixmap(int(x), int(y), scaled_pixmap)
        else:
            p.setBrush(QBrush(QColor(0, 120, 212, 220)))
            p.setPen(Qt.NoPen)
            p.drawEllipse(avatar_x, avatar_y, self.AVATAR_SIZE, self.AVATAR_SIZE)
            p.setPen(Qt.white)
            p.setFont(QFont("Segoe MDL2 Assets", 20))
            p.drawText(QRect(avatar_x, avatar_y, self.AVATAR_SIZE, self.AVATAR_SIZE), Qt.AlignCenter, "\uE99A")

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.is_moving = False
            self._press_pos = e.globalPos()
            self._start_pos = self.pos()
            e.accept()
            
    def mouseMoveEvent(self, e):
        if e.buttons() & Qt.LeftButton:
            delta = e.globalPos() - self._press_pos
            if not self.is_moving and delta.manhattanLength() >= self._drag_threshold:
                self.is_moving = True
                self.setCursor(Qt.ClosedHandCursor)

            if self.is_moving:
                self.move(self._start_pos + delta)
                try:
                    self.pos_changed.emit(int(self.x()), int(self.y()))
                except Exception:
                    pass
                e.accept()

    def mouseReleaseEvent(self, e):
        self.setCursor(Qt.OpenHandCursor)
        
        if self.is_moving:
            self.is_moving = False
            # 边缘吸附逻辑
            rect = QApplication.desktop().availableGeometry(self)
            left = rect.left() + self._margin
            right = rect.right() - self.width() - self._margin
            top = rect.top() + self._margin
            bottom = rect.bottom() - self.height() - self._margin
            
            x = min(max(self.x(), left), right)
            y = min(max(self.y(), top), bottom)
            
            # 吸附到四角/边缘
            snap = 80
            dx_l, dx_r = abs(x - left), abs(x - right)
            dy_t, dy_b = abs(y - top), abs(y - bottom)
            
            min_dx = min(dx_l, dx_r)
            min_dy = min(dy_t, dy_b)
            
            if min_dx <= snap and min_dy <= snap:
                x = left if dx_l <= dx_r else right
                y = top if dy_t <= dy_b else bottom
            elif min_dx <= min_dy and min_dx <= snap:
                x = left if dx_l <= dx_r else right
            elif min_dy < min_dx and min_dy <= snap:
                y = top if dy_t <= dy_b else bottom
                
            self.move(x, y)
            try:
                self.pos_changed.emit(int(x), int(y))
            except Exception:
                pass
            self.pos_changed.emit(x, y)
        else:
            # 单击事件
            self.clicked.emit()
            self.hide() # 点击球后，球消失

        e.accept()

    def showEvent(self, e):
        super().showEvent(e)
        try:
            self.visibility_changed.emit(True)
        except Exception:
            pass

    def hideEvent(self, e):
        super().hideEvent(e)
        try:
            self.visibility_changed.emit(False)
        except Exception:
            pass

    def enterEvent(self, e):
        self.setWindowOpacity(1.0)
    
    def leaveEvent(self, e):
        self.setWindowOpacity(0.9)


_single_instance_server = None
_main_window_ref = None
_floating_ball_ref = None
_pending_activate = False
_single_instance_mutex_handle = None

def _single_instance_id_digest() -> str:
    base = None
    try:
        if hasattr(sys, "_MEIPASS"):
            base = os.path.abspath(sys.executable)
        else:
            base = os.path.abspath(__file__)
    except Exception:
        base = "desktop_pet_fluent"
    return hashlib.md5(base.encode("utf-8", errors="ignore")).hexdigest()

def _single_instance_mutex_name() -> str:
    digest = _single_instance_id_digest()
    return f"Local\\mycompany.desktop_pet_fluent.{digest}"

def _single_instance_server_name() -> str:
    digest = _single_instance_id_digest()
    return f"desktop_pet_fluent_{digest}"

def _acquire_single_instance_mutex() -> bool:
    global _single_instance_mutex_handle
    try:
        kernel32 = ctypes.windll.kernel32
    except Exception:
        return True
    try:
        name = _single_instance_mutex_name()
        handle = kernel32.CreateMutexW(None, True, name)
        if not handle:
            return True
        last_error = kernel32.GetLastError()
        ERROR_ALREADY_EXISTS = 183
        if last_error == ERROR_ALREADY_EXISTS:
            try:
                kernel32.CloseHandle(handle)
            except Exception:
                pass
            return False
        _single_instance_mutex_handle = handle
        return True
    except Exception:
        return True

def _activate_existing_window_best_effort():
    try:
        user32 = ctypes.windll.user32
    except Exception:
        return
    try:
        title = "皮皮桌面助手"
        hwnd = user32.FindWindowW(None, title)
        if not hwnd:
            return
        SW_RESTORE = 9
        user32.ShowWindow(hwnd, SW_RESTORE)
        user32.SetForegroundWindow(hwnd)
    except Exception:
        return

def _activate_main_window():
    global _pending_activate
    _pending_activate = False
    w = _main_window_ref
    if w is None:
        return
    try:
        if hasattr(w, "isMinimized") and w.isMinimized():
            w.showNormal()
    except Exception:
        pass
    try:
        w.show()
    except Exception:
        return
    try:
        w.raise_()
        w.activateWindow()
    except Exception:
        pass
    b = _floating_ball_ref
    if b is not None:
        try:
            b.hide()
        except Exception:
            pass

def _notify_existing_instance(server_name: str) -> bool:
    sock = QLocalSocket()
    sock.connectToServer(server_name)
    if sock.waitForConnected(250):
        sock.write(b"show")
        sock.flush()
        sock.waitForBytesWritten(250)
        sock.disconnectFromServer()
        sock.close()
        return True
    sock.close()
    return False

def _ensure_single_instance(server_name: str):
    server = QLocalServer()
    try:
        server.setSocketOptions(QLocalServer.WorldAccessOption)
    except Exception:
        pass

    def _install_listeners():
        def _on_second_instance_message():
            global _pending_activate
            _pending_activate = True
            if _main_window_ref is not None:
                QTimer.singleShot(0, _activate_main_window)

        def _on_new_connection():
            while server.hasPendingConnections():
                s = server.nextPendingConnection()
                if s is None:
                    continue

                def _handle_ready_read(sock=s):
                    try:
                        sock.readAll()
                    except Exception:
                        pass
                    _on_second_instance_message()
                    try:
                        sock.disconnectFromServer()
                    except Exception:
                        pass

                s.readyRead.connect(_handle_ready_read)
                s.disconnected.connect(s.deleteLater)

        server.newConnection.connect(_on_new_connection)

    if server.listen(server_name):
        _install_listeners()
        return True, server

    if _notify_existing_instance(server_name):
        return False, None

    QLocalServer.removeServer(server_name)
    if server.listen(server_name):
        _install_listeners()
        return True, server

    return True, None

if __name__ == "__main__":
    server_name = _single_instance_server_name()
    if not _acquire_single_instance_mutex():
        _notify_existing_instance(server_name)
        sys.exit(0)
    from PyQt5.QtCore import QLibraryInfo, QCoreApplication
    _paths = []
    _plugins = QLibraryInfo.location(QLibraryInfo.PluginsPath)
    if _plugins and os.path.isdir(_plugins):
        _paths.append(_plugins)
        _platforms = os.path.join(_plugins, "platforms")
        if os.path.isdir(_platforms):
            os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = get_windows_short_path(_platforms)
    _bin = QLibraryInfo.location(QLibraryInfo.BinariesPath)
    if _bin and os.path.isdir(_bin):
        _pbin = get_windows_short_path(_bin)
        os.environ["PATH"] = _pbin + os.pathsep + os.environ.get("PATH", "")
        try:
            if hasattr(os, "add_dll_directory"):
                os.add_dll_directory(_pbin)
        except Exception:
            pass
    if _paths:
        QCoreApplication.setLibraryPaths(_paths)
    app = QApplication(sys.argv)
    # 不再自动清空历史，改为对话管理
    # app.aboutToQuit.connect(db.clear_chat_history)
    _, _single_instance_server = _ensure_single_instance(server_name)
    
    # --- 新增逻辑：读取数据库来决定启动时的主题 ---
    # 临时连接数据库读取一次设置
    try:
        temp_conn = sqlite3.connect(DB_FILE)
        cur = temp_conn.cursor()
        cur.execute("SELECT value FROM settings WHERE key = 'dark_mode'")
        res = cur.fetchone()
        is_dark_init = res and res[0] == "True"
        temp_conn.close()
    except:
        is_dark_init = False

    # 设置启动主题
    if is_dark_init:
        setTheme(Theme.DARK)
    else:
        setTheme(Theme.LIGHT)
    # ------------------------------------------

    window = MainWindow()
    ball = FloatingBall()
    ball.show()
    _main_window_ref = window
    _floating_ball_ref = ball
    if _pending_activate:
        QTimer.singleShot(0, _activate_main_window)

    # 创建音乐模式GIF动画覆盖层（绑定悬浮球，由音乐模式开关控制）
    if _MUSIC_MODE_AVAILABLE:
        _aura = MusicAuraOverlay(ball_widget=ball)
        window._music_aura_overlay = _aura
        try:
            ball.visibility_changed.connect(_aura.set_ball_visible)
        except Exception:
            pass
        print("[MainWindow] 音乐模式GIF动画覆盖层已创建")
    else:
        window._music_aura_overlay = None

    # 启动时如果音乐模式已开启，则自动开始监听，支持“程序启动前已在播放音频”的场景
    try:
        if _MUSIC_MODE_AVAILABLE and getattr(window, "_music_mode_enabled", False):
            print("[MainWindow] 启动时检测到音乐模式已开启，自动启动音频监测")
            QTimer.singleShot(0, window._start_audio_monitoring)
    except Exception as e:
        print(f"[MainWindow] 启动时自动启动音频监测失败: {e}")

    # 互斥逻辑
    ball.clicked.connect(window.show) # 点击球显示窗口
    # window.closeEvent = lambda e: (ball.show(), e.accept()) # 关闭窗口显示球
    
    # 悬浮球移动时，更新音乐动画位置
    def on_ball_pos_changed(x, y):
        try:
            if window._music_aura_overlay:
                window._music_aura_overlay.follow_ball()
        except Exception:
            pass

    ball.pos_changed.connect(on_ball_pos_changed)
    
    # 修改：主窗口关闭时，不退出程序，而是隐藏并显示悬浮球（模拟最小化到托盘/悬浮球）
    def on_window_close(e):
        e.ignore() # 忽略关闭事件，不销毁窗口
        window.hide()
        ball.show()
        try:
            if getattr(window, '_music_mode_enabled', False) and getattr(window, '_music_is_playing', False) and window._music_aura_overlay:
                window._music_aura_overlay.start()
        except Exception:
            pass
        
        # 窗口隐藏后，检查音乐模式并启动音频监测
        print("[Window] 窗口已隐藏，切换到悬浮窗模式")
        window._start_audio_monitoring()
    
    window.closeEvent = on_window_close
    
    # 保存原始的 show 方法
    _orig_window_show = window.show
    
    def on_window_show():
        """窗口显示时调用"""
        try:
            if hasattr(window, '_music_aura_overlay') and window._music_aura_overlay:
                window._music_aura_overlay.stop()
        except Exception:
            pass
        _orig_window_show()
        try:
            ball.hide()
        except Exception:
            pass
        print("[Window] 窗口已显示，停止音频监测")
        window._stop_audio_monitoring()
    
    window.show = on_window_show
    
    # 程序退出时清理资源
    def on_app_quit():
        print("[App] 程序退出，清理资源...")
        # 清理音乐模式资源
        if hasattr(window, '_cleanup_music_resources'):
            window._cleanup_music_resources()
        
        print("[App] 所有资源已清理")
    
    app.aboutToQuit.connect(on_app_quit)
    
    sys.exit(app.exec_())
