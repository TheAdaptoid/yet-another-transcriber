import re
import tkinter as tk

import pytest

from transcriber.indicator import _TkOverlay


@pytest.fixture
def overlay(tk_master):
    root = tk.Toplevel(tk_master)
    window = _TkOverlay(root, lambda: None)
    try:
        yield window
    finally:
        if root.winfo_exists():
            window.close()


def test_states_have_distinct_ribbons_and_real_text(overlay):
    overlay.present("recording", None)
    overlay.root.update()
    assert overlay.root.winfo_width() >= 230
    assert overlay.frame.winfo_width() >= overlay.root.winfo_width() - 7
    assert overlay.state_label.cget("text") == "RECORDING"
    assert overlay.ribbon.cget("bg") == "#F36746"
    assert overlay.label.cget("text") == "Recording…"
    assert overlay.hint_label.cget("text") == "Win+Alt+S to stop"
    assert overlay.hint_label.winfo_manager()
    assert overlay.close_button.winfo_manager()
    assert not overlay.copy_button.winfo_manager()
    assert not overlay.dismiss_button.winfo_manager()

    overlay.present("transcribing", None)
    overlay.root.update_idletasks()
    assert overlay.root.winfo_width() >= 230
    assert overlay.state_label.cget("text") == "TRANSCRIBING"
    assert overlay.ribbon.cget("bg") == "#A6D4EF"
    assert overlay.label.cget("text") == "Transcribing…"
    assert overlay.hint_label.cget("text") == ""
    assert not overlay.hint_label.winfo_manager()
    assert overlay.close_button.winfo_manager()


def test_cancel_button_only_shown_for_active_states_and_invokes_callback(overlay):
    calls = []
    overlay.on_cancel = lambda: calls.append("cancel")
    for state in ("recording", "transcribing"):
        overlay.present(state, None)
        assert overlay.cancel_button.winfo_manager()
        overlay.cancel_button.invoke()
    assert calls == ["cancel", "cancel"]
    for state in ("error", "copy"):
        overlay.present(state, None)
        assert not overlay.cancel_button.winfo_manager()


def test_error_uses_dynamic_text_and_keeps_actions(overlay):
    overlay.present("error", "Win+Alt+S could not be registered.")
    assert overlay.state_label.cget("text") == "ERROR"
    assert overlay.ribbon.cget("bg") == "#F5CB5E"
    assert overlay.label.cget("text") == "Win+Alt+S could not be registered."
    assert overlay.dismiss_button.winfo_manager()
    assert overlay.close_button.winfo_manager()
    assert not overlay.copy_button.winfo_manager()

    overlay.present("error", None)
    assert overlay.label.cget("text") == "Dictation failed."


def test_copy_result_is_complete_selectable_and_reports_clipboard_outcomes(
    overlay, monkeypatch
):
    from transcriber import indicator

    class Clipboard:
        succeed = True

        def __init__(self, *, owner):
            self.owner = owner

        def set_clipboard(self, text):
            assert text == result
            return self.succeed

    result = "\n".join(f"Example line {n}" for n in range(120))
    monkeypatch.setattr(indicator, "WindowsInsertion", Clipboard)
    overlay.present("copy", result)
    assert overlay.state_label.cget("text") == "RESULT"
    assert overlay.ribbon.cget("bg") == "#F5CB5E"
    assert overlay.label.cget("text") == "Could not paste. Select or copy this result."
    assert overlay.transcript.get("1.0", "end-1c") == result
    panels = overlay.separator.master.pack_slaves()
    assert panels.index(overlay.transcript_holder) < panels.index(overlay.separator)
    assert panels.index(overlay.separator) < panels.index(overlay.close_button.master)
    overlay.transcript.tag_add("sel", "1.0", "1.8")
    assert overlay.transcript.get("sel.first", "sel.last") == "Example "
    assert all(
        button.winfo_manager()
        for button in (
            overlay.copy_button,
            overlay.dismiss_button,
            overlay.close_button,
        )
    )

    overlay.copy_button.invoke()
    assert overlay.label.cget("text") == "Copied. You can dismiss this result."
    Clipboard.succeed = False
    overlay.copy_button.invoke()
    assert overlay.label.cget("text") == "Copy failed. Select the text and try again."
    assert overlay.transcript.get("1.0", "end-1c") == result


