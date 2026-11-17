# Offline dictation verification

The MVP is **not verified usable**. Execute the setup script first on Windows 11
with CMake, MSVC, a microphone, Windows Terminal/OpenCode, and Obsidian.
Do not record audio, transcripts, window titles, or clipboard content in results.

## Gates

- [x] **Verified:** build the pinned whisper.cpp v1.9.5 source with MSVC,
  verify model and binary hashes, and launch with the resulting assets.
- [x] **Verified:** dictate into OpenCode in Windows Terminal and verify
  editable insertion without submitting the prompt.
- [x] **Verified:** dictate into Obsidian and verify caret insertion.
- [x] **Verified:** UI Automation identified the focused elements sufficiently
  for successful insertion in both applications during these checks.
- [ ] **Not verified:** confirm no submission with Terminal multiline warnings enabled and disabled.
- [x] **Verified:** switching from an Obsidian note to the search field
  produced the fallback without changing the search field.
- [x] **Verified:** switching from OpenCode to an editable Obsidian search
  field produced the fallback without changing the search field.
- [ ] **Not verified:** indicator never takes foreground while recording, processing, or showing a fallback in either target app.
- [ ] **Not verified:** hotkey conflict, microphone failure, missing or invalid model, and clipboard or paste failures show an error or copyable transcript.
- [ ] **Not verified:** a 60-second recording stops exactly once; shortcuts during transcription do nothing.
- [ ] **Failed; retest required:** a quiet microphone recording produced a
  `[BLANK_AUDIO]` marker that was inserted into OpenCode. A separate synthetic
  noise test also produced hallucinated words. The low-level PCM noise gate is
  not a voice activity detector.
- [ ] **Not verified:** disconnect networking after setup, restart, and dictate successfully.
- [ ] **Not verified:** orphan audio is removed and log rotation preserves privacy.

## Observations in this development environment

- Win+Alt+S registration and unregistration: passed as an isolated Windows API check.
- A second registration of Win+Alt+S while the first was held failed as expected.
- A Tk error overlay was visible without changing the foreground window.
- The pinned source built with MSVC and CMake. The CLI reports
  `whisper.cpp version: 1.9.5-dev`; the checked-out v1.9.5 tag resolves to the
  pinned source commit.
- The model SHA-256 matched the pinned value, and startup asset validation
  passed for the model, executable, and installed DLLs.
- A direct CPU CLI invocation with synthetic silent audio exited successfully.
  A real runtime instance started with verified assets and shut down cleanly.
  Neither check verifies speech recognition quality or target-app insertion.
- The recognizer returned a nonempty result for whisper.cpp's bundled JFK
  sample in 1.3 seconds on this PC. This is not a user-microphone latency
  measurement or a target-app verification.
- In a scratch Obsidian note, the user reported that the indicator appeared and
  dictated text landed in the note. After focus moved to another application
  without a text field, the fallback appeared and the user copied and pasted
  its text into the scratch note.
- The user also reported that the fallback appeared when focus moved from the
  scratch Obsidian note to the search field in the same window, and the search
  field remained unchanged.
- In OpenCode running in Windows Terminal, the user reported that dictated text
  appeared in the editable input and was not submitted.
- When recording started in OpenCode and focus moved to Obsidian's search
  field, the user reported that the fallback appeared and the search field
  remained unchanged.
- Windows Terminal, Obsidian, OpenCode, and a default input device are present.
  OpenCode insertion, offline operation, and the remaining microphone and
  failure checks still require a controlled manual session.

## Latency observations

Record cold and warm results separately, without transcript content. Use
`python scripts/summarize-logs.py <path-to-app.jsonl>` for stage summaries.

| Recording | Cold stop-to-insertion | Warm stop-to-insertion | Model load / inference |
|---|---|---|---|
| 5 seconds | Not verified | Not verified | Not verified |
| 15 seconds | Not verified | Not verified | Not verified |
| 45 seconds | Not verified | Not verified | Not verified |
