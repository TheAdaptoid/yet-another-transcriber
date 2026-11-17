"""Windows synchronization primitives for the background instance."""

import ctypes
from ctypes import wintypes

_kernel = ctypes.WinDLL("kernel32", use_last_error=True)
_kernel.CreateMutexW.argtypes = (wintypes.LPVOID, wintypes.BOOL, wintypes.LPCWSTR)
_kernel.CreateMutexW.restype = wintypes.HANDLE
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
