# Offline Windows Dictation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Dictate English locally on Windows 11 into terminal and editor applications with Win+Alt+S, without submitting terminal input.

**Architecture:** A Python background process owns a global hotkey, microphone capture, a non-activating corner indicator, and one dictation session at a time. Each utterance runs a pinned CPU `whisper-cli` against a temporary WAV; target verification precedes clipboard paste. Failures leave a copyable transcript when one exists. Structured local logs measure every stage without recording content.

**Tech Stack:** Python 3.13, `uv`, `sounddevice`, `numpy`, `comtypes`, Win32 APIs via `ctypes`, Tkinter, `whisper.cpp` v1.9.5 and `ggml-base.en.bin`, `ruff`, `ty`, `pytest`.

**Spec:** [Offline Windows dictation design](../specs/2026-11-15-offline-windows-dictation-design.md); [architecture and sequence diagrams](../../architecture/offline-dictation-mvp.md).

## Global Constraints

- Windows 11 x64 only; run `.venv\Scripts\python.exe -m transcriber` from the repository. Use `uv sync --python 3.13`; commit `uv.lock`. Do not build a distributable package yet.
- Keep app-specific storage under `%USERPROFILE%\.yat`: `models\`, `bin\`, `tmp\`, `logs\`. Never place app data in `%LOCALAPPDATA%`.
- Use Win+Alt+S, English-only `ggml-base.en.bin`, CPU-only `whisper-cli` v1.9.5, 16 kHz mono PCM, and a 60-second recording cap. Ignore additional hotkeys while processing or inserting.
- Keep audio and transcription offline after setup. No history, telemetry, rewriting, audio/text in logs, cloud calls, or runtime downloads.
- Capture original foreground window **and** UI Automation focused-element identity. Never auto-paste if either changes or cannot be verified; do not silently downgrade this condition.
- For Windows Terminal, normalize all line breaks, tabs, and controls to spaces. Only send Ctrl+V, never Enter; leave the result on the Unicode clipboard. Do not auto-retry uncertain paste.
- Use a non-activating Tkinter corner indicator. Give visible errors and a copyable transcript on insertion/focus failure.
- Use `ruff` for lint/format, `ty` for type checks, and `pytest` for tests. Verify a terminal and editor on the user's PC before calling the MVP usable.

## Review Focus

1. An empty/silent recording must not paste hallucinated words; Task 2 tests the no-speech result.
2. Focus changes to another field in the same app must prevent auto-paste; Task 3 tests element identity as well as window identity.
3. CR, LF, tabs, and control characters must not submit terminal input; Task 3 tests sanitization and only-Ctrl+V input.
4. A late recording callback or shortcut during transcription must not start a second session; Task 4 tests the 60-second cutoff and busy state.
5. A third-party error or CLI output containing dictated words must not reach logs; Task 1 tests allowlisted metadata, and Task 2 tests CLI output handling.

## File Map

- `pyproject.toml`, `.python-version`, `uv.lock`: uv project and checks. Preserve the existing `.gitignore`; it already ignores `.venv/`, caches, and `.superpowers/` without ignoring `uv.lock` or docs.
- `transcriber/config.py`: paths, asset names, and fixed MVP limits; `transcriber/diagnostics.py`: allowlisted JSON-lines events, rotation, stage timings.
- `transcriber/audio.py`: in-memory capture and one temporary WAV; `transcriber/recognizer.py`: CPU CLI invocation and result parsing; `scripts/setup-local.ps1`: pinned assets and build; `scripts/summarize-logs.py`: latency report.
- `transcriber/targets.py`: window/UIA snapshots and app classification; `transcriber/insertion.py`: terminal-safe text, Unicode clipboard, and Ctrl+V.
- `transcriber/session.py`: pure state transitions and one-session coordinator with injectable ports.
- `transcriber/hotkey.py`: Win32 registration/message loop; `transcriber/indicator.py`: non-activating Tkinter overlay; `transcriber/__main__.py`: runtime wiring and startup checks.
- `tests/test_config_diagnostics.py`, `tests/test_audio_recognizer.py`, `tests/test_targets_insertion.py`, `tests/test_session.py`, `tests/test_runtime.py`: focused automated tests. `docs/verification.md`: actual-PC verification checklist and measurement template.

---

### Task 1: uv project, storage, and private diagnostics

**Files:**
- Create: `pyproject.toml`, `.python-version`, `transcriber/__init__.py`, `transcriber/config.py`, `transcriber/diagnostics.py`, `tests/test_config_diagnostics.py`
- Generated and commit: `uv.lock`

**Interfaces:**
- Produces: `Paths.for_home(home: Path) -> Paths` with `.root`, `.model`, `.cli`, `.tmp`, `.log`; constants `MAX_SECONDS = 60`, `SAMPLE_RATE = 16000`, `MODEL_NAME = "ggml-base.en.bin"`.
- Produces: `make_logger(path: Path) -> logging.Logger`, `log_event(logger: logging.Logger, session_id: str, event: str, **metrics: int | float | str) -> None`; only named numeric/timing fields and `model`, `process_name`, `error_category` may be serialized. Reject unknown or content-bearing fields.

- [ ] **Step 1: Write failing tests** for `Paths.for_home(Path("C:/Users/Test"))` resolving to `C:/Users/Test/.yat/{models,bin,tmp,logs}`, a 5 MiB/five-file rotating logger, a valid timing event, and rejection of `transcript`, `audio`, `clipboard`, `window_title`, and arbitrary exception text. Test that an exception containing dictated words does not enter a log file.
- [ ] **Step 2: Run** `uv run --no-project --with pytest --python 3.13 pytest tests/test_config_diagnostics.py -q`; expect failure because `transcriber.config` and `transcriber.diagnostics` do not exist.
- [ ] **Step 3: Add** `pyproject.toml` with `requires-python = ">=3.13,<3.14"`, non-package uv project, runtime dependencies `sounddevice`, `numpy`, `comtypes`, and dev dependencies `pytest`, `ruff`, `ty`. Set `.python-version` to `3.13`; implement the two interfaces. Preserve the existing `.gitignore`, which already excludes `.venv/`, test/lint caches, bytecode, and `.superpowers/` but not docs or `uv.lock`. Create and lock the environment with `uv sync --python 3.13`.
- [ ] **Step 4: Run** `.\.venv\Scripts\python.exe -m pytest tests/test_config_diagnostics.py -q`; expect PASS. Run `uv sync --locked`; expect no lock changes.
- [ ] **Step 5: Commit** only Task 1 files with message `chore: establish uv project and private diagnostics`.

### Task 2: Local asset setup, audio, and CPU recognition

**Files:**
- Create: `scripts/setup-local.ps1`, `transcriber/audio.py`, `transcriber/recognizer.py`, `tests/test_audio_recognizer.py`
- Modify: `transcriber/config.py` only if Task 2 assets require it; preserve the existing `.gitignore`

**Interfaces:**
- Consumes: `Paths`, `MAX_SECONDS`, `SAMPLE_RATE`, `MODEL_NAME`, `log_event`.
- Produces: `Recorder.start() -> None`, `Recorder.stop() -> np.ndarray`, `Recorder.close() -> None` (signed 16-bit mono samples; callback-safe); `write_temp_wav(samples: np.ndarray, directory: Path) -> Path`, `cleanup_temp_wavs(directory: Path) -> None` (own `yat-*.wav` only).
- Produces: `Recognizer.transcribe(samples: np.ndarray, paths: Paths, session_id: str) -> str`. Spawn `%USERPROFILE%\.yat\bin\whisper-cli.exe` with `-m`, `-f`, `-l en`, `-ng`, `-np`, `-nt`; return transcript from stdout, not stderr. Always remove the WAV.

- [ ] **Step 1: Write failing tests** with fake input stream and subprocess: recording uses 16 kHz mono signed PCM; stop returns copied samples; a late callback cannot append after stop; WAV is 16 kHz/mono/16-bit; cleanup removes only owned stale WAVs; an empty/silent capture returns an empty transcript without launching CLI; CLI arguments pin English/CPU/model; missing or failing CLI raises a categorized error; output or error text containing speech never enters logs; temp WAV disappears on all exits. Assert separate sanitized timing events for WAV write, CLI startup, and inference.
- [ ] **Step 2: Run** `.\.venv\Scripts\python.exe -m pytest tests/test_audio_recognizer.py -q`; expect FAIL for missing `audio`/`recognizer`.
- [ ] **Step 3: Implement** `Recorder`, WAV writer, cleanup, and `Recognizer` with a bounded subprocess timeout and no network path. Add `scripts/setup-local.ps1`: checkout `whisper.cpp` tag `v1.9.5` at commit `d1be6fde11ac6e0407606b4e42fe72d34add8037`, build CPU `whisper-cli` with CMake/MSVC, copy EXE and required DLLs to `~\.yat\bin`, download the model to `~\.yat\models`, and verify its SHA-256 is `a03779c86df3323075f5e796cb2ce5029f00ec8869eee3fdfb897afe36c6d002` (the [official model LFS pointer](https://huggingface.co/ggerganov/whisper.cpp/raw/main/ggml-base.en.bin)). Record built binary hash/version in a local manifest; reject missing or mismatched assets at runtime. Only setup accesses the network.
- [ ] **Step 4: Run** `.\.venv\Scripts\python.exe -m pytest tests/test_audio_recognizer.py -q`; expect PASS. Run `scripts/setup-local.ps1` on a Windows build host and verify model hash, CLI version, and binary presence; record any machine-only blocker rather than assuming success.
- [ ] **Step 5: Commit** only Task 2 files with message `feat: add local capture and CPU speech recognition`.

### Task 3: Verified target and safe text insertion

**Files:**
- Create: `transcriber/targets.py`, `transcriber/insertion.py`, `tests/test_targets_insertion.py`

**Interfaces:**
- Consumes: `log_event`.
- Historical design: capture a foreground window and UI Automation focused-element runtime ID with an application allowlist. The current implementation uses neutral target identity and fails closed if identity is unavailable.
- Historical design: sanitize terminal text, then place Unicode text on the clipboard and send Ctrl+V without Enter or clipboard restoration. The current implementation sanitizes every automatic paste.

- [ ] **Step 1: Write failing tests** for a changed HWND, a changed runtime ID in the same HWND, and missing UIA identity; each must deny insertion. Test ANSI removal and whitespace collapse. With fake Win32 calls, assert clipboard receives Unicode text, the only synthesized keystrokes are Ctrl down/V down/V up/Ctrl up, and the clipboard retains the transcript even on failure.
- [ ] **Step 2: Run** `.\.venv\Scripts\python.exe -m pytest tests/test_targets_insertion.py -q`; expect FAIL for missing `targets`/`insertion`.
- [ ] **Step 3: Implement** the snapshot, UIA comparison, app classification, safe text, clipboard write, and guarded `SendInput`. Do not use window title or textbox contents for identification. Check foreground/focus again immediately before `SendInput`; return false on uncertainty and never retry.
- [ ] **Step 4: Run** `.\.venv\Scripts\python.exe -m pytest tests/test_targets_insertion.py -q`; expect PASS. If UIA cannot expose a stable focused element in either named app, mark its integration gate blocked for user review; do not weaken the check.
- [ ] **Step 5: Commit** only Task 3 files with message `feat: verify focus before safe paste`.

### Task 4: One-session controller and timing events

**Files:**
- Create: `transcriber/session.py`, `tests/test_session.py`

**Interfaces:**
- Consumes: `Recorder`, `Recognizer`, `TargetSnapshot`, `capture_target`, `still_focused`, `safe_text`, `paste_text`, `Paths`, `log_event`.
- Produces: `SessionController.on_hotkey() -> None`, `SessionController.on_limit() -> None`, `SessionController.on_transcription_done(text: str | None, error: str | None) -> None`; injectable clock/worker and a `show_state(state: Literal["idle","recording","transcribing","error","copy"], text: str | None) -> None` callback. UI/main thread owns state; a worker does WAV/CLI work and sends completion to the UI queue.

- [ ] **Step 1: Write failing tests** with fake clock, recorder, recognizer, focus, clipboard, and UI: idle→recording→transcribing→idle; second press stops; 60-second timer stops once; busy hotkeys do nothing; late microphone data cannot enter the next session; missing/failing focus shows copy without paste; silence closes without insertion; inference failure shows error. Assert one session ID and stage timing events for mic open, recording, focus check, clipboard write, paste, and total stop-to-insertion; assert no dictated words in any event.
- [ ] **Step 2: Run** `.\.venv\Scripts\python.exe -m pytest tests/test_session.py -q`; expect FAIL for missing `session`.
- [ ] **Step 3: Implement** the controller, one-way transitions, timeout, UI callback, guarded paste, and allowed stage metrics. Keep UI operations on Tk's main thread. On fail/uncertain insertion leave a copyable transcript, never auto-retry.
- [ ] **Step 4: Run** `.\.venv\Scripts\python.exe -m pytest tests/test_session.py -q`; expect PASS.
- [ ] **Step 5: Commit** only Task 4 files with message `feat: coordinate one offline dictation session`.

### Task 5: Windows hotkey, overlay, and executable entry point

**Files:**
- Create: `transcriber/hotkey.py`, `transcriber/indicator.py`, `transcriber/__main__.py`, `tests/test_runtime.py`

**Interfaces:**
- Consumes: Task 4 `SessionController` and `show_state`; Task 1 `Paths`, `make_logger`.
- Produces: `HotkeyListener.start(on_press: Callable[[], None]) -> None`, `HotkeyListener.stop() -> None`; `Indicator.show(state: str, text: str | None = None) -> None`, `Indicator.close() -> None`; `main() -> int`.

- [ ] **Step 1: Write failing tests** with fake Win32/Tk adapters: `RegisterHotKey` receives `MOD_WIN | MOD_ALT` and virtual key `S`; registration conflict produces a visible error; listener unregisters on shutdown; overlay updates recording→transcribing→copy/error without becoming foreground; main checks local assets, clears orphan WAVs, initializes logs, and wires hotkey events to the controller. Test shutdown while recording and while processing.
- [ ] **Step 2: Run** `.\.venv\Scripts\python.exe -m pytest tests/test_runtime.py -q`; expect FAIL for missing runtime modules.
- [ ] **Step 3: Implement** a Win32 hotkey message loop on a worker thread that enqueues presses, and a Tk main-loop queue that owns the controller and indicator. Configure the Tk overlay as topmost, `WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW`; keep normal state non-activating. Show a small copy/error fallback without silently discarding text. Exit cleanly on Ctrl+C or window close; do not add tray, installer, or settings UI.
- [ ] **Step 4: Run** `.\.venv\Scripts\python.exe -m pytest tests/test_runtime.py -q`; expect PASS. Start `.venv\Scripts\python.exe -m transcriber` on Windows and verify registration/error visibility without claiming target-app integration yet.
- [ ] **Step 5: Commit** only Task 5 files with message `feat: wire Windows shortcut and corner status`.

### Task 6: Profiling and actual-PC verification

**Files:**
- Create: `scripts/summarize-logs.py`, `tests/test_log_summary.py`, `docs/verification.md`
- Modify: existing files only to fix failures found during verification; keep changes within the owning task's interface

**Interfaces:**
- Consumes: structured log events from Task 1.
- Produces: `summarize(path: Path) -> dict[str, object]` with per-stage count, median, and p95 for numeric durations; missing stages stay missing, not zero. A CLI prints the summary without printing transcript or paths to private audio.

- [ ] **Step 1: Write failing tests** for summaries of repeated sessions, missing stages, malformed lines, and log events with unexpected text fields. Assert count/median/p95 and no content in output. Draft `docs/verification.md` with a checklist for real terminal and editor use, terminal multiline warning on/off, focus switched to another field/app, indicator focus, conflict/mic/model/paste failure, 60-second cutoff, offline launch after setup, log rotation/privacy, and 5/15/45-second warm/cold latency observations.
- [ ] **Step 2: Run** `.\.venv\Scripts\python.exe -m pytest tests/test_log_summary.py -q`; expect FAIL for missing `summarize`.
- [ ] **Step 3: Implement** the numeric summary CLI. Complete the actual-PC checklist when that machine is available; if not, mark each untested gate explicitly **not verified**, not passed. Never weaken focus/terminal safeguards to make a checklist pass.
- [ ] **Step 4: Run** `uv sync --locked`, `.\.venv\Scripts\ruff.exe check .`, `.\.venv\Scripts\ruff.exe format --check .`, `.\.venv\Scripts\ty.exe check`, `.\.venv\Scripts\python.exe -m pytest -q`, and `.\.venv\Scripts\python.exe scripts/summarize-logs.py` against sample logs. Expect all checks green and no private content in output. Record actual manual-test and latency results separately; do not call the MVP usable if either target app or offline runtime remains unverified.
- [ ] **Step 5: Commit** only Task 6 files and any verified fixes with message `test: verify offline dictation and profile stages`.

## Execution notes

- The repo currently has only the spec and architecture documents; preserve existing `.superpowers/` user files and do not add generated WAVs, models, or binaries to git.
- Install/setup and actual target-app checks require Windows tools and access to the user's microphone and apps. Automated tests must use fakes so they can run without those devices.
- If a real-PC gate exposes an impossible UIA or Terminal behavior, stop and request a design revision rather than pretending a unit test proves safe insertion.
