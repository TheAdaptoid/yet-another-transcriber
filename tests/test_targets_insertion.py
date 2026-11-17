from types import SimpleNamespace

from transcriber import insertion, targets


def test_target_requires_window_and_identity(monkeypatch):
    monkeypatch.setattr(targets, "_foreground", lambda: 123)
    monkeypatch.setattr(targets, "_focused_runtime_id", lambda: (1, 2))
    target = targets.capture_target()
    assert target == targets.TargetSnapshot(123, (1, 2))
    assert targets.still_focused(target)
    monkeypatch.setattr(targets, "_focused_runtime_id", lambda: (1, 3))
    assert not targets.still_focused(target)
    monkeypatch.setattr(targets, "_focused_runtime_id", lambda: ())
    assert targets.capture_target() is None
    monkeypatch.setattr(targets, "_focused_runtime_id", lambda: (1, 2))
    monkeypatch.setattr(targets, "_foreground", lambda: 124)
    assert not targets.still_focused(target)
    assert targets.capture_target() is not None
    monkeypatch.setattr(
        targets, "_focused_runtime_id", lambda: (_ for _ in ()).throw(OSError())
    )
    assert targets.capture_target() is None


def test_all_targets_sanitize_controls_and_ansi():
    assert insertion.safe_text("one\r\ntwo\t\x1b[31m") == "one two"
    assert insertion.safe_text("a\x00b\x07c\x9bd") == "a b c d"
    assert insertion.safe_text("one\n two\t!") == "one two !"


def test_password_or_disabled_element_is_not_a_target(monkeypatch):
    import comtypes.client

    element = SimpleNamespace(
        CurrentIsPassword=True, CurrentIsEnabled=True, GetRuntimeId=lambda: (1, 2)
    )
    monkeypatch.setattr(
        comtypes.client,
        "GetModule",
        lambda _: SimpleNamespace(CUIAutomation=object(), IUIAutomation=object()),
    )
    monkeypatch.setattr(
        comtypes.client,
        "CreateObject",
        lambda *args, **kwargs: SimpleNamespace(GetFocusedElement=lambda: element),
    )
    monkeypatch.setattr(targets, "_foreground", lambda: 123)
    assert targets.capture_target() is None
    element.CurrentIsPassword = False
    element.CurrentIsEnabled = False
    assert targets.capture_target() is None
    element.CurrentIsEnabled = True
    assert targets.capture_target() == targets.TargetSnapshot(123, (1, 2))
    del element.CurrentIsPassword
    assert targets.capture_target() is None


def test_foreground_change_during_capture_fails_closed(monkeypatch):
    windows = iter((123, 124))
    monkeypatch.setattr(targets, "_foreground", lambda: next(windows))
    monkeypatch.setattr(targets, "_focused_runtime_id", lambda: (1, 2))
    assert targets.capture_target() is None


class FakeWindows:
    def __init__(self):
        self.clipboard = None
        self.keys = []
        self.send_result = True

    def set_clipboard(self, text):
        self.clipboard = text
        return True

    def send_keys(self, keys):
        self.keys.extend(keys)
        return self.send_result


def test_paste_only_sends_ctrl_v_and_keeps_unicode_clipboard():
    win = FakeWindows()
    assert insertion.paste_text("hello 世界", guard=lambda: True, api=win)
    assert win.clipboard == "hello 世界"
    assert win.keys == [(0x11, False), (0x56, False), (0x56, True), (0x11, True)]


def test_focus_guard_and_failed_input_keep_clipboard():
    win = FakeWindows()
    assert not insertion.paste_text("saved", guard=lambda: False, api=win)
    assert win.clipboard == "saved"
    assert win.keys == []
    win.send_result = False
    assert not insertion.paste_text("saved", guard=lambda: True, api=win)
    assert win.clipboard == "saved"


def test_focus_exception_fails_closed():
    win = FakeWindows()

    def failed_guard():
        raise OSError("bad focus")

    assert not insertion.paste_text("saved", guard=failed_guard, api=win)
    assert win.keys == []


def test_clipboard_open_uses_owned_window_not_null(monkeypatch):
    calls = []
    monkeypatch.setattr(
        insertion, "_open_clipboard", lambda owner: calls.append(owner) or False
    )
    assert not insertion.WindowsInsertion(owner=123).set_clipboard("content")
    assert calls == [123]
    assert not insertion.WindowsInsertion().set_clipboard("content")
    assert calls == [123]
