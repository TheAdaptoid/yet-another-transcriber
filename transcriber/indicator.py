"""Display recording status without activating the overlay."""

import ctypes
import tkinter as tk
from ctypes import wintypes

from transcriber.insertion import WindowsInsertion

_PAPER = "#F8EFD2"
_INK = "#151515"
_STATE_COLORS = {
    "recording": "#F36746",
    "transcribing": "#A6D4EF",
    "error": "#F5CB5E",
    "copy": "#F5CB5E",
}


class _TkOverlay:
    def __init__(self, root, on_close):
        self.root = root
        self.on_close = on_close
        self.root.withdraw()
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.configure(bg=_INK)
        self.frame = tk.Frame(root, bg=_INK, padx=2, pady=2)
        self.frame.pack(padx=(0, 7), pady=(0, 7))
        paper = tk.Frame(self.frame, bg=_PAPER)
        paper.pack(fill="both", expand=True)
        self.ribbon = tk.Frame(paper, bg=_STATE_COLORS["recording"], padx=11, pady=5)
        self.ribbon.pack(fill="x")
        self.state_label = tk.Label(
            self.ribbon,
            text="RECORDING",
            bg=_STATE_COLORS["recording"],
            fg=_INK,
            font=("Segoe UI", 9, "bold"),
        )
        self.state_label.pack(side="left")
        self.activity_label = tk.Canvas(
            self.ribbon,
            width=20,
            height=14,
            bg=_STATE_COLORS["recording"],
            highlightthickness=0,
        )
        self.activity_label.pack(side="right")
        self.activity_label.create_rectangle(5, 4, 12, 11, fill=_INK, outline="")
        message = tk.Frame(paper, bg=_PAPER, padx=12, pady=9)
        message.pack(fill="x")
        self.label = tk.Label(
            message,
            bg=_PAPER,
            fg=_INK,
            justify="left",
            anchor="w",
            wraplength=320,
            font=("Segoe UI", 13, "bold"),
        )
        self.label.pack(fill="x", anchor="w")
        self.hint_label = tk.Label(
            message, bg=_PAPER, fg=_INK, anchor="w", font=("Segoe UI", 10)
        )
        self.hint_label.pack(fill="x", pady=(4, 0))
        self.transcript_holder = tk.Frame(paper, bg=_INK, padx=2, pady=2)
        self.transcript = tk.Text(
            self.transcript_holder,
            width=38,
            height=6,
            wrap="word",
            state="disabled",
            exportselection=False,
            bg="#FFF8E6",
            fg=_INK,
            insertbackground=_INK,
            selectbackground=_INK,
            selectforeground="#FFFFFF",
            relief="flat",
            borderwidth=0,
            font=("Segoe UI", 10),
        )
        scrollbar = tk.Scrollbar(self.transcript_holder, command=self.transcript.yview)
        self.transcript.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self.transcript.pack(side="left", fill="both", expand=True)
        separator = tk.Frame(paper, height=2, bg=_INK)
        separator.pack(fill="x")
        actions = tk.Frame(paper, bg=_PAPER, padx=10, pady=7)
        actions.pack(fill="x")
        button_style = {
            "bg": _PAPER,
            "fg": _INK,
            "activebackground": "#F5CB5E",
            "activeforeground": _INK,
            "font": ("Segoe UI", 9, "bold"),
            "relief": "solid",
            "borderwidth": 2,
            "highlightthickness": 2,
            "highlightcolor": _INK,
            "highlightbackground": _PAPER,
            "padx": 7,
            "pady": 3,
            "takefocus": True,
        }
        self.copy_button = tk.Button(
            actions, button_style, text="Copy", command=self._copy
        )
        self.dismiss_button = tk.Button(
            actions, button_style, text="Dismiss", command=self.hide
        )
        self.close_button = tk.Button(
            actions, button_style, text="Exit", command=on_close
        )
        self.close_button.pack(side="right")
        self.text = None

    def _copy(self):
        if self.text:
            if WindowsInsertion(owner=self.clipboard_owner()).set_clipboard(self.text):
                self.label.config(text="Copied. You can dismiss this result.")
            else:
                self.label.config(text="Copy failed. Select the text and try again.")

    def clipboard_owner(self):
        self.root.update_idletasks()
        user32 = ctypes.windll.user32
        user32.GetParent.argtypes = [wintypes.HWND]
        user32.GetParent.restype = wintypes.HWND
        return user32.GetParent(self.root.winfo_id()) or self.root.winfo_id()

    def present(self, state, text):
        self.text = text if state == "copy" else None
        color = _STATE_COLORS.get(state, _STATE_COLORS["error"])
        self.ribbon.config(bg=color)
        self.state_label.config(
            text={"copy": "RESULT"}.get(state, state.upper()), bg=color
        )
        self.activity_label.config(bg=color)
        self.label.config(
            text={
                "recording": "Recording…",
                "transcribing": "Transcribing…",
                "error": text or "Dictation failed.",
                "copy": "Could not paste. Select or copy this result.",
            }.get(state, state)
        )
        self.hint_label.config(text="Win+Alt+S to stop" if state == "recording" else "")
        if state in {"recording", "transcribing"}:
            self.activity_label.pack(side="right")
        else:
            self.activity_label.pack_forget()
        if state == "copy":
            self.transcript.config(state="normal")
            self.transcript.delete("1.0", "end")
            self.transcript.insert("1.0", text or "")
            self.transcript.config(state="disabled")
            self.transcript_holder.pack(fill="both", expand=True, padx=12, pady=(0, 8))
            self.copy_button.pack(side="right")
        else:
            self.transcript_holder.pack_forget()
            self.copy_button.pack_forget()
        if state in {"copy", "error"}:
            self.dismiss_button.pack(side="right")
        else:
            self.dismiss_button.pack_forget()
        self.root.update_idletasks()
        width = self.root.winfo_reqwidth()
        height = self.root.winfo_reqheight()
        x = max(0, self.root.winfo_screenwidth() - width - 20)
        y = max(0, self.root.winfo_screenheight() - height - 60)
        self.root.geometry(f"{width}x{height}+{x}+{y}")
        user32 = ctypes.windll.user32
        hwnd = self.clipboard_owner()
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

    def clipboard_owner(self):
        """Return the app-owned native window used for clipboard ownership."""
        return self.adapter.clipboard_owner()
