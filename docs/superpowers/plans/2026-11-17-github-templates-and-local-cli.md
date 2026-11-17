# GitHub Templates and Local CLI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans or, if the user explicitly chooses delegation, superpowers:subagent-driven-development. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add lightweight GitHub templates and an installable `yat` command that manages background dictation.

**Architecture:** Package `transcriber` with a Typer CLI and Rich output. A detached Windows child owns a per-user singleton and exposes a shutdown signal; the child reports startup results to its parent. The existing runtime remains responsible for recording, insertion, and cleanup.

**Tech Stack:** Python 3.13, uv, Typer, Rich, Windows APIs, pytest.

**Spec:** `docs/superpowers/specs/2026-11-17-github-templates-and-local-cli-design.md`

## Global Constraints

- Windows 11 x64 and Python 3.13 are the supported baseline.
- Do not publish this project to an index or download runtime models during installation or startup.
- Preserve offline recognition, focus checks, paste safeguards, and privacy boundaries.
- Use Typer and Rich as runtime dependencies; `python -m transcriber` compatibility is not required.
- The existing pinned engine and model setup remains separate.

## Review Focus

- Concurrent starts: only one child can own the singleton.
- Startup timeout or child crash: never report success, and do not leave an unreported child.
- Stale process information or reused PID: never terminate an unrelated process.
- Missing microphone or invalid assets: doctor returns actionable failure without capturing audio.
- Terminal closure and changed working directory: the installed background app continues to work.

## File map

- `pyproject.toml`, `uv.lock`: package metadata, build backend, CLI entry point, dependencies.
- `transcriber/cli.py`: Typer commands and Rich presentation.
- `transcriber/service.py`: Windows singleton, startup handshake, shutdown coordination, child launch.
- `transcriber/__main__.py`: runtime readiness reporting and Tk-thread shutdown integration.
- `transcriber/doctor.py`: non-recording environment checks.
- `tests/test_cli.py`, `tests/test_service.py`, `tests/test_doctor.py`: focused behavior tests.
- `.github/ISSUE_TEMPLATE/bug_report.md`, `.github/pull_request_template.md`: contributor templates.
- `README.md`, `CONTRIBUTING.md`: installation, usage, and development instructions.

The templates and CLI are separable deliverables. They share this plan because
the user requested one small pre-release specification; Task 1 can ship alone.

### Task 1: GitHub contribution templates

**Files:** Create `.github/ISSUE_TEMPLATE/bug_report.md`, `.github/pull_request_template.md`.

**Interfaces:** GitHub discovers the issue template by its front matter and
location and the pull request template by its path.

- [ ] Create a Markdown issue template with GitHub `name` and `about` front
  matter. Ask for reproduction steps, expected and actual results, environment,
  and relevant diagnostics. Warn against posting private audio, transcripts,
  clipboard contents, and window titles.
- [ ] Create the PR template with summary, tests, limitations, applicable
  privacy and insertion checkboxes, and a link to `CONTRIBUTING.md`.
- [ ] Check both paths and required sections locally. On GitHub, verify template
  discovery after publication; record that check as pending until then.
- [ ] Commit the two template files.

### Task 2: Installable package and CLI surface

**Files:** Modify `pyproject.toml`, `uv.lock`; create `transcriber/cli.py` and `tests/test_cli.py`.

**Interfaces:** Expose Typer application `transcriber.cli:app` as `yat`.
Later tasks attach `start`, `stop`, and `doctor` commands to this application.

- [ ] Add tests using `typer.testing.CliRunner`: `yat --help` exits 0 and lists
  `start`, `stop`, and `doctor`; an unknown command exits nonzero. Initially
  use command stubs that explicitly report unimplemented behavior.
- [ ] Run `uv run pytest tests/test_cli.py -q`; confirm failure before the CLI exists.
- [ ] Configure a build backend and explicit `transcriber` package discovery,
  remove `[tool.uv] package = false`, add Typer and Rich runtime dependencies,
  and register `[project.scripts] yat = \"transcriber.cli:app\"`.
- [ ] Add the Typer application and command stubs. Update `uv.lock` with
  `uv lock`, then run `uv sync --locked` and the CLI tests; expect success.
- [ ] Build with `uv build` and inspect the wheel for `transcriber` and the
  console entry point. Do not publish it.
- [ ] Commit the package metadata, lockfile, CLI, and tests.

### Task 3: Background lifecycle and safe shutdown

**Files:** Create `transcriber/service.py`, `tests/test_service.py`; modify
`transcriber/__main__.py`, `transcriber/cli.py`, `tests/test_runtime.py`.

**Interfaces:** `start_service() -> tuple[bool, str]` and
`stop_service() -> tuple[bool, str]` in `transcriber/service.py`; CLI commands
print the returned message and exit nonzero on `False`. The child entry point
accepts a startup-report channel and calls the existing `Runtime` methods.

