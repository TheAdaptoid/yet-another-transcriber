"""Sanitize and paste text with a final focus guard."""

import ctypes
import re
import time
import unicodedata
from ctypes import wintypes
from typing import Callable, Literal

_ANSI = re.compile(r"\x1b(?:\[[0-?]*[ -/]*[@-~]|\][^\x07]*(?:\x07|\x1b\\)|[@-_])")


def safe_text(text: str, kind: Literal["terminal", "obsidian"]) -> str:
    """Make terminal input a single line; preserve normal editor text."""
    if kind == "obsidian":
        return text
    text = _ANSI.sub("", text)
    text = "".join(" " if unicodedata.category(c).startswith("C") else c for c in text)
    return " ".join(text.split())


class _KeyboardInput(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_size_t),
    ]


class _MouseInput(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_size_t),
    ]


class _HardwareInput(ctypes.Structure):
    _fields_ = [
        ("uMsg", wintypes.DWORD),
        ("wParamL", wintypes.WORD),
        ("wParamH", wintypes.WORD),
    ]


class _InputUnion(ctypes.Union):
    _fields_ = [("ki", _KeyboardInput), ("mi", _MouseInput), ("hi", _HardwareInput)]


class _Input(ctypes.Structure):
    _fields_ = [("type", wintypes.DWORD), ("value", _InputUnion)]


def _open_clipboard(owner: int) -> bool:
    user32 = ctypes.windll.user32
    user32.OpenClipboard.argtypes = [wintypes.HWND]
    return bool(user32.OpenClipboard(owner))


class WindowsInsertion:
    """Win32 Unicode clipboard and keyboard operations."""

    def __init__(self, owner: int | None = None):
        """Bind clipboard ownership to a window belonging to this process."""
        self.owner = owner

    def set_clipboard(self, text: str) -> bool:
        """Set CF_UNICODETEXT and transfer the allocated memory to Windows."""
        if not self.owner:
            return False
        user32 = ctypes.windll.user32
        kernel = ctypes.windll.kernel32
        kernel.GlobalAlloc.argtypes = [wintypes.UINT, ctypes.c_size_t]
        kernel.GlobalAlloc.restype = wintypes.HGLOBAL
        kernel.GlobalLock.argtypes = [wintypes.HGLOBAL]
        kernel.GlobalLock.restype = ctypes.c_void_p
        kernel.GlobalUnlock.argtypes = [wintypes.HGLOBAL]
        kernel.GlobalFree.argtypes = [wintypes.HGLOBAL]
        user32.SetClipboardData.argtypes = [wintypes.UINT, wintypes.HANDLE]
        user32.SetClipboardData.restype = wintypes.HANDLE
        data = (text + "\0").encode("utf-16-le")
        handle = kernel.GlobalAlloc(0x0002, len(data))
        if not handle:
            return False
        owned = True
        try:
            ptr = kernel.GlobalLock(handle)
            if not ptr:
                return False
            ctypes.memmove(ptr, data, len(data))
            kernel.GlobalUnlock(handle)
            if not _open_clipboard(self.owner):
                return False
            try:
                if not user32.EmptyClipboard():
                    return False
                if not user32.SetClipboardData(13, handle):
                    return False
                owned = False
                return True
            finally:
                user32.CloseClipboard()
        finally:
            if owned:
                kernel.GlobalFree(handle)

    def send_keys(self, keys: list[tuple[int, bool]]) -> bool:
        """Send exactly the supplied key transitions once."""
        values = (_Input * len(keys))()
        for item, (key, up) in zip(values, keys, strict=True):
            item.type = 1
            item.value.ki = _KeyboardInput(key, 0, 2 if up else 0, 0, 0)
        send = ctypes.windll.user32.SendInput
        send.argtypes = [wintypes.UINT, ctypes.POINTER(_Input), ctypes.c_int]
        send.restype = wintypes.UINT
        return send(len(values), values, ctypes.sizeof(_Input)) == len(values)


def paste_text(
    text: str,
    *,
    guard: Callable[[], bool] | None = None,
    api: WindowsInsertion | None = None,
    on_clipboard: Callable[[float], None] | None = None,
) -> bool:
    """Put text on clipboard and paste only after a successful focus guard."""
    win = api or WindowsInsertion()
    try:
        started = time.monotonic()
        copied = win.set_clipboard(text)
        if on_clipboard:
            on_clipboard((time.monotonic() - started) * 1000)
        if not copied:
            return False
        if guard is None or not guard():
            return False
        return win.send_keys([(0x11, False), (0x56, False), (0x56, True), (0x11, True)])
    except Exception:
        return False
