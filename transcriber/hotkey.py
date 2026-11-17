"""Register a single global shortcut on a dedicated Windows message thread."""

import ctypes
import threading
from ctypes import wintypes

MOD_ALT = 0x0001
MOD_WIN = 0x0008
MOD_NOREPEAT = 0x4000


class _Win32Hotkey:
    def __init__(self):
        self.user32 = ctypes.windll.user32
        self.kernel32 = ctypes.windll.kernel32

    def register(self, modifiers, key):
        return bool(self.user32.RegisterHotKey(None, 1, modifiers, key))

    def thread_id(self):
        return self.kernel32.GetCurrentThreadId()

    def next_message(self):
        msg = wintypes.MSG()
        result = self.user32.GetMessageW(ctypes.byref(msg), None, 0, 0)
        if result <= 0:
            return "quit"
        return "hotkey" if msg.message == 0x0312 and msg.wParam == 1 else "other"

    def unregister(self):
        self.user32.UnregisterHotKey(None, 1)

    def quit(self, thread_id):
        self.user32.PostThreadMessageW(thread_id, 0x0012, 0, 0)


class HotkeyListener:
    """Own the Win+Alt+S registration for the life of the listener."""

    def __init__(self, api=None):
        """Accept a Win32 adapter for isolated testing."""
        self.api = api or _Win32Hotkey()
        self.thread = None
        self.ready = threading.Event()
        self.thread_id = None
        self.registered = False

    def start(self, on_press):
        """Register and start a worker, raising on a shortcut conflict."""

        def run():
            self.thread_id = self.api.thread_id()
            self.registered = self.api.register(
                MOD_WIN | MOD_ALT | MOD_NOREPEAT, ord("S")
            )
            self.ready.set()
            if not self.registered:
                return
            try:
                while True:
                    message = self.api.next_message()
                    if message == "quit":
                        break
                    if message == "hotkey":
                        on_press()
            finally:
                self.api.unregister()

        self.thread = threading.Thread(target=run, name="yat-hotkey", daemon=True)
        self.thread.start()
        if not self.ready.wait(5) or not self.registered:
            raise RuntimeError("Global hotkey registration failed.")

    def stop(self):
        """Stop the message loop and unregister the shortcut."""
        if self.thread and self.thread.is_alive() and self.thread_id is not None:
            self.api.quit(self.thread_id)
            self.thread.join(timeout=3)
