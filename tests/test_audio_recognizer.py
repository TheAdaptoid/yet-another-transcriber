import json
import subprocess
import threading
import wave

import numpy as np
import pytest

from transcriber.audio import Recorder, cleanup_temp_wavs, write_temp_wav
from transcriber.config import MAX_SECONDS, SAMPLE_RATE, Paths
from transcriber.diagnostics import make_logger
from transcriber.recognizer import RecognitionError, Recognizer


class FakeStream:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.callback = kwargs["callback"]

    def start(self):
        pass

    def stop(self):
        pass

    def close(self):
        pass

    def deliver(self, samples):
        self.callback(
            np.array(samples, dtype=np.int16).reshape(-1, 1), len(samples), None, None
        )


def test_recorder_format_copy_cap_and_late_callback():
    streams = []

    def factory(**kwargs):
        stream = FakeStream(**kwargs)
        streams.append(stream)
        return stream

    recorder = Recorder(stream_factory=factory)
    recorder.start()
    first = streams[-1]
    assert (
        first.kwargs["samplerate"],
        first.kwargs["channels"],
        first.kwargs["dtype"],
    ) == (
        SAMPLE_RATE,
        1,
        "int16",
    )
    first.deliver([1, 2])
    samples = recorder.stop()
    first.deliver([3])
    assert samples.tolist() == [1, 2]
    recorder.start()
    first.deliver([9])
    streams[-1].deliver([4])
    assert recorder.stop().tolist() == [4]
    recorder.start()
    streams[-1].deliver(np.ones(SAMPLE_RATE * MAX_SECONDS + 10, dtype=np.int16))
    assert recorder.stop().size == SAMPLE_RATE * MAX_SECONDS


def test_wave_format_and_owned_cleanup(tmp_path):
    path = write_temp_wav(np.array([1, -2], dtype=np.int16), tmp_path)
    with wave.open(str(path), "rb") as f:
        assert (
            f.getframerate(),
            f.getnchannels(),
            f.getsampwidth(),
            f.getnframes(),
        ) == (
            SAMPLE_RATE,
            1,
            2,
            2,
        )
    other = tmp_path / "other.wav"
    other.write_bytes(b"keep")
    cleanup_temp_wavs(tmp_path)
    assert not path.exists()
    assert other.exists()


def test_silence_never_launches_cli(tmp_path):
    paths = Paths.for_home(tmp_path)

    def fail(*args, **kwargs):
        raise AssertionError("CLI launched")

    recognizer = Recognizer(make_logger(paths.log), popen=fail)
    assert recognizer.transcribe(np.array([], dtype=np.int16), paths, "a") == ""
    assert recognizer.transcribe(np.zeros(800, dtype=np.int16), paths, "a") == ""
    assert (
        recognizer.transcribe(
            np.tile(np.array([-3, 4], dtype=np.int16), 400), paths, "a"
        )
        == ""
    )


def test_recognition_logs_only_metrics_and_cleans_wave(tmp_path):
    paths = Paths.for_home(tmp_path)
    paths.cli.parent.mkdir(parents=True)
    paths.cli.touch()
    calls = []

    class Process:
        returncode = 0

        def communicate(self, timeout):
            assert timeout > 0
            return ("dictated secret words", "stderr dictated secret words")

    def launch(args, **kwargs):
        calls.append(args)
        assert kwargs["stdout"] == subprocess.PIPE
        assert kwargs["stderr"] == subprocess.PIPE
        return Process()

    recognizer = Recognizer(make_logger(paths.log), popen=launch)
    assert recognizer.transcribe(np.array([1000], dtype=np.int16), paths, "a") == (
        "dictated secret words"
    )
    args = calls[0]
    assert args[0] == str(paths.cli)
    assert args[args.index("-m") + 1] == str(paths.model)
    assert args[args.index("-l") + 1] == "en"
    assert all(flag in args for flag in ("-ng", "-np", "-nt"))
    assert not list(paths.tmp.glob("yat-*.wav"))
    log = paths.log.read_text()
    assert "dictated secret words" not in log
    assert {json.loads(line)["event"] for line in log.splitlines()} >= {
        "wav_write",
        "cli_start",
        "inference",
    }


