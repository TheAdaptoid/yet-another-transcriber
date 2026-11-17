# Offline Windows dictation — MVP design

## Intent

A personal Windows 11 tool that saves typing in OpenCode (Windows Terminal) and Obsidian. Press Win+Alt+S to start recording; press it again to stop. Transcribe English speech entirely on the PC, then insert text at the current cursor without pressing Enter or submitting anything.

## Goals and boundaries

- Work without a network after installation and model acquisition; never send recorded audio or text to a service. Once installed, first launch must not download a model or depend on network access.
- Produce usable speech-to-text with ordinary punctuation. No rewriting layer; occasional omitted filler words are acceptable.
- Give clear recording/processing feedback and a recoverable result if insertion fails.
- Test the shortcut on the actual Windows 11 PC: Microsoft's published shortcut list does not assign Win+Alt+S, but installed apps may. Report a registration conflict rather than silently using another shortcut.
- Prioritize OpenCode in Windows Terminal and Obsidian; do not promise every Windows app, elevated window, password field, or remote desktop.
- No meetings, audio-file import, history, syncing, team features, custom dictionary, mobile app, or live transcription in the MVP.

## Approaches

1. **Chosen: CPU-first `whisper.cpp`.** Simplest local engine path on the Ryzen 5800X; measure real dictation latency before adding acceleration.
2. **Alternative: Radeon/Vulkan `whisper.cpp` from day one.** Potentially quicker inference, with more driver/build/packaging work before validating the dictation workflow.
3. **Alternative: Python `faster-whisper` with AMD ROCm.** Convenient integration, but more complicated Windows GPU dependencies for a personal MVP.

## Decided implementation

