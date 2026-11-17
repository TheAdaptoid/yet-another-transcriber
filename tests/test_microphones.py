import pytest
from typer.testing import CliRunner

from transcriber.cli import app


@pytest.fixture
def inventory(monkeypatch, tmp_path):
    from transcriber import microphones

    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    devices = [
        {"name": "Mic A", "hostapi": 0, "max_input_channels": 1},
        {"name": "Output", "hostapi": 0, "max_input_channels": 0},
        {"name": "Mic B", "hostapi": 1, "max_input_channels": 1},
    ]
    monkeypatch.setattr(microphones.sd, "query_devices", lambda: devices)
    monkeypatch.setattr(
        microphones.sd, "query_hostapis", lambda: [{"name": "API A"}, {"name": "API B"}]
    )
    monkeypatch.setattr(microphones.sd.default, "device", (0, -1))
    return microphones, devices


def test_selection_survives_reorder_and_missing_or_duplicate_fails(inventory):
    microphones, devices = inventory
    microphones.select_device(2)
    assert microphones.resolve_device() == 2
    devices.reverse()
    assert microphones.resolve_device() == 0
    devices.append(devices[0].copy())
    with pytest.raises(microphones.MicrophoneError, match="ambiguous"):
        microphones.resolve_device()
    devices[:] = []
    with pytest.raises(microphones.MicrophoneError, match="missing"):
        microphones.resolve_device()


def test_invalid_settings_fail_closed(inventory, tmp_path):
    microphones, _ = inventory
    path = tmp_path / ".yat" / "microphone.json"
    path.parent.mkdir()
    path.write_text("invalid")
    with pytest.raises(microphones.MicrophoneError, match="settings"):
        microphones.resolve_device()


def test_cli_list_select_and_clear(inventory):
    microphones, _ = inventory
    runner = CliRunner()
    result = runner.invoke(app, ["microphone", "list"])
    assert result.exit_code == 0
    assert "Mic A" in result.output and "Mic B" in result.output
    assert "Mic A [API A] (default)" in result.output
    assert runner.invoke(app, ["microphone", "select", "2"]).exit_code == 0
    assert microphones.resolve_device() == 2
    assert runner.invoke(app, ["microphone", "clear"]).exit_code == 0
    assert microphones.resolve_device() is None


def test_doctor_checks_selected_format_without_opening_stream(inventory, monkeypatch):
    from transcriber import doctor

    microphones, _ = inventory
    microphones.select_device(2)
    calls = []
    monkeypatch.setattr(
        microphones.sd, "check_input_settings", lambda **kw: calls.append(kw)
    )
    monkeypatch.setattr(doctor, "check_shortcut", lambda: (None, "unknown"))
    monkeypatch.setattr(doctor, "check_assets", lambda paths: False)
    result = dict((name, (status, text)) for name, status, text in doctor.run_checks())
    assert result["microphone"][0] is True
    assert calls == [
        {"device": 2, "samplerate": 16000, "channels": 1, "dtype": "int16"}
    ]


def test_unsupported_format_reports_actionable_failure(inventory, monkeypatch):
    from transcriber import doctor

    microphones, _ = inventory
    monkeypatch.setattr(
        microphones.sd,
        "check_input_settings",
        lambda **kw: (_ for _ in ()).throw(ValueError("unsupported")),
    )
    monkeypatch.setattr(doctor, "check_shortcut", lambda: (None, "unknown"))
    monkeypatch.setattr(doctor, "check_assets", lambda paths: False)
    checks = {name: (status, detail) for name, status, detail in doctor.run_checks()}
    assert checks["microphone"][0] is False
    assert "yat microphone list" in checks["microphone"][1]


def test_recorder_resolves_selection_at_each_start(inventory):
    from transcriber.audio import Recorder

    microphones, devices = inventory
    microphones.select_device(2)
    calls = []

    class Stream:
        def __init__(self, **kwargs):
            calls.append(kwargs)

        def start(self):
            pass

        def stop(self):
            pass

        def close(self):
            pass

    recorder = Recorder(stream_factory=Stream)
    recorder.start()
    recorder.stop()
    devices.reverse()
    recorder.start()
    recorder.stop()
    assert [call["device"] for call in calls] == [2, 0]


