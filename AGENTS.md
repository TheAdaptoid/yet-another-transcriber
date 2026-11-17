# Repository guidance

## Development

- Windows 11 x64 and Python 3.13 are the supported environment. Set up with `uv sync --python 3.13`.
- Run these commands from the repository root:
  ```powershell
  uv sync --locked
  uv run ruff check .
  uv run ruff format --check .
  uv run ty check
  uv run pytest -q
  ```
  `ty` excludes tests.
- Run a focused test with `uv run pytest -q tests/test_session.py::test_missing_or_changed_focus_is_copyable_without_paste`. Most tests do not need downloaded models or a microphone. Tests use fake microphones and recognizers. Some tests use Windows APIs or Tk.
- Live dictation needs Git, CMake, MSVC, the Windows SDK, and network access. Run `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/setup-local.ps1`. It refuses to overwrite an existing manifest. Use `scripts/setup-vad.ps1` for an existing installation that needs VAD. Stop an existing instance before testing lifecycle changes.

## Wiring and safety

- `yat` starts at `transcriber.cli:app`. The `start` command launches a detached `transcriber.service` child. The child runs `transcriber.__main__.Runtime`. The runtime connects the Tk UI queue and worker to `SessionController`. Keep controller state and UI updates on the UI thread.
- Assets, temporary WAVs, and logs live under `%USERPROFILE%\.yat`, outside the checkout. Setup pins whisper.cpp and both models. Setup checks their hashes. The runtime checks the manifest and hashes. When pins change, keep setup and runtime validation consistent.
- Follow the safety boundaries in `CONTRIBUTING.md`. Keep recognition local. Do not log sensitive content. Remove temporary audio. Paste automatically only when both the original window and focused element match. Keep Windows Terminal text on one line. Send only Ctrl+V. Never send Enter. Do not bypass VAD.
- Audio, focus, insertion, and indicator changes need manual Windows tests as well as automated tests. Record manual tests and cases not tested in the PR.
