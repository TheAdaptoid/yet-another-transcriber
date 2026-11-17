"""Capture a target only when its window and UI Automation identity are known."""

import ctypes
from ctypes import wintypes
from dataclasses import dataclass


@dataclass(frozen=True)
class TargetSnapshot:
    """Identity required for a safe insertion."""

    hwnd: int
    runtime_id: tuple[int, ...]


def _foreground() -> int:
    user32 = ctypes.windll.user32
    user32.GetForegroundWindow.restype = wintypes.HWND
    return int(user32.GetForegroundWindow() or 0)


def _focused_runtime_id() -> tuple[int, ...]:
    import comtypes.client

    module = comtypes.client.GetModule("UIAutomationCore.dll")
    automation = comtypes.client.CreateObject(
        module.CUIAutomation, interface=module.IUIAutomation
    )
    element = automation.GetFocusedElement()
    if not element or element.CurrentIsPassword or not element.CurrentIsEnabled:
        return ()
    return tuple(int(value) for value in element.GetRuntimeId())


def capture_target() -> TargetSnapshot | None:
    """Return a complete supported target or fail closed."""
    try:
        hwnd = _foreground()
        if not hwnd:
            return None
        runtime_id = _focused_runtime_id()
        if not runtime_id or _foreground() != hwnd:
            return None
        return TargetSnapshot(hwnd, runtime_id)
    except Exception:
        return None


def still_focused(target: TargetSnapshot) -> bool:
    """Require both original window and focused element to match."""
    return capture_target() == target
