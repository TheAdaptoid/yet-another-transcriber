"""Capture a target only when its window and UI Automation identity are known."""

import ctypes
from ctypes import wintypes
from dataclasses import dataclass
from enum import StrEnum


class TargetOutcome(StrEnum):
    """Bounded results of capturing or comparing a target."""

    MATCH = "match"
    UNAVAILABLE = "unavailable"
    CHANGED = "changed"
    AUTOMATION_ERROR = "automation_error"


@dataclass(frozen=True)
class TargetSnapshot:
    """Identity required for a safe insertion."""

    hwnd: int
    runtime_id: tuple[int, ...]


@dataclass(frozen=True)
class TargetResult:
    """A capture outcome and its target when available."""

    outcome: TargetOutcome
    target: TargetSnapshot | None = None


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


def capture_target_result() -> TargetResult:
    """Capture a complete target, preserving a safe failure category."""
    try:
        hwnd = _foreground()
        if not hwnd:
            return TargetResult(TargetOutcome.UNAVAILABLE)
        runtime_id = _focused_runtime_id()
        if not runtime_id:
            return TargetResult(TargetOutcome.UNAVAILABLE)
        if _foreground() != hwnd:
            return TargetResult(TargetOutcome.CHANGED)
        return TargetResult(TargetOutcome.MATCH, TargetSnapshot(hwnd, runtime_id))
    except Exception:
        return TargetResult(TargetOutcome.AUTOMATION_ERROR)


def capture_target() -> TargetSnapshot | None:
    """Return a complete supported target or fail closed."""
    return capture_target_result().target


def check_focus(target: TargetSnapshot) -> TargetOutcome:
    """Compare the current target with the original snapshot."""
    result = capture_target_result()
    if result.outcome != TargetOutcome.MATCH:
        return result.outcome
    return TargetOutcome.MATCH if result.target == target else TargetOutcome.CHANGED


def still_focused(target: TargetSnapshot) -> bool:
    """Require both original window and focused element to match."""
    return check_focus(target) == TargetOutcome.MATCH
