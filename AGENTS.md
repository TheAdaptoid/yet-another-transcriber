# Repository guidance

## Development

- Windows 11 x64 and Python 3.13 are the supported environment. Set up with `uv sync --python 3.13`.
- Run the checks from the repository root: `uv sync --locked`, `uv run ruff check .`, `uv run ruff format --check .`, `uv run ty check`, `uv run pytest -q`. `ty` excludes tests.
- Run a focused test with `uv run pytest -q tests/test_session.py::test_missing_or_changed_focus_is_copyable_without_paste`. Tests fake the microphone and recognizer, so most do not need downloaded models or a microphone; some exercise Windows APIs or Tk.
- Live dictation requires `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/setup-local.ps1` and its Git, CMake, MSVC, SDK, and network prerequisites. It refuses to overwrite an existing manifest; use `scripts/setup-vad.ps1` for an existing installation needing VAD. Stop an existing instance before testing lifecycle changes.

## Wiring and safety

- `yat` enters through `transcriber.cli:app`; `start` launches the detached `transcriber.service` child, which runs `transcriber.__main__.Runtime`. The runtime wires the Tk UI queue and worker to `SessionController`; keep controller state and UI updates on the UI thread.
- Assets, temporary WAVs, and logs live under `%USERPROFILE%\.yat`, outside the checkout. Setup pins and verifies whisper.cpp and both models; runtime validates the manifest and hashes. Keep setup and runtime verification consistent when changing pins.
- Follow the safety boundaries in `CONTRIBUTING.md`: local-only recognition, no sensitive content in logs, clean up temporary audio, and fail closed unless both window and focused element match. Terminal insertion must remain single-line Ctrl+V only, never Enter; do not silently bypass VAD.
- Audio, focus, insertion, and indicator changes need manual Windows checks in addition to automated tests; report unverified cases in the PR.
