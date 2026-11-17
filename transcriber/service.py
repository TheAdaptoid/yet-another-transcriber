"""Windows synchronization primitives for the background instance."""

import ctypes
import queue
import subprocess
import sys
import threading
from ctypes import wintypes

_kernel = ctypes.WinDLL("kernel32", use_last_error=True)
_kernel.CreateMutexW.argtypes = (wintypes.LPVOID, wintypes.BOOL, wintypes.LPCWSTR)
_kernel.CreateMutexW.restype = wintypes.HANDLE
_kernel.OpenMutexW.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.LPCWSTR)
_kernel.OpenMutexW.restype = wintypes.HANDLE
_kernel.CreateEventW.argtypes = (
    wintypes.LPVOID,
    wintypes.BOOL,
    wintypes.BOOL,
    wintypes.LPCWSTR,
)
_kernel.CreateEventW.restype = wintypes.HANDLE
_kernel.OpenEventW.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.LPCWSTR)
_kernel.OpenEventW.restype = wintypes.HANDLE
_kernel.SetEvent.argtypes = (wintypes.HANDLE,)
_kernel.SetEvent.restype = wintypes.BOOL
_kernel.WaitForSingleObject.argtypes = (wintypes.HANDLE, wintypes.DWORD)
_kernel.WaitForSingleObject.restype = wintypes.DWORD
_kernel.ReleaseMutex.argtypes = (wintypes.HANDLE,)
_kernel.ReleaseMutex.restype = wintypes.BOOL
_kernel.CloseHandle.argtypes = (wintypes.HANDLE,)
_kernel.CloseHandle.restype = wintypes.BOOL


class InstanceSignals:
    """Own a singleton mutex and its shutdown event on the creating thread."""

    def __init__(self, mutex: int, event: int) -> None:
        """Store the owned mutex and event handles."""
        self._mutex = mutex
        self._event = event

    @classmethod
    def acquire(cls, name: str) -> "InstanceSignals | None":
        """Acquire a named singleton, or return None if it already exists."""
        mutex = _kernel.CreateMutexW(None, True, name + "-mutex")
        if not mutex:
            raise ctypes.WinError(ctypes.get_last_error())
        if ctypes.get_last_error() == 183:
            _kernel.CloseHandle(mutex)
            return None
        event = _kernel.CreateEventW(None, True, False, name + "-stop")
        if not event:
            error = ctypes.get_last_error()
            _kernel.ReleaseMutex(mutex)
            _kernel.CloseHandle(mutex)
            raise ctypes.WinError(error)
        return cls(mutex, event)

    @staticmethod
    def request_stop(name: str) -> bool:
        """Signal an existing instance without opening or terminating a PID."""
        event = _kernel.OpenEventW(0x0002, False, name + "-stop")
        if not event:
            error = ctypes.get_last_error()
            if error == 2:
                return False
            raise ctypes.WinError(error)
        try:
            if not _kernel.SetEvent(event):
                raise ctypes.WinError(ctypes.get_last_error())
            return True
        finally:
            _kernel.CloseHandle(event)

    def stop_requested(self) -> bool:
        """Return whether shutdown has been requested."""
        result = _kernel.WaitForSingleObject(self._event, 0)
        if result == 0:
            return True
        if result == 258:
            return False
        raise ctypes.WinError(ctypes.get_last_error())

    def close(self) -> None:
        """Release the owned Windows handles."""
        if self._event:
            _kernel.CloseHandle(self._event)
            self._event = None
        if self._mutex:
            _kernel.ReleaseMutex(self._mutex)
            _kernel.CloseHandle(self._mutex)
            self._mutex = None


