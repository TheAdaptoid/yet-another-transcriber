import json

import pytest

from transcriber.config import Paths


def test_existing_installation_defaults_to_base(tmp_path):
    assert Paths.for_home(tmp_path).model.name == "ggml-base.en.bin"


def test_selected_small_model_is_used(tmp_path):
    root = tmp_path / ".yat"
    root.mkdir()
    (root / "model.json").write_text(json.dumps({"model": "small.en"}))
    assert Paths.for_home(tmp_path).model.name == "ggml-small.en.bin"


def test_invalid_selection_fails_closed(tmp_path):
    root = tmp_path / ".yat"
    root.mkdir()
    (root / "model.json").write_text(json.dumps({"model": "../../other"}))
    with pytest.raises(ValueError):
        Paths.for_home(tmp_path)


def test_small_model_uses_its_own_trusted_hash(tmp_path, monkeypatch):
    import hashlib

    from transcriber import __main__ as runtime

    root = tmp_path / ".yat"
    (root / "bin").mkdir(parents=True)
    (root / "models").mkdir()
    (root / "model.json").write_text('{"model":"small.en"}')
    paths = Paths.for_home(tmp_path)

    def digest(data):
        return hashlib.sha256(data).hexdigest()

    paths.model.write_bytes(b"small")
    paths.vad_model.write_bytes(b"vad")
    paths.cli.write_bytes(b"cli")
    monkeypatch.setattr(runtime, "MODEL_SHA256", digest(b"base"))
    monkeypatch.setattr(runtime, "SMALL_MODEL_SHA256", digest(b"small"))
    monkeypatch.setattr(runtime, "VAD_SHA256", digest(b"vad"))
    (paths.cli.parent / "manifest.json").write_text(
        json.dumps(
            {
                "version": "v1.9.5",
                "source_commit": runtime.SOURCE_COMMIT,
                "model_sha256": digest(b"base"),
                "vad_sha256": digest(b"vad"),
                "cli_sha256": digest(b"cli"),
                "dll_sha256": {},
            }
        )
    )
    assert runtime.check_assets(paths)
    paths.model.write_bytes(b"tampered")
    assert not runtime.check_assets(paths)


def test_model_cli_select_and_list(tmp_path, monkeypatch):
    from typer.testing import CliRunner

    from transcriber.cli import app

    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    runner = CliRunner()
    result = runner.invoke(app, ["model", "select", "small.en"])
    assert result.exit_code == 0
    assert Paths.for_home(tmp_path).model.name == "ggml-small.en.bin"
    result = runner.invoke(app, ["model", "list"])
    assert result.exit_code == 0
    assert "small.en" in result.output
    assert runner.invoke(app, ["model", "select", "../other"]).exit_code != 0


def test_doctor_handles_invalid_model_settings(tmp_path, monkeypatch):
    from transcriber import doctor

    root = tmp_path / ".yat"
    root.mkdir()
    (root / "model.json").write_text("{broken")
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    monkeypatch.setattr(doctor, "check_format", lambda device: None)
    monkeypatch.setattr(doctor, "resolve_device", lambda: None)
    monkeypatch.setattr(doctor, "check_shortcut", lambda: (True, "ok"))
    assert next(item for item in doctor.run_checks() if item[0] == "assets")[1] is False
