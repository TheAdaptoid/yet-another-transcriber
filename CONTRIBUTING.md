# Contributing

Thanks for helping improve Yet Another Transcriber. Bug reports, documentation
fixes, and pull requests are welcome.

## Set up a development environment

Use Windows 11 x64 with Git, CMake, the MSVC x64 C++ tools, a Windows SDK, and
uv. See the [README](README.md#requirements) for links and setup details.

1. Clone the repository and open PowerShell in its root directory.
2. Run `uv sync --python 3.13`.
3. If you need live dictation, run
   `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/setup-local.ps1`.

The automated tests use fakes for the microphone and recognizer. Most changes
do not require a model download or a working microphone.
For a locally installed command, follow the README's `uv tool install`
instructions. Use `yat doctor`, `yat start`, and `yat stop` to check and run it.
Stop an existing instance before testing lifecycle changes.

## Check your changes

Run these commands from the repository root:

```powershell
uv sync --locked
uv run ruff check .
uv run ruff format --check .
uv run ty check
uv run pytest -q
```

Run `uv run ruff format .` to format files when needed. Add tests
for behavior changes and bug fixes. For changes to audio, focus, insertion, or
the indicator, record any manual checks and any unverified cases in the pull
request. Use [the verification checklist](docs/verification.md) as a guide.

## Preserve the safety boundaries

- Keep recording and recognition local after setup. Do not add runtime model
  downloads, telemetry, or cloud transcription.
- Do not log or commit audio, transcripts, clipboard contents, text-field
  contents, or window titles. Do not include them in issue reports.
- Keep temporary audio under `%USERPROFILE%\.yat\tmp` and clean it up.
- Require both the original window and the focused element to match before
  automatic paste. Fail closed when either identity is uncertain.
- Keep Windows Terminal text on one line. Send only Ctrl+V; never send Enter.
- Keep the VAD model pinned and verified. Do not silently fall back to
  transcription without VAD.

## Send a change

Describe the problem, the change, and how you tested it in your pull request.
Mention platform limits and checks you could not run. Keep unrelated changes
separate, and do not commit local models, binaries, WAV files, or private logs.

By submitting a contribution, you agree to license it under the project's
[MIT License](LICENSE).