@pytest.mark.parametrize("mode", ["missing", "failed", "timeout"])
def test_recognition_failure_is_categorized_and_removes_wav(tmp_path, mode):
    paths = Paths.for_home(tmp_path)
    if mode != "missing":
        paths.cli.parent.mkdir(parents=True)
        paths.cli.touch()

    class Process:
        returncode = 1

        def communicate(self, timeout=None):
            if mode == "timeout" and timeout is not None:
                raise subprocess.TimeoutExpired("secret speech", timeout)
            return ("secret speech", "secret speech")

        def kill(self):
            pass

    recognizer = Recognizer(make_logger(paths.log), popen=lambda *a, **kw: Process())
    with pytest.raises(RecognitionError) as exc:
        recognizer.transcribe(np.array([1000], dtype=np.int16), paths, "a")
    assert (
        exc.value.category
        == {
            "missing": "cli_missing",
            "failed": "cli_failed",
            "timeout": "cli_timeout",
        }[mode]
    )
    assert not list(paths.tmp.glob("yat-*.wav"))
    assert "secret speech" not in paths.log.read_text()


def test_wave_is_removed_even_when_diagnostics_fail(tmp_path, monkeypatch):
    from transcriber import recognizer as module

    paths = Paths.for_home(tmp_path)

    def broken_log(*args, **kwargs):
        raise OSError("log failed")

    monkeypatch.setattr(module, "log_event", broken_log)
    recognizer = Recognizer(make_logger(paths.log))
    with pytest.raises(OSError):
        recognizer.transcribe(np.array([1000], dtype=np.int16), paths, "a")
    assert not list(paths.tmp.glob("yat-*.wav"))


def test_close_terminates_inflight_recognizer(tmp_path):
    paths = Paths.for_home(tmp_path)
    paths.cli.parent.mkdir(parents=True)
    paths.cli.touch()
    started = threading.Event()
    killed = threading.Event()

    class Process:
        returncode = 1

        def communicate(self, timeout=None):
            started.set()
            assert killed.wait(3)
            return "", ""

        def kill(self):
            killed.set()

    recognizer = Recognizer(make_logger(paths.log), popen=lambda *a, **kw: Process())
    errors = []

    def transcribe():
        try:
            recognizer.transcribe(np.array([1000], dtype=np.int16), paths, "a")
        except RecognitionError as exc:
            errors.append(exc.category)

    thread = threading.Thread(target=transcribe)
    thread.start()
    assert started.wait(3)
    recognizer.close()
    thread.join(3)
    assert not thread.is_alive()
    assert killed.is_set()
    assert not list(paths.tmp.glob("yat-*.wav"))


def test_close_waits_for_wave_creation_to_finish(tmp_path, monkeypatch):
    from transcriber import recognizer as module

    paths = Paths.for_home(tmp_path)
    entered = threading.Event()
    release = threading.Event()
    closed = threading.Event()
    real_write = module.write_temp_wav

    def slow_write(samples, directory):
        entered.set()
        assert release.wait(3)
        return real_write(samples, directory)

    monkeypatch.setattr(module, "write_temp_wav", slow_write)
    recognizer = Recognizer(make_logger(paths.log))

    def transcribe():
        try:
            recognizer.transcribe(np.array([1000], dtype=np.int16), paths, "a")
        except RecognitionError:
            pass

    worker = threading.Thread(target=transcribe)
    worker.start()
    assert entered.wait(3)

    def close():
        recognizer.close()
        closed.set()

    closer = threading.Thread(target=close)
    closer.start()
    assert not closed.wait(0.1)
    release.set()
    closer.join(3)
    worker.join(3)
    assert closed.is_set()
    assert not list(paths.tmp.glob("yat-*.wav"))
