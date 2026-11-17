import io
import uuid

from transcriber import service
from transcriber.service import InstanceSignals


def test_singleton_and_stop_signal():
    name = f"Local\\yat-test-{uuid.uuid4().hex}"
    owner = InstanceSignals.acquire(name)
    assert owner is not None
    try:
        assert InstanceSignals.acquire(name) is None
        assert not owner.stop_requested()
        assert InstanceSignals.request_stop(name)
        assert owner.stop_requested()
    finally:
        owner.close()
    assert not InstanceSignals.request_stop(name)
    replacement = InstanceSignals.acquire(name)
    assert replacement is not None
    replacement.close()


def test_stop_without_instance_is_safe():
    name = f"Local\\yat-test-{uuid.uuid4().hex}"
    assert not InstanceSignals.request_stop(name)


def test_instance_name_uses_current_windows_sid():
    assert service._instance_name().startswith("Local\\yat-S-1-")
    assert service._instance_name() == service._instance_name()


def test_launcher_reports_success_only_after_ready(monkeypatch):
    class Child:
        stdout = io.BytesIO(b"ready\n")

        def wait(self, timeout=None):
            raise AssertionError("ready child must remain running")

    monkeypatch.setattr(service.subprocess, "Popen", lambda *a, **k: Child())
    ok, message = service.start_service()
    assert ok
    assert "started" in message.lower()


def test_launcher_reports_startup_error(monkeypatch):
    class Child:
        stdout = io.BytesIO(b"error:assets_or_hotkey\n")

        def wait(self, timeout=None):
            return 1

    monkeypatch.setattr(service.subprocess, "Popen", lambda *a, **k: Child())
    ok, message = service.start_service()
    assert not ok
    assert "assets" in message.lower() or "hotkey" in message.lower()


def test_launcher_timeout_terminates_only_its_child(monkeypatch):
    class Child:
        stdout = None
        killed = False

        def kill(self):
            self.killed = True

        def wait(self, timeout=None):
            return 1

    child = Child()
    monkeypatch.setattr(service.subprocess, "Popen", lambda *a, **k: child)
    monkeypatch.setattr(service, "_read_startup", lambda child, timeout: None)
    ok, message = service.start_service()
    assert not ok
    assert "timed out" in message.lower()
    assert child.killed
