# Background Console Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** Launch the Windows background service without a visible console.

**Architecture:** Replace the detached-process flag with the experimentally verified no-window flag. Preserve the process group, standard handles, readiness handshake, and singleton shutdown protocol.

**Tech Stack:** Python 3.13, Windows subprocess flags, pytest.

**Spec:** `docs/superpowers/specs/2026-11-17-background-console-design.md`

## Global Constraints

- Preserve readiness reporting, singleton and shutdown behavior, and dictation safety boundaries.
- Do not change recognizer, audio, focus, insertion, or indicator behavior.
- Do not combine `CREATE_NO_WINDOW` with `DETACHED_PROCESS`.

## Review Focus

- Incorrect flags or handles: assert exact launch flags and all three redirected handles.
- Duplicate launch: preserve the existing duplicate-start test.
- Startup error: preserve the existing sanitized error test.
- Startup timeout: preserve the existing child cleanup test.
- Launcher exit and shutdown: preserve the existing real subprocess lifecycle tests.

### Task 1: Launch without a console

**Files:**
- Modify: `transcriber/service.py`
- Test: `tests/test_service.py`

**Interfaces:** Preserve `start_service() -> tuple[bool, str]` and its existing subprocess arguments except for the creation flags.

- [ ] Add `test_launcher_uses_no_window_and_redirected_handles`: capture `Popen` arguments using a fake ready child; assert the executable and child arguments, exact `CREATE_NO_WINDOW | CREATE_NEW_PROCESS_GROUP` flags, and `DEVNULL`, `PIPE`, `DEVNULL` for stdin, stdout, stderr.
- [ ] Run `uv run pytest -q tests/test_service.py::test_launcher_uses_no_window_and_redirected_handles`; expect failure on the flags.
- [ ] Replace `DETACHED_PROCESS` with `CREATE_NO_WINDOW` in `start_service`.
- [ ] Run `uv run pytest -q tests/test_service.py`; expect all tests to pass.
- [ ] Run `uv run ruff check .`, `uv run ruff format --check .`, `uv run ty check`, and `uv run pytest -q`; expect all checks to pass.
- [ ] Record the manual investigation results and untested cases in the PR; commit the changes.
