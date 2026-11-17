import json
import os
import subprocess
from pathlib import Path


def test_invalid_download_preserves_model_and_manifest(tmp_path):
    root = tmp_path / ".yat"
    model = root / "models" / "ggml-silero-v5.1.2.bin"
    manifest = root / "bin" / "manifest.json"
    model.parent.mkdir(parents=True)
    manifest.parent.mkdir(parents=True)
    model.write_bytes(b"existing model")
    manifest.write_text('{"version":"v1.9.5"}')
    script = Path(__file__).resolve().parents[1] / "scripts" / "setup-vad.ps1"
    command = (
        "Get-Command Invoke-WebRequest | Out-Null; "
        "function Invoke-WebRequest { param($Uri,$OutFile) "
        "[IO.File]::WriteAllBytes($OutFile,[byte[]](1,2,3)) }; "
        f"& '{script}'"
    )
    env = os.environ.copy()
    env["USERPROFILE"] = str(tmp_path)
    result = subprocess.run(
        ["powershell", "-NoProfile", "-Command", command],
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode != 0
    assert model.read_bytes() == b"existing model"
    assert manifest.read_text() == '{"version":"v1.9.5"}'
    assert not list(model.parent.glob("yat-vad-*.download"))


def test_verified_download_updates_existing_manifest(tmp_path):
    root = tmp_path / ".yat"
    model = root / "models" / "ggml-silero-v5.1.2.bin"
    manifest = root / "bin" / "manifest.json"
    model.parent.mkdir(parents=True)
    manifest.parent.mkdir(parents=True)
    model.write_bytes(b"existing model")
    manifest.write_text('{"version":"v1.9.5"}')
    script = Path(__file__).resolve().parents[1] / "scripts" / "setup-vad.ps1"
    expected = "29940d98d42b91fbd05ce489f3ecf7c72f0a42f027e4875919a28fb4c04ea2cf"
    command = (
        "Get-Command Get-FileHash,Invoke-WebRequest | Out-Null; "
        "function Invoke-WebRequest { param($Uri,$OutFile) "
        "[IO.File]::WriteAllBytes($OutFile,[byte[]](1,2,3)) }; "
        "function Get-FileHash { param($LiteralPath,$Algorithm) "
        f"[pscustomobject]@{{Hash='{expected}'}} }}; "
        f"& '{script}'"
    )
    env = os.environ.copy()
    env["USERPROFILE"] = str(tmp_path)
    result = subprocess.run(
        ["powershell", "-NoProfile", "-Command", command],
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    assert model.read_bytes() == bytes([1, 2, 3])
    assert expected in manifest.read_text(encoding="utf-8-sig")
    assert '"v1.9.5"' in manifest.read_text(encoding="utf-8-sig")


def test_failed_manifest_commit_restores_existing_model(tmp_path):
    root = tmp_path / ".yat"
    model = root / "models" / "ggml-silero-v5.1.2.bin"
    manifest = root / "bin" / "manifest.json"
    model.parent.mkdir(parents=True)
    manifest.parent.mkdir(parents=True)
    model.write_bytes(b"original model")
    manifest.write_text('{"version":"v1.9.5"}')
    script = Path(__file__).resolve().parents[1] / "scripts" / "setup-vad.ps1"
    expected = "29940d98d42b91fbd05ce489f3ecf7c72f0a42f027e4875919a28fb4c04ea2cf"
    command = (
        "Get-Command Get-FileHash,Invoke-WebRequest | Out-Null; "
        "function Invoke-WebRequest { param($Uri,$OutFile) "
        "[IO.File]::WriteAllBytes($OutFile,[byte[]](1,2,3)) }; "
        "function Get-FileHash { param($LiteralPath,$Algorithm) "
        f"[pscustomobject]@{{Hash='{expected}'}} }}; & '{script}'"
    )
    env = os.environ.copy()
    env["USERPROFILE"] = str(tmp_path)
    with manifest.open("rb"):
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", command],
            env=env,
            capture_output=True,
            text=True,
            timeout=30,
        )
    assert result.returncode != 0
    assert model.read_bytes() == b"original model"
    assert json.loads(manifest.read_text()) == {"version": "v1.9.5"}


def test_full_setup_does_not_touch_existing_install(tmp_path):
    root = tmp_path / ".yat"
    manifest = root / "bin" / "manifest.json"
    manifest.parent.mkdir(parents=True)
    manifest.write_text('{"version":"v1.9.5","vad_sha256":"existing"}')
    sentinel = tmp_path / "build-started"
    script = Path(__file__).resolve().parents[1] / "scripts" / "setup-local.ps1"
    command = (
        f"function git {{ [IO.File]::WriteAllText('{sentinel}','called'); "
        "throw 'unexpected build' }; "
        "function cmake { throw 'unexpected build' }; "
        f"& '{script}'"
    )
    env = os.environ.copy()
    env["USERPROFILE"] = str(tmp_path)
    result = subprocess.run(
        ["powershell", "-NoProfile", "-Command", command],
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode != 0
    assert not sentinel.exists()
    assert json.loads(manifest.read_text())["vad_sha256"] == "existing"
