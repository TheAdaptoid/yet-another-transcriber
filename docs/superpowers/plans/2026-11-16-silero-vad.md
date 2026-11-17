# Offline Silero VAD Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prevent no-speech recordings from being pasted by requiring the pinned local Silero detector.

**Architecture:** The existing CPU `whisper-cli` performs VAD and transcription in one invocation. Setup installs and verifies a separate VAD model; startup and each transcription fail closed if it is missing or invalid. VAD is not a guarantee against false detections.

**Tech Stack:** Windows 11, Python 3.13, PowerShell, whisper.cpp v1.9.5, Silero GGML v5.1.2, pytest, ruff, ty.

**Spec:** `docs/superpowers/specs/2026-11-15-offline-windows-dictation-design.md`

## Global Constraints

- Keep runtime offline; setup alone may download.
- Use `%USERPROFILE%\.yat\models\ggml-silero-v5.1.2.bin`.
- SHA-256: `29940d98d42b91fbd05ce489f3ecf7c72f0a42f027e4875919a28fb4c04ea2cf`.
- Pass `--vad -vm <model-path>` to the CPU CLI; use upstream defaults pending real-PC measurements.
- Missing, corrupted, unreadable, or failed VAD must never fall back to unguarded transcription or insertion.
- Never log audio, transcript content, or CLI output. Preserve existing focus, terminal, and temporary-audio safety rules.

## Review Focus

1. The model disappears or changes after startup: each invocation rejects it before the CLI runs.
2. CLI VAD initialization or inference fails: surface a categorized error and never paste.
3. No speech returns an empty result: no clipboard write or synthesized keys.
4. Quiet speech, clipped boundaries, music, and background speech-like noise: real-PC outcomes are explicit gates, not implied by passing fakes.
5. Setup failure must not replace a verified VAD model or corrupt the existing manifest.

---

### Task 1: VAD asset and setup

**Files:** Modify `transcriber/config.py`, `transcriber/__main__.py`, `scripts/setup-local.ps1`, `tests/test_config_diagnostics.py`, `tests/test_runtime.py`; create `scripts/setup-vad.ps1`.

**Interfaces:** `Paths.vad_model: Path`; constants `VAD_MODEL_NAME` and `VAD_SHA256`. `check_assets(paths)` requires both the pinned VAD hash in the manifest and the matching file. `setup-vad.ps1` installs the VAD model and adds `vad_sha256` to the existing manifest without rebuilding the CLI. `setup-local.ps1` calls it after writing its manifest.

- [ ] **Step 1:** Test `Paths.vad_model`, valid startup with the VAD asset, and startup rejection for missing, changed, or mismatched VAD model and manifest.
- [ ] **Step 2:** Run `python -m pytest tests/test_config_diagnostics.py tests/test_runtime.py -q`; expect failure for the missing VAD interface.
- [ ] **Step 3:** Implement the interface. Download to a unique temporary file, verify SHA-256 before replacing the model, and atomically replace the manifest after parsing it. Preserve the existing manifest on errors. Only setup may access the network.
- [ ] **Step 4:** Run the task tests and full pytest suite; expect PASS. Run `scripts/setup-vad.ps1` on this PC and verify the model hash and `check_assets`. Do not rebuild existing assets.
- [ ] **Step 5:** Commit the task files as `feat: install and verify offline VAD model`.

### Task 2: Require VAD in recognition and verify

**Files:** Modify `transcriber/recognizer.py`, `tests/test_audio_recognizer.py`, `tests/test_session.py`, `docs/verification.md`.

**Interfaces:** `Recognizer.transcribe(samples, paths, session_id)` checks `paths.vad_model` against `VAD_SHA256` before spawning; it passes `--vad -vm <path>` every time. No-speech output is empty; CLI errors raise `RecognitionError` without exposing output.

- [ ] **Step 1:** Add failing tests for exact CLI flags, missing or changed VAD model after startup, VAD CLI failure, empty no-speech output, and no paste for an empty result. Keep the blank-marker regression and speech-output tests.
- [ ] **Step 2:** Run `python -m pytest tests/test_audio_recognizer.py tests/test_session.py -q`; expect FAIL for missing VAD checks.
- [ ] **Step 3:** Implement the per-invocation hash check and required CLI flags. Treat VAD errors as failures. Never retry without VAD.
- [ ] **Step 4:** Run `uv sync --locked`, `ruff check .`, `ruff format --check .`, `ty check`, and the full pytest suite. Test the actual CLI with synthetic silence/noise and bundled speech. Record results without logging speech or claiming measured RAM.
- [ ] **Step 5:** Restart the app only after the old unsafe process is stopped. Ask the user to repeat quiet/noisy and normal/quiet speech in scratch targets. Record results; keep unusable status until real-PC gates pass.
- [ ] **Step 6:** Commit task files as `feat: require offline speech detection`.
