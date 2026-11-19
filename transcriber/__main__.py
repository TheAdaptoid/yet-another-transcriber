"""Run the local Windows dictation process."""

import hashlib
import json
import os
import queue
import threading
import tkinter as tk
from pathlib import Path

from transcriber.audio import Recorder, cleanup_temp_wavs
from transcriber.config import VAD_SHA256, Paths
from transcriber.diagnostics import make_logger
from transcriber.hotkey import HotkeyListener
from transcriber.indicator import Indicator
from transcriber.insertion import WindowsInsertion, copy_text_result, paste_text_result
from transcriber.recognizer import Recognizer
from transcriber.session import SessionController

MODEL_SHA256 = "a03779c86df3323075f5e796cb2ce5029f00ec8869eee3fdfb897afe36c6d002"
SMALL_MODEL_SHA256 = "c6138d6d58ecc8322097e0f987c32f1be8bb0a18532a3f88f734d1bbf9c41e5d"
SOURCE_COMMIT = "d1be6fde11ac6e0407606b4e42fe72d34add8037"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def check_assets(paths: Paths) -> bool:
    """Validate pinned local assets against the setup manifest."""
    try:
        manifest = json.loads(
            (paths.cli.parent / "manifest.json").read_text(encoding="utf-8-sig")
        )
        dlls = manifest["dll_sha256"]
        if not isinstance(dlls, dict):
            return False
        if any(
            not isinstance(name, str)
            or Path(name).name != name
            or not name.lower().endswith(".dll")
            or _sha256(paths.cli.parent / name) != digest
            for name, digest in dlls.items()
        ):
            return False
        model_hashes = {
            "ggml-base.en.bin": MODEL_SHA256,
            "ggml-small.en.bin": SMALL_MODEL_SHA256,
        }
        expected_model = model_hashes.get(paths.model.name)
        return (
            manifest["version"] == "v1.9.5"
            and manifest["source_commit"] == SOURCE_COMMIT
            and manifest["model_sha256"] == MODEL_SHA256
            and expected_model is not None
            and _sha256(paths.model) == expected_model
            and manifest["vad_sha256"] == VAD_SHA256
            and _sha256(paths.vad_model) == VAD_SHA256
            and _sha256(paths.cli) == manifest["cli_sha256"]
        )
    except (OSError, ValueError, KeyError, TypeError):
        return False


class Runtime:
    """Wire the UI queue, background worker, and hotkey listener."""

    def __init__(
        self, *, paths, indicator, listener, loop, assets_ok=check_assets, recorder=None
    ):
        """Create runtime ports without registering a shortcut yet."""
        self.paths = paths
        self.indicator = indicator
        self.listener = listener
        self.loop = loop
        self.assets_ok = assets_ok
        self.recorder = recorder or Recorder()
        self.queue = queue.Queue()
        self.controller = None
        self.closed = False
        self.start_error = "assets_or_hotkey"

    def start(self):
        """Check assets, remove orphan audio, and register the shortcut."""
        cleanup_temp_wavs(self.paths.tmp)
        logger = make_logger(self.paths.log)
        if not self.assets_ok(self.paths):
            self.start_error = "assets"
            self.indicator.show(
                "error", "Local model or speech engine missing or invalid. Run setup."
            )
            return False

        def insertion_api():
            return WindowsInsertion(owner=self.indicator.clipboard_owner())

        self.controller = SessionController(
            paths=self.paths,
            logger=logger,
            recorder=self.recorder,
            recognizer=Recognizer(logger),
            show_state=self.indicator.show,
            schedule=lambda seconds, fn: self.loop.after(int(seconds * 1000), fn),
            worker=lambda fn: threading.Thread(target=fn, daemon=True).start(),
            post=self.queue.put,
            copy=lambda text: copy_text_result(text, api=insertion_api()),
            paste=lambda text, **kwargs: paste_text_result(
                text, api=insertion_api(), **kwargs
            ),
        )
        controller = self.controller
        try:
            self.listener.start(lambda: controller.enqueue_hotkey(self.queue.put))
        except Exception:
            self.start_error = "hotkey"
            self.indicator.show("error", "Win+Alt+S could not be registered.")
            return False
        self.loop.after(50, self.drain)
        return True

    def drain(self):
        """Run queued callbacks on Tk's thread."""
        if self.closed:
            return
        while True:
            try:
                fn = self.queue.get_nowait()
            except queue.Empty:
                break
            fn()
        self.loop.after(50, self.drain)

    def shutdown(self):
        """Stop the listener, close capture, and destroy the UI."""
        if self.closed:
            return
        self.closed = True
        self.listener.stop()
        if self.controller is not None:
            self.controller.close()
        self.indicator.close()


def run_managed(app, loop, signals, report) -> int:
    """Run the app with readiness reporting and loop-thread shutdown."""
    try:
        if not app.start():
            report("error:" + getattr(app, "start_error", "assets_or_hotkey"))
            return 1

        def check_stop():
            if signals.stop_requested():
                app.shutdown()
            elif not app.closed:
                loop.after(100, check_stop)

        loop.after(100, check_stop)
        report("ready")
        loop.mainloop()
        return 0
    finally:
        app.shutdown()


def main(signals=None, report=None) -> int:
    """Start the background app without fetching assets."""
    try:
        paths = Paths.for_home(Path(os.environ["USERPROFILE"]))
    except (KeyError, OSError, ValueError, UnicodeError):
        if report is not None:
            report("error:assets_or_hotkey")
        return 1
    root = tk.Tk()
    app = None

    def shutdown():
        if app is not None:
            app.shutdown()

    def cancel():
        if app is not None and app.controller is not None:
            app.controller.cancel()

    indicator = Indicator(root=root, on_close=shutdown, on_cancel=cancel)
    app = Runtime(
        paths=paths, indicator=indicator, listener=HotkeyListener(), loop=root
    )
    if signals is not None and report is not None:
        return run_managed(app, root, signals, report)
    app.start()
    try:
        root.mainloop()
    except KeyboardInterrupt:
        pass
    finally:
        app.shutdown()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
