# Offline dictation verification

The MVP is **not verified usable**. Execute the setup script first on Windows 11
with CMake, MSVC, a microphone, Windows Terminal/OpenCode, and Obsidian.
Do not record audio, transcripts, window titles, or clipboard content in results.

## Gates

- [ ] **Not verified:** build whisper.cpp v1.9.5 with MSVC, verify model and binary hashes, and launch with the resulting assets.
- [ ] **Not verified:** dictate into OpenCode in Windows Terminal and verify caret insertion.
- [ ] **Not verified:** dictate into Obsidian and verify caret insertion.
- [ ] **Not verified:** confirm UI Automation element identity remains stable in both applications.
- [ ] **Not verified:** confirm no submission with Terminal multiline warnings enabled and disabled.
- [ ] **Not verified:** switch to another field in the same app, then to another app; neither case auto-pastes.
- [ ] **Not verified:** indicator never takes foreground while recording, processing, or showing a fallback in either target app.
- [ ] **Not verified:** hotkey conflict, microphone failure, missing or invalid model, and clipboard or paste failures show an error or copyable transcript.
- [ ] **Not verified:** a 60-second recording stops exactly once; shortcuts during transcription do nothing.
- [ ] **Not verified:** silent and realistically noisy no-speech recordings do not produce pasted words. The low-level PCM noise gate is not a voice activity detector.
- [ ] **Not verified:** disconnect networking after setup, restart, and dictate successfully.
- [ ] **Not verified:** orphan audio is removed and log rotation preserves privacy.

## Observations in this development environment

- Win+Alt+S registration and unregistration: passed as an isolated Windows API check.
- A Tk error overlay was visible without changing the foreground window.
- Setup was attempted but CMake was unavailable. The model and CLI were not installed or verified.

## Latency observations

Record cold and warm results separately, without transcript content. Use
`python scripts/summarize-logs.py <path-to-app.jsonl>` for stage summaries.

| Recording | Cold stop-to-insertion | Warm stop-to-insertion | Model load / inference |
|---|---|---|---|
| 5 seconds | Not verified | Not verified | Not verified |
| 15 seconds | Not verified | Not verified | Not verified |
| 45 seconds | Not verified | Not verified | Not verified |
