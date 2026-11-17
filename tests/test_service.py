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


def test_stop_without_service_is_success(monkeypatch):
    monkeypatch.setattr(
        service, "_instance_name", lambda: f"Local\\yat-{uuid.uuid4().hex}"
    )
    ok, message = service.stop_service()
    assert ok
    assert "not running" in message.lower()


def test_stop_signals_instance_and_waits_for_release(monkeypatch):
    import threading

    name = f"Local\\yat-test-{uuid.uuid4().hex}"
    ready = threading.Event()
    observed = []

    def owner_thread():
        owner = InstanceSignals.acquire(name)
        assert owner is not None
        ready.set()
        while not owner.stop_requested():
            threading.Event().wait(0.01)
        observed.append(True)
        owner.close()

    thread = threading.Thread(target=owner_thread)
    thread.start()
    assert ready.wait(2)
    monkeypatch.setattr(service, "_instance_name", lambda: name)
    try:
        ok, message = service.stop_service()
        assert ok, message
        assert observed == [True]
    finally:
        InstanceSignals.request_stop(name)
        thread.join(timeout=2)
    assert not thread.is_alive()


def test_stop_timeout_never_terminates_process(monkeypatch):
    class Kernel:
        def OpenMutexW(self, *args):
            return 1

        def WaitForSingleObject(self, *args):
            return 258

        def CloseHandle(self, *args):
            return 1

    monkeypatch.setattr(service, "_instance_name", lambda: "test")
    monkeypatch.setattr(service, "_kernel", Kernel())
    monkeypatch.setattr(InstanceSignals, "request_stop", lambda name: True)
    ok, message = service.stop_service()
    assert not ok
    assert "timed out" in message.lower()


def test_launcher_reports_duplicate_instance(monkeypatch):
    class Child:
        stdout = io.BytesIO(b"error:already_running\n")

        def wait(self, timeout=None):
            return 1

    monkeypatch.setattr(service.subprocess, "Popen", lambda *a, **k: Child())
    ok, message = service.start_service()
    assert not ok
    assert "already running" in message.lower()


def test_detached_child_handshake_duplicate_and_stop(monkeypatch):
    import sys
    from concurrent.futures import ThreadPoolExecutor

    name = f"Local\\yat-integration-{uuid.uuid4().hex}"
    code = f"""
import time
from transcriber import service
import transcriber.__main__ as runtime
service._instance_name = lambda: {name!r}
def fake_main(signals, report):
    report("ready")
    while not signals.stop_requested():
        time.sleep(0.01)
    return 0
runtime.main = fake_main
raise SystemExit(service._child_main())
"""
    real_popen = service.subprocess.Popen

    def launch(args, **kwargs):
        return real_popen([sys.executable, "-c", code], **kwargs)

    monkeypatch.setattr(service.subprocess, "Popen", launch)
    monkeypatch.setattr(service, "_instance_name", lambda: name)
    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(lambda _: service.start_service(), range(2)))
        assert sum(ok for ok, _ in results) == 1
        assert any("already running" in message.lower() for _, message in results)
        ok, message = service.stop_service()
        assert ok, message
        ok, message = service.stop_service()
        assert ok
        assert "not running" in message.lower()
    finally:
        service.stop_service()