def _instance_name() -> str:
    """Derive a session-local name from the current Windows user SID."""
    advapi = ctypes.WinDLL("advapi32", use_last_error=True)
    token = wintypes.HANDLE()
    advapi.OpenProcessToken.argtypes = (
        wintypes.HANDLE,
        wintypes.DWORD,
        ctypes.POINTER(wintypes.HANDLE),
    )
    advapi.GetTokenInformation.argtypes = (
        wintypes.HANDLE,
        ctypes.c_int,
        wintypes.LPVOID,
        wintypes.DWORD,
        ctypes.POINTER(wintypes.DWORD),
    )
    advapi.ConvertSidToStringSidW.argtypes = (
        wintypes.LPVOID,
        ctypes.POINTER(wintypes.LPWSTR),
    )
    _kernel.GetCurrentProcess.restype = wintypes.HANDLE
    _kernel.LocalFree.argtypes = (wintypes.HLOCAL,)
    _kernel.LocalFree.restype = wintypes.HLOCAL
    if not advapi.OpenProcessToken(_kernel.GetCurrentProcess(), 8, ctypes.byref(token)):
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        size = wintypes.DWORD()
        advapi.GetTokenInformation(token, 1, None, 0, ctypes.byref(size))
        buffer = ctypes.create_string_buffer(size.value)
        if not advapi.GetTokenInformation(token, 1, buffer, size, ctypes.byref(size)):
            raise ctypes.WinError(ctypes.get_last_error())
        sid = ctypes.cast(buffer, ctypes.POINTER(ctypes.c_void_p)).contents.value
        text = wintypes.LPWSTR()
        if not advapi.ConvertSidToStringSidW(sid, ctypes.byref(text)):
            raise ctypes.WinError(ctypes.get_last_error())
        try:
            value = text.value
            if value is None:
                raise RuntimeError("Windows returned an empty user SID")
            return "Local\\yat-" + value
        finally:
            _kernel.LocalFree(ctypes.cast(text, wintypes.HLOCAL))
    finally:
        _kernel.CloseHandle(token)


def _read_startup(child, timeout: float) -> str | None:
    messages = queue.Queue()

    def read():
        try:
            messages.put(child.stdout.readline().decode("utf-8").strip())
        except (OSError, ValueError, UnicodeError):
            messages.put("")

    threading.Thread(target=read, daemon=True).start()
    try:
        return messages.get(timeout=timeout)
    except queue.Empty:
        return None


def start_service() -> tuple[bool, str]:
    """Start a detached instance and wait for its readiness message."""
    try:
        child = subprocess.Popen(
            [sys.executable, "-m", "transcriber.service", "--child"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            creationflags=(
                subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP
            ),
        )
    except OSError:
        return False, "Could not launch the background process."
    result = _read_startup(child, 15.0)
    if result == "ready":
        return True, "Dictation started."
    if result is None:
        child.kill()
        child.wait()
        return False, "Startup timed out."
    try:
        child.wait(timeout=5)
    except subprocess.TimeoutExpired:
        child.kill()
        child.wait()
    if result == "error:already_running":
        return False, "Dictation is already running."
    if result == "error:assets_or_hotkey":
        return False, "Startup failed: check local assets and the hotkey."
    return False, "Background process failed before reporting readiness."


def stop_service() -> tuple[bool, str]:
    """Request shutdown and wait for the instance to release its mutex."""
    try:
        name = _instance_name()
        mutex = _kernel.OpenMutexW(0x00100001, False, name + "-mutex")
        if not mutex:
            if ctypes.get_last_error() == 2:
                return True, "Dictation is not running."
            return False, "Could not access the dictation instance."
        try:
            if not InstanceSignals.request_stop(name):
                return (
                    False,
                    "Instance is starting or its shutdown signal is unavailable.",
                )
            result = _kernel.WaitForSingleObject(mutex, 10000)
            if result in (0, 0x80):
                _kernel.ReleaseMutex(mutex)
                return True, "Dictation stopped."
            if result == 258:
                return False, "Timed out waiting for dictation to stop."
            return False, "Could not confirm dictation stopped."
        finally:
            _kernel.CloseHandle(mutex)
    except OSError:
        return False, "Could not signal the dictation instance."


def _child_main() -> int:
    """Own the singleton and run the application until shutdown."""
    signals = InstanceSignals.acquire(_instance_name())
    if signals is None:
        print("error:already_running", flush=True)
        return 1
    try:
        from transcriber.__main__ import main

        return main(signals=signals, report=lambda value: print(value, flush=True))
    finally:
        signals.close()


if __name__ == "__main__":
    if sys.argv[1:] == ["--child"]:
        raise SystemExit(_child_main())
    raise SystemExit(2)
