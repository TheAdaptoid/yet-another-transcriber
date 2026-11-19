import os
import subprocess
from pathlib import Path


def test_bad_download_preserves_existing_model(tmp_path):
    root = tmp_path / ".yat"
    model = root / "models" / "ggml-small.en.bin"
    manifest = root / "bin" / "manifest.json"
    model.parent.mkdir(parents=True)
    manifest.parent.mkdir(parents=True)
    model.write_bytes(b"original")
    manifest.write_text("{}")
    script = Path(__file__).resolve().parents[1] / "scripts" / "setup-small-model.ps1"
    assert script.is_file()
    command = (
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
    assert model.read_bytes() == b"original"
    assert manifest.read_text() == "{}"
    assert not list(model.parent.glob("yat-small-*.download"))


def test_verified_download_installs_without_changing_manifest(tmp_path):
    root = tmp_path / ".yat"
    manifest = root / "bin" / "manifest.json"
    manifest.parent.mkdir(parents=True)
    manifest.write_text("{}")
    model = root / "models" / "ggml-small.en.bin"
    model.parent.mkdir()
    model.write_bytes(b"old model")
    script = Path(__file__).resolve().parents[1] / "scripts" / "setup-small-model.ps1"
    expected = "c6138d6d58ecc8322097e0f987c32f1be8bb0a18532a3f88f734d1bbf9c41e5d"
    command = (
        "Get-Command Get-FileHash,Invoke-WebRequest | Out-Null; "
        "function Invoke-WebRequest { param($Uri,$OutFile) "
        "[IO.File]::WriteAllBytes($OutFile,[byte[]](1,2,3)) }; "
        "function Get-FileHash { param($LiteralPath,$Algorithm) "
        f"[pscustomobject]@{{Hash='{expected}'}} }}; & '{script}'"
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
    assert manifest.read_text() == "{}"
