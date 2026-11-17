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
