# -*- coding: utf-8 -*-
"""全局快捷键（方案 17.2.2）。

必须使用 Win32 ``RegisterHotKey``：``QShortcut`` 在窗口失焦时失效，
做不了"展开/箭头模式/暂停"这类全局键。V4.1 只有 QShortcut，无可复用实现。
"""

from __future__ import annotations

import ctypes
import sys
from ctypes import wintypes
from dataclasses import dataclass

from PySide6.QtCore import QAbstractNativeEventFilter

if sys.platform == "win32":
    _user32 = ctypes.windll.user32
else:  # pragma: no cover
    _user32 = None

MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008
MOD_NOREPEAT = 0x4000

WM_HOTKEY = 0x0312

_MODIFIERS = {
    "ctrl": MOD_CONTROL,
    "control": MOD_CONTROL,
    "alt": MOD_ALT,
    "shift": MOD_SHIFT,
    "win": MOD_WIN,
}

#: 字母 / 数字 / 功能键到虚拟键码
_VK_NAMES = {
    "space": 0x20,
    "esc": 0x1B,
    "escape": 0x1B,
    "enter": 0x0D,
    "return": 0x0D,
    "tab": 0x09,
}
for _i in range(10):
    _VK_NAMES[str(_i)] = 0x30 + _i
for _c in "abcdefghijklmnopqrstuvwxyz":
    _VK_NAMES[_c] = ord(_c.upper())
for _i in range(1, 25):
    _VK_NAMES[f"f{_i}"] = 0x6F + _i


class HotkeyError(RuntimeError):
    """注册失败，通常是快捷键已被其它程序占用。"""


def parse_hotkey(spec: str) -> tuple[int, int]:
    """把 ``Ctrl+Alt+Space`` 解析为 (modifiers, vk)。

    无法解析时抛 :class:`HotkeyError`，由调用方提示用户重新绑定。
    """
    parts = [p.strip().lower() for p in str(spec or "").split("+") if p.strip()]
    if not parts:
        raise HotkeyError("快捷键为空")
    modifiers = 0
    key_name = ""
    for part in parts:
        if part in _MODIFIERS:
            modifiers |= _MODIFIERS[part]
        else:
            key_name = part
    if not key_name:
        raise HotkeyError(f"快捷键缺少主键：{spec}")
    vk = _VK_NAMES.get(key_name)
    if vk is None:
        raise HotkeyError(f"不支持的按键：{key_name}")
    if modifiers == 0:
        raise HotkeyError(f"全局快捷键必须带修饰键：{spec}")
    return modifiers | MOD_NOREPEAT, vk


@dataclass
class _Binding:
    hotkey_id: int
    spec: str
    callback: object


class GlobalHotkeys(QAbstractNativeEventFilter):
    """注册全局快捷键，并把 WM_HOTKEY 派发给回调。

    ``RegisterHotKey`` 需要线程消息循环，Qt 的事件循环满足该条件。
    """

    def __init__(self) -> None:
        super().__init__()
        self._bindings: dict[int, _Binding] = {}
        self._next_id = 0x4000
        self._registered = False

    @property
    def supported(self) -> bool:
        return _user32 is not None

    @property
    def bindings(self) -> tuple[str, ...]:
        return tuple(b.spec for b in self._bindings.values())

    def register(self, spec: str, callback) -> int:
        if not self.supported:
            raise HotkeyError("当前平台不支持全局快捷键")
        modifiers, vk = parse_hotkey(spec)
        hotkey_id = self._next_id
        self._next_id += 1
        if not _user32.RegisterHotKey(None, hotkey_id, modifiers, vk):
            raise HotkeyError(f"快捷键注册失败（可能已被占用）：{spec}")
        self._bindings[hotkey_id] = _Binding(hotkey_id, spec, callback)
        return hotkey_id

    def register_many(self, mapping: dict[str, object]) -> dict[str, str]:
        """批量注册，返回失败项 {spec: 原因}，成功项不出现。

        单个冲突不应导致整体失败（方案 17.2.2：显示冲突并提示重新绑定）。
        """
        failures: dict[str, str] = {}
        for spec, callback in mapping.items():
            try:
                self.register(spec, callback)
            except HotkeyError as exc:
                failures[spec] = str(exc)
        return failures

    def unregister_all(self) -> None:
        if not self.supported:
            self._bindings.clear()
            return
        for hotkey_id in list(self._bindings):
            _user32.UnregisterHotKey(None, hotkey_id)
        self._bindings.clear()

    def nativeEventFilter(self, event_type, message):  # noqa: N802 (Qt 命名)
        if event_type != b"windows_generic_MSG":
            return False, 0
        try:
            msg = ctypes.cast(int(message), ctypes.POINTER(wintypes.MSG)).contents
        except Exception:
            return False, 0
        if msg.message != WM_HOTKEY:
            return False, 0
        binding = self._bindings.get(int(msg.wParam))
        if binding is not None:
            try:
                binding.callback()
            except Exception:
                pass
            return True, 0
        return False, 0


__all__ = [
    "MOD_ALT",
    "MOD_CONTROL",
    "MOD_SHIFT",
    "MOD_WIN",
    "WM_HOTKEY",
    "HotkeyError",
    "parse_hotkey",
    "GlobalHotkeys",
]
