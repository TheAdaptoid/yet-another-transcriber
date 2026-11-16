"""Display recording status without activating the overlay."""

import ctypes
import tkinter as tk
from ctypes import wintypes

from transcriber.insertion import WindowsInsertion


class _TkOverlay:
    def __init__(self, root, on_close):
        self.root = root
        self.on_close = on_close
        self.root.withdraw()
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.frame = tk.Frame(root, bg="#222222", padx=12, pady=8)
        self.frame.pack(fill="both", expand=True)
        self.label = tk.Label(
            self.frame, bg="#222222", fg="white", justify="left", wraplength=380
        )
        self.label.pack(side="left")
        self.copy_button = tk.Button(self.frame, text="Copy", command=self._copy)
        self.close_button = tk.Button(self.frame, text="×", command=on_close)
        self.close_button.pack(side="right")
        self.text = None

    def _copy(self):
        if self.text:
            WindowsInsertion().set_clipboard(self.text)

    def present(self, state, text):
        self.text = text if state == "copy" else None
        self.label.config(
            text={
                "recording": "Recording…  Win+Alt+S to stop",
                "transcribing": "Transcribing…",
                "error": text or "Dictation failed.",
                "copy": "Could not paste. Copy this result:\n" + (text or ""),
            }.get(state, state)
        )
        if state == "copy":
            self.copy_button.pack(side="right")
        else:
            self.copy_button.pack_forget()
        self.root.update_idletasks()
        width = self.root.winfo_reqwidth()
        height = self.root.winfo_reqheight()
        x = max(0, self.root.winfo_screenwidth() - width - 20)
        y = max(0, self.root.winfo_screenheight() - height - 60)
        self.root.geometry(f"{width}x{height}+{x}+{y}")
        user32 = ctypes.windll.user32
        user32.GetParent.argtypes = [wintypes.HWND]
        user32.GetParent.restype = wintypes.HWND
        hwnd = user32.GetParent(self.root.winfo_id()) or self.root.winfo_id()
        get_long = user32.GetWindowLongPtrW
        get_long.argtypes = [wintypes.HWND, ctypes.c_int]
        get_long.restype = ctypes.c_ssize_t
        set_long = user32.SetWindowLongPtrW
        set_long.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_ssize_t]
        set_long.restype = ctypes.c_ssize_t
        set_long(hwnd, -20, get_long(hwnd, -20) | 0x08000000 | 0x00000080)
        user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
        user32.ShowWindow(hwnd, 4)
        user32.SetWindowPos.argtypes = [
            wintypes.HWND,
            wintypes.HWND,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            wintypes.UINT,
        ]
        user32.SetWindowPos(
            hwnd, wintypes.HWND(-1), x, y, width, height, 0x0010 | 0x0040
        )

    def hide(self):
        self.root.withdraw()

    def close(self):
        self.root.destroy()


class Indicator:
    """Present states via a non-activating adapter."""

    def __init__(self, root=None, on_close=lambda: None, adapter=None):
        """Use the supplied adapter or construct the Tk overlay."""
        self.adapter = adapter or _TkOverlay(root, on_close)

    def show(self, state: str, text: str | None = None):
        """Show a status or hide the idle indicator."""
        if state == "idle":
            self.adapter.hide()
        else:
            self.adapter.present(state, text)

    def close(self):
        """Destroy the overlay."""
        self.adapter.close()
