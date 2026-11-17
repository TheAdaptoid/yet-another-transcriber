# Microphone Selection Implementation Plan

**Goal:** Allow users to select a microphone and validate the recording format without capturing audio.

**Architecture:** Store a name and host API identity under the user profile. Resolve it against the current inventory whenever recording starts and whenever doctor runs; reject missing or ambiguous identities. Keep the default device when no selection exists.

**Tech Stack:** Python 3.13, sounddevice, Typer, pytest.

**Spec:** GitHub issue #9 and its investigation comment.

## Global Constraints

- Recording stays local; doctor never opens a stream.
- Use 16000 Hz, mono, int16; do not silently substitute devices.
- Preserve existing diagnostics privacy and report manual tests honestly.

## Review Focus

- Device reordering: test identity resolution after index changes.
- Missing and duplicate identities: test failure and reselection guidance.
- Invalid settings and I/O errors: test they do not restore defaults silently.
- Unsupported format: test doctor reports failure without recording.
- Service already running: test selection is read at every stream start.

## Tasks

- [ ] Add failing tests for settings, device enumeration and identity resolution; implement and rerun.
- [ ] Add failing tests for recorder and doctor using the same resolution and format; implement and rerun.
- [ ] Add failing CLI and session error tests; implement list/select/clear and safe errors; document use and identity limits.
- [ ] Run locked setup, lint, formatting, typing and full tests; record manual test limitations and create PR.