- Run as a Python 3.13 x64 background process on Windows 11. Manage Python and dependencies with `uv` (`pyproject.toml` and committed `uv.lock`). Start the MVP directly with `.venv\Scripts\python.exe -m transcriber` from the repository; do not build a distributable package yet. Keep the code organized so a later release can package it. No packaged installer, startup-at-login, or cloud service.
- Keep application-specific files under `~\.yat` (`%USERPROFILE%\.yat`): `models\` for model files, `bin\` for the local `whisper-cli`, `tmp\` for temporary audio, and `logs\` for diagnostics. Keep the source tree, `pyproject.toml`, `uv.lock`, and the `uv` virtual environment in the repository. Do not store app data in `%LOCALAPPDATA%`.
- Use Win32 `RegisterHotKey` via `ctypes` for Win+Alt+S. Use `sounddevice` to record the default microphone as mono 16 kHz PCM. If hotkey registration or microphone opening fails, show an error rather than silently switching defaults.
- Pin `whisper.cpp` to release v1.9.5, build its CPU-only `whisper-cli` for Windows, and use `ggml-base.en.bin` with explicit English transcription (not translation). Run the CLI once per completed utterance; do not add a persistent server or model preloading in the MVP. Setup may download source/model once, but installed dictation has no network calls. Keep the model, CLI version, and downloaded-artifact hashes recorded for reproducible setup.
- Record up to **60 seconds** per utterance. The second shortcut stops capture; at 60 seconds the app stops automatically and begins transcription. While transcribing or inserting, additional shortcut presses are ignored. No streaming, queued sessions, or simultaneous recordings.
- Snapshot the original foreground top-level window (`GetForegroundWindow`) and focused UI Automation element identity at recording start; use the same checks immediately before insertion. Use `comtypes` to access UI Automation. Require the window and element to still match; if UI Automation cannot identify a stable element in a target app, do not silently weaken the check—treat that target as a failed verification gate and revisit the design. The indicator must not become the foreground window.
- Capture audio in memory. Write only the temporary 16 kHz PCM WAV needed by `whisper-cli` to `~\.yat\tmp`, and remove it after success or failure. Clean up any orphaned temporary audio on the next launch. No transcript/audio history and no transcript/audio content in logs.
- After a successful transcription and focus check, put the transcript on the Windows Unicode-text clipboard and send **only Ctrl+V** through Win32 `SendInput` to the original target; never synthesize Enter. **Leave the transcript on the clipboard** afterward, including if paste appears to fail, so it can be pasted manually. The previous clipboard contents are not restored. If focus is uncertain or insertion fails, do not retry automatically; show a copyable result.
- For Windows Terminal/OpenCode, collapse CR/LF, tabs, and other controls to spaces before clipboard paste so the result is a single editable line. Do not rely on Terminal's multiline warning or bracketed-paste mode for safety; verify in the actual OpenCode prompt that no submission occurs. For Obsidian, paste the recognizer's text without terminal-specific line collapsing; do not invent paragraph breaks.
- Use `base.en` for the MVP; measure stop-to-insertion time with representative 5-, 15-, and 45-second dictations on the target PC. Record model-load and end-to-end timings. `small.en`, preloading, or Radeon acceleration are later changes only if measured latency or recognition quality makes them worthwhile.
- Use `ruff` for linting and formatting, `ty` for static type checks, and `pytest` for tests. Pin their versions with the other development dependencies in `uv.lock`. The plan must include unit tests for state transitions and text safety, plus manual integration tests in OpenCode and Obsidian.

## Mid-course correction: offline speech detection

The first real-PC silence test inserted `[BLANK_AUDIO]` into OpenCode.
Synthetic no-speech noise also produced hallucinated words.
The existing PCM peak gate and marker filter do not establish silence safety.

- Add a small, CPU-only voice activity detection (VAD) model to the offline recognition path.
- Pin the VAD model and its integrity hash during setup.
  Keep the model under `~\.yat\models`; do not download it at runtime.
- Require a positive speech detection before any transcript can be pasted.
  If detection finds no speech, return an empty result and do not paste.
- If the VAD model is missing, invalid, or fails, show an error and do not paste.
  Do not fall back to recognition without VAD.
- Keep the existing audio privacy, temporary file, focus, clipboard, and terminal safety rules.
  Do not log VAD input, transcript text, or third-party output.
- VAD is not a guarantee against hallucination.
  It can reject quiet speech or accept background sounds as speech.
  Measure false rejects, false detections, memory use, and latency on the target PC.
- Test empty capture, quiet-room noise, and background noise without speech.
  Test normal and quiet speech, including short utterances.
  Report any false detection or rejected speech as a failed verification gate.
- The VAD model and integration method remain to be selected from the lightweight options research.
  Do not call the MVP usable until the selection, implementation, and real-PC checks are complete.

## Local diagnostics

- Write detailed structured JSON-lines logs to `~\.yat\logs\app.jsonl`. Rotate at 5 MiB per file and keep five files total. Logs remain local.
- Give each dictation a session ID. Log state changes and stage durations with a monotonic clock: microphone open, recording, WAV write, CLI start, model load if the CLI exposes it, inference, focus check, clipboard write, paste, and total stop-to-insertion time. Log the model version, audio duration, output character count, target process name, and error category.
- Include exception traces and failure details that help diagnose performance and integration problems. Never log audio, transcript text, clipboard contents, text-field contents, or window titles. Sanitize third-party CLI output before logging it so a transcript cannot enter the logs.
- Define profiler-friendly log events and a simple way to summarize latency by stage. Check log rotation and privacy in tests. Do not add telemetry or network logging.

## UI and interaction

- Keep the app in the background: no main window or review step is needed for normal dictation.
- A compact, fixed screen-corner indicator appears while recording, changes to a processing state after the second shortcut press, then disappears when the text is inserted. It must never activate or take focus away from OpenCode or Obsidian. Do not show a live transcript.
- The second shortcut ends recording and starts processing. The app attempts
  insertion only when speech is detected and the safety checks pass. There is no
  dedicated cancel action in the MVP; unwanted text can be deleted in the target
  app.
- Use a small Tkinter corner overlay with Windows no-activate/tool-window styles for recording and processing. On success it closes after insertion. On microphone, model, hotkey, or insertion failure, show a plain-language error; when a transcript exists, leave it on the clipboard and show a dismissible fallback with the text/copy action. Do not pretend insertion succeeded.
- No animation, sound, setup screens, configuration UI, or extra visual polish. Keep feedback legible and unobtrusive.

## Verification gates, not product decisions

Before calling the MVP usable, run `uv sync`, `ruff`, `ty`, and `pytest`. Test hotkey registration on the actual PC; correct target identification and caret insertion in **both** Windows Terminal/OpenCode and Obsidian; no auto-submit with Terminal multiline warnings on and off; no focus theft by the overlay; clipboard behavior; microphone/model/focus/paste failures; 60-second cutoff; orphaned-audio cleanup; local log privacy and rotation; and operation with network disabled after setup. Measure latency; do not assert a speed target without target-machine evidence. If a verification gate fails, surface the failure and revise the design with the user rather than quietly relaxing the safety behavior. See [architecture diagram](../../architecture/offline-dictation-mvp.md).
