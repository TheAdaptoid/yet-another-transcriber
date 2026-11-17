import json

import numpy as np

from transcriber.config import Paths
from transcriber.diagnostics import make_logger
from transcriber.session import SessionController
from transcriber.targets import TargetSnapshot


class Recorder:
    def __init__(self):
        self.starts = 0
        self.stops = 0

    def start(self):
        self.starts += 1

    def stop(self):
        self.stops += 1
        return np.array([1000], dtype=np.int16)

    def close(self):
        pass


class Recognizer:
    def __init__(self):
        self.text = "private words"
        self.error = None
        self.closed = False

    def transcribe(self, samples, paths, session_id):
        if self.error:
            raise RuntimeError("private words")
        return self.text

    def close(self):
        self.closed = True


def setup_controller(tmp_path):
    paths = Paths.for_home(tmp_path)
    rec = Recorder()
    recognizer = Recognizer()
    states = []
    timers = []
    work = []
    ui = []
    pastes = []
    copies = []
    target = TargetSnapshot(42, (1, 2))
    clock = iter(range(10000))
    ctl = SessionController(
        paths=paths,
        logger=make_logger(paths.log),
        recorder=rec,
        recognizer=recognizer,
        show_state=lambda state, text: states.append((state, text)),
        capture=lambda: target,
        focused=lambda t: t == target,
        paste=lambda text, **kwargs: (
            pastes.append(text) or kwargs["on_clipboard"](0.1) or kwargs["guard"]()
        ),
        copy=lambda text: copies.append(text) or True,
        schedule=lambda delay, fn: timers.append((delay, fn)),
        worker=lambda fn: work.append(fn),
        post=lambda fn: ui.append(fn),
        clock=lambda: next(clock),
    )
    return ctl, rec, recognizer, states, timers, work, ui, pastes, copies, paths


def finish_work(work, ui):
    work.pop(0)()
    ui.pop(0)()


def test_session_transitions_timings_busy_and_one_id(tmp_path):
    ctl, rec, _, states, timers, work, ui, pastes, _, paths = setup_controller(tmp_path)
    ctl.on_hotkey()
    assert ctl.state == "recording"
    assert timers[0][0] == 60
    ctl.on_hotkey()
    assert ctl.state == "transcribing"
    ctl.on_hotkey()
    ctl.on_limit()
    assert rec.starts == 1 and rec.stops == 1
    finish_work(work, ui)
    assert ctl.state == "idle"
    assert pastes == ["private words"]
    assert [s[0] for s in states] == ["recording", "transcribing", "idle"]
    events = [json.loads(line) for line in paths.log.read_text().splitlines()]
    assert len({event["session_id"] for event in events}) == 1
    assert {event["event"] for event in events} >= {
        "mic_open",
        "recording",
        "focus_check",
        "clipboard_write",
        "paste",
        "stop_to_insertion",
    }
    assert any(
        event.get("output_characters") == len("private words") for event in events
    )
    assert all("process_name" not in event for event in events)
    assert any(event.get("model") == "ggml-base.en.bin" for event in events)
    assert "private words" not in paths.log.read_text()


def test_limit_only_stops_once_and_old_timer_cannot_stop_next_session(tmp_path):
    ctl, rec, _, _, timers, work, ui, _, _, _ = setup_controller(tmp_path)
    ctl.on_hotkey()
    old_timer = timers[0][1]
    old_timer()
    old_timer()
    assert rec.stops == 1
    finish_work(work, ui)
    ctl.on_hotkey()
    old_timer()
    assert ctl.state == "recording"
    assert rec.stops == 1


def test_missing_or_changed_focus_is_copyable_without_paste(tmp_path):
    ctl, _, _, states, _, work, ui, pastes, copies, _ = setup_controller(tmp_path)
    ctl.capture = lambda: None
    ctl.on_hotkey()
    ctl.on_hotkey()
    finish_work(work, ui)
    assert pastes == []
    assert copies == ["private words"]
    assert states[-1] == ("copy", "private words")
    ctl.capture = lambda: TargetSnapshot(42, (1,))
    ctl.focused = lambda target: False
    ctl.on_hotkey()
    ctl.on_hotkey()
    finish_work(work, ui)
    assert not pastes and len(copies) == 2


def test_session_sanitizes_multiline_text_before_automatic_paste(tmp_path):
    ctl, _, recognizer, _, _, work, ui, pastes, _, _ = setup_controller(tmp_path)
    recognizer.text = "first\r\nsecond\x1b[31m"
    ctl.on_hotkey()
    ctl.on_hotkey()
    finish_work(work, ui)
    assert pastes == ["first second"]


def test_silence_and_error_never_paste(tmp_path):
    ctl, _, recognizer, states, _, work, ui, pastes, _, _ = setup_controller(tmp_path)
    recognizer.text = ""
    ctl.on_hotkey()
    ctl.on_hotkey()
    finish_work(work, ui)
    assert ctl.state == "idle"
    assert not pastes
    recognizer.error = True
    ctl.on_hotkey()
    ctl.on_hotkey()
    finish_work(work, ui)
    assert states[-1][0] == "error"
    assert not pastes


def test_shutdown_while_processing_ignores_late_completion(tmp_path):
    ctl, rec, recognizer, _, _, work, ui, pastes, _, _ = setup_controller(tmp_path)
    ctl.on_hotkey()
    ctl.on_hotkey()
    ctl.close()
    assert recognizer.closed
    finish_work(work, ui)
    assert not pastes
    assert rec.stops == 1


def test_hotkeys_arriving_during_insertion_are_not_replayed(tmp_path):
    ctl, rec, _, _, _, work, ui, _, _, _ = setup_controller(tmp_path)
    queued_hotkeys = []

    def paste_during_hotkey(text, **kwargs):
        ctl.enqueue_hotkey(queued_hotkeys.append)
        return True

    ctl.paste = paste_during_hotkey
    ctl.on_hotkey()
    ctl.on_hotkey()
    finish_work(work, ui)
    for callback in queued_hotkeys:
        callback()
    assert ctl.state == "idle"
    assert rec.starts == 1


def test_old_queued_hotkey_is_invalidated_on_stop(tmp_path):
    ctl, rec, _, _, _, work, ui, _, _, _ = setup_controller(tmp_path)
    queued = []
    ctl.on_hotkey()
    ctl.enqueue_hotkey(queued.append)
    ctl.on_hotkey()
    finish_work(work, ui)
    queued.pop()()
    assert ctl.state == "idle"
    assert rec.starts == 1