def test_invalid_utf8_settings_fail_closed(inventory, tmp_path):
    microphones, _ = inventory
    path = tmp_path / ".yat" / "microphone.json"
    path.parent.mkdir()
    path.write_bytes(b"\xff")
    with pytest.raises(microphones.MicrophoneError, match="settings"):
        microphones.resolve_device()


def test_list_shows_inventory_when_settings_are_invalid(inventory, tmp_path):
    path = tmp_path / ".yat" / "microphone.json"
    path.parent.mkdir()
    path.write_text("invalid")
    result = CliRunner().invoke(app, ["microphone", "list"])
    assert result.exit_code != 0
    assert "Mic A" in result.output
    assert "settings" in result.output.lower()


def test_recorder_does_not_open_stream_when_device_disappears(inventory):
    from transcriber.audio import Recorder

    microphones, devices = inventory
    microphones.select_device(2)
    calls = []

    class Stream:
        def __init__(self, **kwargs):
            calls.append(kwargs)

        def start(self):
            pass

        def stop(self):
            pass

        def close(self):
            pass

    recorder = Recorder(stream_factory=Stream)
    devices.pop()
    with pytest.raises(microphones.MicrophoneError, match="missing"):
        recorder.start()
    assert calls == []
    microphones.clear_selection()
    recorder.start()
    recorder.stop()
    assert calls[0]["device"] is None


def test_running_recorder_refreshes_cached_portaudio_inventory(inventory, monkeypatch):
    from transcriber.audio import Recorder

    microphones, devices = inventory
    microphones.select_device(2)
    physical = list(devices)
    snapshot = list(devices)
    events = []

    def initialize():
        snapshot[:] = physical
        events.append("initialize")

    monkeypatch.setattr(
        microphones.sd, "_terminate", lambda: events.append("terminate")
    )
    monkeypatch.setattr(microphones.sd, "_initialize", initialize)
    monkeypatch.setattr(microphones.sd, "query_devices", lambda: snapshot)
    opened = []

    class Stream:
        def __init__(self, **kwargs):
            opened.append(kwargs["device"])

        def start(self):
            pass

        def stop(self):
            pass

        def close(self):
            pass

    recorder = Recorder(stream_factory=Stream)
    recorder.start()
    recorder.stop()
    physical.reverse()
    recorder.start()
    recorder.stop()
    assert opened == [2, 0]
    assert events == ["terminate", "initialize", "terminate", "initialize"]


def test_second_recorder_cannot_refresh_while_stream_is_open(inventory, monkeypatch):
    from transcriber.audio import Recorder

    microphones, _ = inventory
    calls = []
    monkeypatch.setattr(microphones.sd, "_terminate", lambda: calls.append("terminate"))
    monkeypatch.setattr(
        microphones.sd, "_initialize", lambda: calls.append("initialize")
    )

    class Stream:
        def __init__(self, **kwargs):
            pass

        def start(self):
            pass

        def stop(self):
            pass

        def close(self):
            pass

    first = Recorder(stream_factory=Stream)
    second = Recorder(stream_factory=Stream)
    first.start()
    try:
        with pytest.raises(microphones.MicrophoneError, match="in use"):
            second.start()
        assert calls == ["terminate", "initialize"]
    finally:
        first.stop()
    second.start()
    second.stop()
    assert calls == ["terminate", "initialize", "terminate", "initialize"]


def test_refresh_failure_retries_without_leaking_backend_lock(inventory, monkeypatch):
    from transcriber.audio import Recorder

    microphones, _ = inventory
    monkeypatch.setattr(microphones.sd, "_initialized", 1)

    def terminate():
        microphones.sd._initialized = 0

    attempts = []

    def initialize():
        attempts.append(True)
        if len(attempts) == 1:
            raise RuntimeError("backend unavailable")
        microphones.sd._initialized = 1

    monkeypatch.setattr(microphones.sd, "_terminate", terminate)
    monkeypatch.setattr(microphones.sd, "_initialize", initialize)
    opened = []

    class Stream:
        def __init__(self, **kwargs):
            opened.append(kwargs["device"])

        def start(self):
            pass

        def stop(self):
            pass

        def close(self):
            pass

    recorder = Recorder(stream_factory=Stream)
    with pytest.raises(microphones.MicrophoneError):
        recorder.start()
    assert opened == []
    recorder.start()
    recorder.stop()
    assert opened == [None]
    assert len(attempts) == 2
