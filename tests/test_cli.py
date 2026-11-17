from typer.testing import CliRunner

from transcriber.cli import app

runner = CliRunner()


def test_help_lists_commands():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    for name in ("start", "stop", "doctor"):
        assert name in result.output


def test_unknown_command_fails():
    result = runner.invoke(app, ["unknown"])
    assert result.exit_code != 0


def test_start_reports_service_result(monkeypatch):
    from transcriber import service

    monkeypatch.setattr(service, "start_service", lambda: (True, "started"))
    result = runner.invoke(app, ["start"])
    assert result.exit_code == 0
    assert "started" in result.output


def test_stop_reports_failure(monkeypatch):
    from transcriber import service

    monkeypatch.setattr(service, "stop_service", lambda: (False, "stop failed"))
    result = runner.invoke(app, ["stop"])
    assert result.exit_code != 0
    assert "stop failed" in result.output