def _assert_within(root, area):
    root.update_idletasks()
    match = re.match(r"(\d+)x(\d+)\+(\d+)\+(\d+)", root.winfo_geometry())
    assert match is not None
    width, height, x, y = map(int, match.groups())
    left, top, right, bottom = area
    assert left <= x and top <= y
    assert x + width <= right and y + height <= bottom


def _assert_visible_inside(root, widget):
    assert widget.winfo_ismapped()
    assert widget.winfo_rootx() >= root.winfo_rootx()
    assert widget.winfo_rooty() >= root.winfo_rooty()
    assert widget.winfo_rootx() + widget.winfo_width() <= (
        root.winfo_rootx() + root.winfo_width()
    )
    assert widget.winfo_rooty() + widget.winfo_height() <= (
        root.winfo_rooty() + root.winfo_height()
    )


@pytest.mark.parametrize("state", ["recording", "transcribing"])
def test_cancel_and_exit_fit_in_small_work_area(overlay, monkeypatch, state):
    area = (0, 0, 320, 270)
    monkeypatch.setattr(overlay, "_work_area", lambda: area)
    overlay.present(state, None)
    overlay.root.update()
    _assert_within(overlay.root, area)
    _assert_visible_inside(overlay.root, overlay.cancel_button)
    _assert_visible_inside(overlay.root, overlay.close_button)


def test_longer_copy_feedback_keeps_actions_visible(overlay, monkeypatch):
    from transcriber import indicator

    class Clipboard:
        def __init__(self, *, owner):
            pass

        def set_clipboard(self, text):
            return True

    monkeypatch.setattr(indicator, "WindowsInsertion", Clipboard)
    monkeypatch.setattr(overlay, "_work_area", lambda: (0, 0, 320, 270))
    overlay.present("copy", "Sample result")
    configure = overlay.label.config

    def longer_feedback(**kwargs):
        if kwargs.get("text") == "Copied. You can dismiss this result.":
            kwargs["text"] = (
                "Copied. You can dismiss this result. " * 2 + "Copied. You can dismiss"
            )
        return configure(**kwargs)

    monkeypatch.setattr(overlay.label, "config", longer_feedback)
    overlay.copy_button.invoke()
    overlay.root.update()
    for button in (overlay.copy_button, overlay.dismiss_button, overlay.close_button):
        _assert_visible_inside(overlay.root, button)
    _assert_visible_inside(overlay.root, overlay.transcript)
    assert overlay.transcript.winfo_height() > 0


def test_long_error_and_result_stay_within_work_area(overlay, monkeypatch):
    area = (0, 0, 480, 300)
    monkeypatch.setattr(overlay, "_work_area", lambda: area, raising=False)
    error = "Microphone" * 160
    overlay.present("error", error)
    _assert_within(overlay.root, area)
    assert overlay.error_details.get("1.0", "end-1c") == error
    assert overlay.dismiss_button.winfo_manager()
    assert overlay.close_button.winfo_manager()

    result = "\n".join(f"Example line {n}" for n in range(140))
    overlay.present("copy", result)
    _assert_within(overlay.root, area)
    assert overlay.transcript.get("1.0", "end-1c") == result
    assert overlay.copy_button.winfo_manager()


@pytest.mark.parametrize("scaling", [1.0, 1.25, 1.5])
def test_layout_respects_tk_scaling(overlay, monkeypatch, scaling):
    area = (0, 0, 520, 350)
    monkeypatch.setattr(overlay, "_work_area", lambda: area, raising=False)
    prior = float(overlay.root.tk.call("tk", "scaling"))
    try:
        overlay.root.tk.call("tk", "scaling", scaling)
        overlay.present("copy", "Sample text " * 120)
        _assert_within(overlay.root, area)
        assert overlay.copy_button.winfo_manager()
    finally:
        overlay.root.tk.call("tk", "scaling", prior)


