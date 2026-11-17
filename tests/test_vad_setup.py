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
