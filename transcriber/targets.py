"""Capture a target only when its window and UI Automation identity are known."""

import ctypes
from ctypes import wintypes
from dataclasses import dataclass
from pathlib import PureWindowsPath
from typing import Literal


@dataclass(frozen=True)
class TargetSnapshot:
    """Identity required for a safe insertion."""

    hwnd: int
    runtime_id: tuple[int, ...]
    process_name: str
    kind: Literal["terminal", "obsidian"]


def _foreground() -> int:
    user32 = ctypes.windll.user32
    user32.GetForegroundWindow.restype = wintypes.HWND
    return int(user32.GetForegroundWindow() or 0)


def _process_name(hwnd: int) -> str:
    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32
    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId.argtypes = [
        wintypes.HWND,
        ctypes.POINTER(wintypes.DWORD),
    ]
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel32.OpenProcess.restype = wintypes.HANDLE
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel32.QueryFullProcessImageNameW.argtypes = [
        wintypes.HANDLE,
        wintypes.DWORD,
        wintypes.LPWSTR,
        ctypes.POINTER(wintypes.DWORD),
    ]
    handle = kernel32.OpenProcess(0x1000, False, pid.value)
    if not handle:
        return ""
    try:
        buffer = ctypes.create_unicode_buffer(32768)
        size = wintypes.DWORD(len(buffer))
        if not kernel32.QueryFullProcessImageNameW(
            handle, 0, buffer, ctypes.byref(size)
        ):
            return ""
        return PureWindowsPath(buffer.value).name
    finally:
        kernel32.CloseHandle(handle)


def _focused_runtime_id() -> tuple[int, ...]:
    import comtypes.client

    module = comtypes.client.GetModule("UIAutomationCore.dll")
    automation = comtypes.client.CreateObject(
        module.CUIAutomation, interface=module.IUIAutomation
    )
    element = automation.GetFocusedElement()
    if not element:
        return ()
    return tuple(int(value) for value in element.GetRuntimeId())


def capture_target() -> TargetSnapshot | None:
    """Return a complete supported target or fail closed."""
    try:
        hwnd = _foreground()
        if not hwnd:
            return None
        process_name = _process_name(hwnd)
        kind = {"windowsterminal.exe": "terminal", "obsidian.exe": "obsidian"}.get(
            process_name.lower()
        )
        if kind is None:
            return None
        runtime_id = _focused_runtime_id()
        if not runtime_id or _foreground() != hwnd:
            return None
        return TargetSnapshot(hwnd, runtime_id, process_name, kind)
    except Exception:
        return None


def still_focused(target: TargetSnapshot) -> bool:
    """Require both original window and focused element to match."""
    return capture_target() == target