@pytest.mark.parametrize("state", ["copy", "error"])
@pytest.mark.parametrize(
    ("area", "scaling"),
    [((0, 0, 320, 240), None), ((0, 0, 420, 300), 1.5)],
)
def test_small_work_area_keeps_actions_and_text_readable(
    overlay, monkeypatch, state, area, scaling
):
    monkeypatch.setattr(overlay, "_work_area", lambda: area)
    prior = float(overlay.root.tk.call("tk", "scaling"))
    if scaling is not None:
        overlay.root.tk.call("tk", "scaling", scaling)
    text = (
        "\n".join(f"Example line {n}" for n in range(100))
        if state == "copy"
        else "Microphone" * 160
    )
    try:
        overlay.present(state, text)
        overlay.root.update()
        _assert_within(overlay.root, area)
        assert overlay.close_button.winfo_height() >= 25
        assert overlay.dismiss_button.winfo_height() >= 25
        _assert_visible_inside(overlay.root, overlay.close_button)
        _assert_visible_inside(overlay.root, overlay.dismiss_button)
        details = overlay.transcript if state == "copy" else overlay.error_details
        if state == "copy":
            assert overlay.copy_button.winfo_height() >= 25
            _assert_visible_inside(overlay.root, overlay.copy_button)
        assert details.winfo_height() >= 20
        _assert_visible_inside(overlay.root, details)
        assert details.get("1.0", "end-1c") == text
        scrollbar = next(
            child
            for child in details.master.winfo_children()
            if isinstance(child, tk.Scrollbar)
        )
        assert scrollbar.winfo_ismapped()
        assert scrollbar.winfo_width() >= 10
        assert details.yview()[1] < 1
    finally:
        overlay.root.tk.call("tk", "scaling", prior)


def _clock(overlay, monkeypatch):
    jobs = {}
    cancelled = []

    def after(delay, callback):
        token = f"job-{len(jobs) + len(cancelled) + 1}"
        jobs[token] = (delay, callback)
        return token

    def cancel(token):
        cancelled.append(token)
        jobs.pop(token, None)

    monkeypatch.setattr(overlay.root, "after", after)
    monkeypatch.setattr(overlay.root, "after_cancel", cancel)
    return jobs, cancelled


def _signal(overlay):
    canvas = overlay.activity_label
    return tuple(tuple(canvas.coords(item)) for item in canvas.find_all())


def test_activity_moves_only_in_active_states_and_cancels_on_transition(
    overlay, monkeypatch
):
    monkeypatch.setattr(overlay, "_animations_enabled", lambda: True, raising=False)
    jobs, cancelled = _clock(overlay, monkeypatch)
    overlay.present("recording", None)
    record = _signal(overlay)
    assert len(jobs) == 1
    first, (delay, tick) = next(iter(jobs.items()))
    assert 800 <= delay <= 1200
    jobs.pop(first)
    tick()
    assert _signal(overlay) != record
    successor = overlay._animation_job

    overlay.present("transcribing", None)
    assert successor in cancelled
    assert _signal(overlay) != record
    assert overlay._animation_job in jobs
    overlay.present("error", "A microphone problem.")
    assert overlay._animation_job is None
    assert not overlay.activity_label.winfo_manager()
    overlay.present("copy", "Example text")
    assert overlay._animation_job is None


def test_hide_and_close_cancel_pending_activity(overlay, monkeypatch):
    monkeypatch.setattr(overlay, "_animations_enabled", lambda: True, raising=False)
    jobs, cancelled = _clock(overlay, monkeypatch)
    overlay.present("recording", None)
    first = overlay._animation_job
    stale = jobs[first][1]
    overlay.hide()
    assert first in cancelled
    assert overlay._animation_job is None
    stale()
    overlay.present("transcribing", None)
    second = overlay._animation_job
    late = jobs[second][1]
    overlay.close()
    assert second in cancelled
    late()


@pytest.mark.parametrize("preference", ["disabled", "unavailable"])
def test_disabled_or_unavailable_animation_is_static(overlay, monkeypatch, preference):
    jobs, _ = _clock(overlay, monkeypatch)
    if preference == "disabled":
        monkeypatch.setattr(
            overlay, "_animations_enabled", lambda: False, raising=False
        )
    else:
        from transcriber import indicator

        def unavailable(*args):
            return 0

        monkeypatch.setattr(
            indicator.ctypes.windll.user32, "SystemParametersInfoW", unavailable
        )
    overlay.present("recording", None)
    assert _signal(overlay)
    assert overlay._animation_job is None
    assert not jobs
    overlay.present("transcribing", None)
    assert _signal(overlay)
    assert overlay._animation_job is None
    assert not jobs
