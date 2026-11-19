# Verified speech model selection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Support verified selection of base.en and small.en.

**Architecture:** Persist an allowlisted model selection, defaulting to base.en.
Resolve it once at startup and verify the chosen model against its trusted hash.
Provide a separate verified installation script and CLI management commands.

**Tech Stack:** Python 3.13, PowerShell, pytest, whisper.cpp.

**Spec:** docs/superpowers/specs/2026-11-18-model-selection-design.md

## Global Constraints
- Keep dictation local, retain VAD and existing paste safety.
- Preserve existing base.en installations; never download during runtime.
- Reject invalid selection or model assets; selection changes require restart.

## Review Focus
- Corrupt or unknown selection must not silently select an untrusted file.
- A missing or corrupt model must not start recognition.
- Existing manifest and installation must continue to work unchanged.
- Failed downloads must not overwrite a valid model.
- Diagnostics must report the selected model accurately.

### Task 1: Selection and verification

**Files:** `transcriber/config.py`, `transcriber/__main__.py`,
`transcriber/diagnostics.py`, `transcriber/session.py`, tests.

**Interfaces:** resolve persisted model selection into `Paths.for_home`;
map exact names to trusted filenames and hashes.

- [ ] Write tests for default, persisted and invalid selection; chosen model hash
  validation and preservation of the existing manifest.
- [ ] Run focused tests and confirm expected failures.
- [ ] Implement selection resolution and fail-closed validation.
- [ ] Run focused tests and confirm pass.

### Task 2: Management and setup

**Files:** `transcriber/cli.py`, model selection module, setup script, tests, README.

**Interfaces:** `yat model list` and `yat model select {base.en|small.en}`;
`scripts/setup-small-model.ps1` verifies before installing.

- [ ] Test CLI selection, invalid input, corruption and atomic settings writes.
- [ ] Run focused tests and confirm expected failures.
- [ ] Implement CLI, setup and instructions.
- [ ] Run focused tests and confirm pass.

### Task 3: Verification

- [ ] Run `uv sync --locked`, `uv run ruff check .`,
  `uv run ruff format --check .`, `uv run ty check`, and `uv run pytest -q`.
- [ ] Review changes and record unperformed live Windows tests.
- [ ] Update issue and create PR.
