# Contributing

Thanks for helping improve Yet Another Transcriber. Bug reports, documentation
fixes, and pull requests are welcome.

## Set up a development environment

Use Windows 11 x64 with Git, CMake, the MSVC x64 C++ tools, a Windows SDK, and
uv. See the [README](README.md#requirements) for links and setup details.

1. Clone the repository.
2. Open PowerShell in its root directory.
3. Run `uv sync --python 3.13`.
4. If you need live dictation, run
   `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/setup-local.ps1`.

The automated tests use fakes for the microphone and recognizer. Most changes
do not need a model download or a working microphone.
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
the indicator, record the manual tests. Record cases that you did not test in
the pull request.

Before changing visual UI, consult the [design references](docs/design/README.md).
For indicator changes, compare the rendered Windows states against the
[worked example](docs/design/indicator.md) as well as running automated tests.

## Preserve the safety boundaries

- Keep recording and recognition local after setup. Do not add runtime model
  downloads, telemetry, or cloud transcription.
- Do not log or commit audio, transcripts, clipboard contents, text-field
  contents, or window titles. Do not include them in issue reports.
- Keep temporary audio under `%USERPROFILE%\.yat\tmp`. Remove it after use.
- Before automatic paste, make sure the original window and focused element
  both match. If either identity is uncertain, do not paste automatically.
- Keep Windows Terminal text on one line. Send only Ctrl+V. Never send Enter.
- Keep the VAD model pinned. Check the model before use. Do not transcribe
  without VAD.

## Send a change

Describe the problem, the change, and how you tested it in your pull request.
Mention platform limits and tests you could not run. Keep unrelated changes
separate, and do not commit local models, binaries, WAV files, or private logs.

By submitting a contribution, you agree to license it under the project's
[MIT License](LICENSE).