- [ ] Write tests for successful readiness only after `Runtime.start()` succeeds;
  missing assets, hotkey conflict, early crash, and timeout all report failure.
  Assert a timed-out launcher cleans up only the child process it created.
  Run the tests and confirm they fail before implementation.
- [ ] Write tests for simultaneous starts, duplicate start, stop, repeated
  stop, stale state, and PID reuse. Assert at most one instance and no process
  termination based solely on a PID. Verify stop invokes `Runtime.shutdown()`
  on the Tk thread and releases the listener and recorder.
- [ ] Implement a Windows per-user/session named mutex held for the lifetime
  of the child, plus a named shutdown event. Derive names from the current
  Windows user SID and session. Use a random per-launch startup-report channel.
  Do not use a PID file as authority for stop. A stale mutex or event must not
  be treated as a running instance without a successful readiness handshake.
- [ ] Launch the child with the installed interpreter and detached Windows
  process flags, with no dependence on the current directory. Pass a private
  startup channel and wait for a bounded response. On timeout, terminate only
  the `Popen` child that this invocation created and wait for its exit.
- [ ] In the child, acquire the mutex atomically, start the existing runtime,
  and report ready only after asset validation and hotkey registration succeed.
  Report explicit failure otherwise. Watch the shutdown event without touching
  Tk from a worker thread; queue `Runtime.shutdown()` onto the Tk thread.
  Close handles on all exit paths, including indicator Exit.
- [ ] Connect `yat start` and `yat stop` to the service functions. Stop signals
  only the named instance and waits a bounded time for the mutex to release;
  no-instance is a successful, informative no-op.
- [ ] Run `uv run pytest tests/test_service.py tests/test_runtime.py tests/test_cli.py -q`;
  all tests must pass. Commit these files.

### Task 4: Doctor checks

**Files:** Create `transcriber/doctor.py`, `tests/test_doctor.py`; modify `transcriber/cli.py`.

**Interfaces:** `run_checks() -> list[tuple[str, bool | None, str]]` returns
check name, pass/fail/unknown, and actionable detail. CLI exits nonzero if any
required check is false; unknown shortcut status is informational.

- [ ] Test Windows x64/Python 3.13, valid and invalid assets, missing default
  microphone, and successful checks. Mock `sounddevice` device queries and
  assert no input stream opens and no audio is captured.
- [ ] Test shortcut reporting for an active YAT instance, independent conflict,
  and an unavailable or unsafe probe. A probe must always unregister a hotkey
  it successfully registers. Assert output excludes transcript, clipboard, and
  window-title content.
- [ ] Run `uv run pytest tests/test_doctor.py -q`; confirm failure before implementation.
- [ ] Implement `run_checks()` using `Paths.for_home`, existing `check_assets`,
  platform checks, and `sounddevice` device metadata. Reuse the service's
  singleton check before any safe temporary hotkey probe. Catch device and
  permission errors and report corrective guidance without exposing private data.
- [ ] Connect `yat doctor` to `run_checks()` and render statuses with Rich.
  Run `uv run pytest tests/test_doctor.py tests/test_cli.py -q`; expect success.
- [ ] Commit the doctor module, CLI changes, and tests.

### Task 5: Documentation and end-to-end verification

**Files:** Modify `README.md`, `CONTRIBUTING.md`; add or update tests only if
verification finds a defect.

- [ ] Document cloning and the existing PowerShell asset setup. From the
  checkout, show `uv tool install --python 3.13 .`, `uv tool update-shell`,
  `yat start`, `yat stop`, and `yat doctor`. Explain that a new terminal may
  be required for PATH changes, and that model setup still needs the checkout.
- [ ] Document local updates with `uv tool install --force --python 3.13 .`
  from the updated checkout and removal with `uv tool uninstall yet-another-transcriber`.
  Explain the separate Python dependency sources, model storage, privacy,
  limitations, and how to start development tests.
- [ ] Run `uv sync --locked`, `uv run pytest -q`, `uv run ruff check .`,
  `uv run ruff format --check .`, and `uv run ty check`. All must pass.
- [ ] With the user's permission, stop any existing dictation instance before
  manual testing. Install locally, launch from a different directory, close the
  launching terminal, run doctor, and stop from a second terminal. Confirm
  `yat start` works again and no duplicate instance is created. Do not disturb
  an active session without permission. Record any checks not performed.
- [ ] Verify the installed wheel does not need the checkout at runtime and
  does not fetch models. Verify the existing focus, fallback, and no-Enter
  tests still pass. Record GitHub template discovery as pending until pushed.
- [ ] Commit documentation and any separately tested fixes.
