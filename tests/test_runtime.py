import hashlib
import json
import queue
import tkinter as tk

import pytest

from transcriber import __main__ as runtime
from transcriber.config import Paths
from transcriber.hotkey import HotkeyListener
from transcriber.indicator import Indicator, _TkOverlay


class FakeHotkeyAPI:
    def __init__(self, succeed=True):
        self.succeed = succeed
        self.registered = None
        self.unregistered = False
        self.messages = queue.Queue()

    def register(self, modifiers, key):
        self.registered = (modifiers, key)
        return self.succeed

    def thread_id(self):
        return 10

    def next_message(self):
        return self.messages.get(timeout=3)

    def unregister(self):
        self.unregistered = True

    def quit(self, thread_id):
        self.messages.put("quit")


def test_hotkey_registration_and_unregistration():
    api = FakeHotkeyAPI()
    listener = HotkeyListener(api=api)
    listener.start(lambda: None)
    assert api.registered == (0x0008 | 0x0001, ord("S"))
    listener.stop()
    assert api.unregistered


def test_hotkey_conflict_is_explicit():
    listener = HotkeyListener(api=FakeHotkeyAPI(False))
    with pytest.raises(RuntimeError, match="hotkey"):
        listener.start(lambda: None)
    listener.stop()


class Overlay:
    def __init__(self):
        self.events = []

    def present(self, state, text):
        self.events.append(("noactivate", state, text))

    def hide(self):
        self.events.append(("hide",))

    def close(self):
        self.events.append(("close",))


def test_indicator_only_uses_nonactivating_overlay():
    overlay = Overlay()
    indicator = Indicator(adapter=overlay)
    for state in ("recording", "transcribing", "copy", "error"):
        indicator.show(state, "example" if state == "copy" else None)
    indicator.show("idle")
    assert [event[0] for event in overlay.events] == ["noactivate"] * 4 + ["hide"]
    indicator.close()
    assert overlay.events[-1] == ("close",)


def test_fallback_text_can_be_selected_and_copy_failure_is_visible(monkeypatch):
    from transcriber import indicator as module

    class FailingClipboard:
        def __init__(self, **kwargs):
            pass

        def set_clipboard(self, text):
            return False

    monkeypatch.setattr(module, "WindowsInsertion", FailingClipboard)
    root = tk.Tk()
    try:
        overlay = _TkOverlay(root, lambda: None)
        overlay.present("copy", "private words")
        overlay.transcript.tag_add("sel", "1.0", "end-1c")
        assert overlay.transcript.get("sel.first", "sel.last") == "private words"
        overlay._copy()
        assert "failed" in overlay.label.cget("text").lower()
    finally:
        root.destroy()


def test_dismissing_fallback_does_not_exit():
    root = tk.Tk()
    closed = []
    try:
        overlay = _TkOverlay(root, lambda: closed.append(True))
        overlay.present("error", "Error")
        overlay.dismiss_button.invoke()
        assert not closed
        assert root.state() == "withdrawn"
    finally:
        root.destroy()


def test_asset_validation_rejects_changes(tmp_path, monkeypatch):
    paths = Paths.for_home(tmp_path)
    paths.model.parent.mkdir(parents=True)
    paths.cli.parent.mkdir(parents=True)
    paths.model.write_bytes(b"model")
    paths.vad_model.write_bytes(b"vad")
    paths.cli.write_bytes(b"cli")
    dll = paths.cli.parent / "whisper.dll"
    dll.write_bytes(b"dll")

    def digest(data):
        return hashlib.sha256(data).hexdigest()

    monkeypatch.setattr(runtime, "MODEL_SHA256", digest(b"model"))
    monkeypatch.setattr(runtime, "VAD_SHA256", digest(b"vad"))
    (paths.cli.parent / "manifest.json").write_text(
        json.dumps(
            {
                "version": "v1.9.5",
                "source_commit": runtime.SOURCE_COMMIT,
                "model_sha256": digest(b"model"),
                "vad_sha256": digest(b"vad"),
                "cli_sha256": digest(b"cli"),
                "dll_sha256": {"whisper.dll": digest(b"dll")},
            }
        )
    )
    assert runtime.check_assets(paths)
    paths.vad_model.write_bytes(b"changed")
    assert not runtime.check_assets(paths)
    paths.vad_model.write_bytes(b"vad")
    manifest_path = paths.cli.parent / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["vad_sha256"] = digest(b"wrong")
    manifest_path.write_text(json.dumps(manifest))
    assert not runtime.check_assets(paths)
    manifest["vad_sha256"] = digest(b"vad")
    manifest_path.write_text(json.dumps(manifest))
    paths.vad_model.unlink()
    assert not runtime.check_assets(paths)
    paths.vad_model.write_bytes(b"vad")
    paths.cli.write_bytes(b"tampered")
    assert not runtime.check_assets(paths)
    paths.cli.write_bytes(b"cli")
    dll.unlink()
    assert not runtime.check_assets(paths)


def test_runtime_start_wires_queue_and_reports_registration_error(tmp_path):
    paths = Paths.for_home(tmp_path)
    paths.tmp.mkdir(parents=True)
    orphan = paths.tmp / "yat-orphan.wav"
    orphan.write_bytes(b"audio")
    overlay = Overlay()
    listener = FakeListener()
    loop = FakeLoop()
    app = runtime.Runtime(
        paths=paths,
        indicator=Indicator(adapter=overlay),
        listener=listener,
        loop=loop,
        assets_ok=lambda paths: True,
        recorder=FakeRecorder(),
    )
    assert app.start()
    assert not orphan.exists()
    listener.callback()
    app.drain()
    assert app.controller.state in {"recording", "idle"}
    app.shutdown()
    assert listener.stopped

    bad = runtime.Runtime(
        paths=paths,
        indicator=Indicator(adapter=overlay),
        listener=FakeListener(fail=True),
        loop=FakeLoop(),
        assets_ok=lambda paths: True,
    )
    assert not bad.start()
    assert overlay.events[-1][1] == "error"


class FakeListener:
    def __init__(self, fail=False):
        self.fail = fail
        self.stopped = False
        self.callback = None

    def start(self, callback):
        if self.fail:
            raise RuntimeError("hotkey unavailable")
        self.callback = callback

    def stop(self):
        self.stopped = True


class FakeLoop:
    def after(self, delay, callback):
        pass


class FakeRecorder:
    def start(self):
        pass

    def close(self):
        pass
