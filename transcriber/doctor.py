"""Check local prerequisites without recording audio."""

import ctypes
import os
import platform
import sys
from pathlib import Path

from transcriber import service
from transcriber.__main__ import check_assets
from transcriber.config import Paths
from transcriber.hotkey import HotkeyListener
from transcriber.microphones import MicrophoneError, check_format, resolve_device


def check_shortcut() -> tuple[bool | None, str]:
    """Check the shortcut unless a managed instance already owns it."""
    try:
        name = service._instance_name()
        mutex = service._kernel.OpenMutexW(0x00100000, False, name + "-mutex")
        if mutex:
            service._kernel.CloseHandle(mutex)
            return None, "A YAT instance exists; shortcut availability was not probed."
        if ctypes.get_last_error() != 2:
            return None, "Cannot determine whether an instance is active."
        listener = HotkeyListener()
        try:
            listener.start(lambda: None)
        except RuntimeError:
            return False, "Win+Alt+S is unavailable; check for a shortcut conflict."
        finally:
            listener.stop()
        return True, "Win+Alt+S is available."
    except (OSError, RuntimeError):
        return None, "Could not safely check the shortcut."


def run_checks() -> list[tuple[str, bool | None, str]]:
    """Return prerequisite statuses without capturing or printing private data."""
    checks = []
    supported = platform.system() == "Windows" and platform.machine().lower() in (
        "amd64",
        "x86_64",
    )
    if supported:
        try:
            supported = int(platform.version().split(".")[-1]) >= 22000
        except ValueError:
            supported = False
    checks.append(("platform", supported, "Windows 11 x64 is required."))
    python_ok = sys.version_info[:2] == (3, 13)
    checks.append(("python", python_ok, "Python 3.13 is required."))
    home = os.environ.get("USERPROFILE")
    assets_ok = bool(home) and check_assets(Paths.for_home(Path(home)))
    checks.append(
        ("assets", assets_ok, "Assets valid." if assets_ok else "Run the asset setup.")
    )
    try:
        check_format(resolve_device())
        microphone_ok = True
        detail = "Input format supported."
    except MicrophoneError as exc:
        microphone_ok = False
        detail = str(exc)
    checks.append(
        (
            "microphone",
            microphone_ok,
            detail,
        )
    )
    status, detail = check_shortcut()
    checks.append(("shortcut", status, detail))
    return checks
