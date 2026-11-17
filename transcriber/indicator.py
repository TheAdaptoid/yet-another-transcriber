"""Display recording status without activating the overlay."""

import ctypes
import tkinter as tk
import tkinter.font as tkfont
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
        self.frame.pack(fill="both", expand=True, padx=(0, 7), pady=(0, 7))
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
        self.error_holder = tk.Frame(paper, bg=_INK, padx=2, pady=2)
        self.error_details = tk.Text(
            self.error_holder,
            width=38,
            height=4,
            wrap="word",
            state="disabled",
            exportselection=False,
            bg="#FFF8E6",
            fg=_INK,
            selectbackground=_INK,
            selectforeground="#FFFFFF",
            relief="flat",
            borderwidth=0,
            font=("Segoe UI", 10),
        )
        error_scrollbar = tk.Scrollbar(
            self.error_holder, command=self.error_details.yview
        )
        self.error_details.configure(yscrollcommand=error_scrollbar.set)
        error_scrollbar.pack(side="right", fill="y")
        self.error_details.pack(side="left", fill="both", expand=True)
        self.separator = tk.Frame(paper, height=2, bg=_INK)
        self.separator.pack(fill="x")
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
        self.state = "idle"
        self.error_text = None
        self._animation_job: str | None = None
        self._animation_generation = 0
        self._closed = False

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
        self._stop_animation()
        self.state = state
        self.error_text = text if state == "error" else None
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
        if state == "recording":
            self.hint_label.pack(fill="x", pady=(4, 0))
        else:
            self.hint_label.pack_forget()
        if state in {"recording", "transcribing"}:
            self.activity_label.pack(side="right")
        else:
            self.activity_label.pack_forget()
        if state == "copy":
            self.transcript.config(state="normal")
            self.transcript.delete("1.0", "end")
            self.transcript.insert("1.0", text or "")
            self.transcript.config(state="disabled")
            self.transcript_holder.pack(
                before=self.separator,
                fill="both",
                expand=True,
                padx=12,
                pady=(0, 8),
            )
            self.copy_button.pack(side="right")
        else:
            self.transcript_holder.pack_forget()
            self.copy_button.pack_forget()
        self.error_holder.pack_forget()
        if state in {"copy", "error"}:
            self.dismiss_button.pack(side="right")
        else:
            self.dismiss_button.pack_forget()
        self._place()
        if state in {"recording", "transcribing"}:
            self._start_animation(state)

    def _animations_enabled(self) -> bool:
        enabled = wintypes.BOOL()
        system_parameters = ctypes.windll.user32.SystemParametersInfoW
        system_parameters.argtypes = [
            wintypes.UINT,
            wintypes.UINT,
            ctypes.c_void_p,
            wintypes.UINT,
        ]
        system_parameters.restype = wintypes.BOOL
        return bool(
            system_parameters(0x1042, 0, ctypes.byref(enabled), 0) and enabled.value
        )

    def _draw_activity(self, state: str, phase: int) -> None:
        self.activity_label.delete("all")
        if state == "recording":
            x = 4 if phase == 0 else 9
            self.activity_label.create_rectangle(x, 4, x + 7, 11, fill=_INK, outline="")
        else:
            for index, x in enumerate((3, 8, 13)):
                top = 3 if index == phase else 6
                self.activity_label.create_rectangle(
                    x, top, x + 3, 11, fill=_INK, outline=""
                )

    def _start_animation(self, state: str) -> None:
        self._draw_activity(state, 0)
        if not self._animations_enabled():
            return
        generation = self._animation_generation
        phase = 0

        def tick():
            nonlocal phase
            if (
                self._closed
                or self.state != state
                or self._animation_generation != generation
            ):
                return
            self._animation_job = None
            phase = (phase + 1) % (2 if state == "recording" else 3)
            self._draw_activity(state, phase)
            self._animation_job = self.root.after(1000, tick)

        self._animation_job = self.root.after(1000, tick)

    def _stop_animation(self) -> None:
        self._animation_generation += 1
        if self._animation_job is not None:
            self.root.after_cancel(self._animation_job)
            self._animation_job = None

    def _work_area(self) -> tuple[int, int, int, int]:
        rect = wintypes.RECT()
        user32 = ctypes.windll.user32
        system_parameters = user32.SystemParametersInfoW
        system_parameters.argtypes = [
            wintypes.UINT,
            wintypes.UINT,
            ctypes.c_void_p,
            wintypes.UINT,
        ]
        system_parameters.restype = wintypes.BOOL
        if system_parameters(0x0030, 0, ctypes.byref(rect), 0):
            return rect.left, rect.top, rect.right, rect.bottom
        return 0, 0, self.root.winfo_screenwidth(), self.root.winfo_screenheight()

    def _place(self) -> None:
        left, top, right, bottom = self._work_area()
        scale = self.root.winfo_fpixels("1i") / 96
        margin = min(round(20 * scale), max(0, (right - left) // 10))
        max_width = max(1, min(right - left - 2 * margin, round(385 * scale)))
        max_height = max(1, bottom - top - 2 * margin)
        text_font = tkfont.Font(font=self.transcript.cget("font"))
        char_width = max(1, text_font.measure("0"))
        line_height = max(1, text_font.metrics("linespace"))
        text_columns = max(10, min(38, (max_width - 58) // char_width))
        self.transcript.config(width=text_columns, height=6)
        self.error_details.config(width=text_columns, height=4)
        self.label.config(wraplength=max(80, max_width - 37))
        self.root.update_idletasks()

        if self.state == "error" and self.root.winfo_reqheight() > max_height:
            self.label.config(text="Dictation failed.")
            self.error_details.config(state="normal")
            self.error_details.delete("1.0", "end")
            self.error_details.insert("1.0", self.error_text or "")
            self.error_details.config(state="disabled")
            self.error_holder.pack(
                before=self.separator,
                fill="both",
                expand=True,
                padx=12,
                pady=(0, 8),
            )
            self.root.update_idletasks()
            base_height = (
                self.root.winfo_reqheight() - self.error_holder.winfo_reqheight()
            )
            lines = min(6, max(2, (max_height - base_height) // line_height))
            self.error_details.config(height=lines)
        elif self.state == "copy":
            self.root.update_idletasks()
            base_height = (
                self.root.winfo_reqheight() - self.transcript_holder.winfo_reqheight()
            )
            lines = min(6, max(2, (max_height - base_height) // line_height))
            self.transcript.config(height=lines)

        self.root.update_idletasks()
        width = min(max_width, max(round(260 * scale), self.root.winfo_reqwidth()))
        height = min(max_height, self.root.winfo_reqheight())
        x = max(left, right - width - margin)
        y = max(top, bottom - height - margin)
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
        self._stop_animation()
        self.state = "idle"
        self.root.withdraw()

    def close(self):
        self._stop_animation()
        self._closed = True
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
