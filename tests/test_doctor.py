from transcriber import doctor, microphones


def test_doctor_success_without_opening_audio(monkeypatch):
    monkeypatch.setattr(doctor.platform, "system", lambda: "Windows")
    monkeypatch.setattr(doctor.platform, "machine", lambda: "AMD64")
    monkeypatch.setattr(doctor.platform, "version", lambda: "10.0.26100")
    monkeypatch.setattr(doctor.sys, "version_info", (3, 13, 1))
    monkeypatch.setattr(doctor, "check_assets", lambda paths: True)
    monkeypatch.setattr(microphones, "read_selection", lambda: None)
    monkeypatch.setattr(microphones.sd, "check_input_settings", lambda **kwargs: None)
    monkeypatch.setattr(
        microphones.sd,
        "InputStream",
        lambda *a, **kw: (_ for _ in ()).throw(AssertionError()),
    )
    monkeypatch.setattr(doctor, "check_shortcut", lambda: (True, "available"))
    checks = doctor.run_checks()
    assert all(status is True for _, status, _ in checks)


def test_doctor_reports_missing_assets_and_microphone(monkeypatch):
    monkeypatch.setattr(doctor, "check_assets", lambda paths: False)

    def missing(**kwargs):
        raise RuntimeError("device unavailable")

    monkeypatch.setattr(microphones, "read_selection", lambda: None)
    monkeypatch.setattr(microphones.sd, "check_input_settings", missing)
    monkeypatch.setattr(doctor, "check_shortcut", lambda: (None, "unknown"))
    checks = {name: (status, text) for name, status, text in doctor.run_checks()}
    assert checks["assets"][0] is False
    assert checks["microphone"][0] is False
    assert checks["shortcut"][0] is None
    assert "setup" in checks["assets"][1].lower()


def test_doctor_cli_returns_error_on_failed_required_check(monkeypatch):
    from typer.testing import CliRunner

    from transcriber.cli import app

    monkeypatch.setattr(doctor, "run_checks", lambda: [("assets", False, "Run setup")])
    result = CliRunner().invoke(app, ["doctor"])
    assert result.exit_code != 0
    assert "Run setup" in result.output


def test_doctor_cli_allows_unknown_shortcut(monkeypatch):
    from typer.testing import CliRunner

    from transcriber.cli import app

    monkeypatch.setattr(
        doctor, "run_checks", lambda: [("shortcut", None, "Cannot check safely")]
    )
    assert CliRunner().invoke(app, ["doctor"]).exit_code == 0


def test_shortcut_probe_unregisters_on_success_and_conflict(monkeypatch):
    calls = []

    class Kernel:
        def OpenMutexW(self, *args):
            import ctypes

            ctypes.set_last_error(2)
            return None

    class Listener:
        conflict = False

        def start(self, callback):
            if self.conflict:
                raise RuntimeError("conflict")

        def stop(self):
            calls.append("stop")

    monkeypatch.setattr(doctor.service, "_instance_name", lambda: "test")
    monkeypatch.setattr(doctor.service, "_kernel", Kernel())
    monkeypatch.setattr(doctor, "HotkeyListener", Listener)
    assert doctor.check_shortcut()[0] is True
    Listener.conflict = True
    assert doctor.check_shortcut()[0] is False
    assert calls == ["stop", "stop"]


def test_shortcut_reports_managed_instance(monkeypatch):
    class Kernel:
        def OpenMutexW(self, *args):
            return 123

        def CloseHandle(self, handle):
            assert handle == 123

    monkeypatch.setattr(doctor.service, "_instance_name", lambda: "test")
    monkeypatch.setattr(doctor.service, "_kernel", Kernel())
    status, message = doctor.check_shortcut()
    assert status is None
    assert "instance" in message
