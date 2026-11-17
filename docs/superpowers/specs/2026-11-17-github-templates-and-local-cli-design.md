# GitHub templates and local CLI

## Purpose and scope

Make the project easier to use and contribute to before its GitHub release.
Add an issue template, a pull request template, and a locally installable CLI.
This document specifies the work; it does not implement it.

Do not publish to PyPI or another package index. Keep Windows 11 x64 and Python
3.13 as the supported baseline. Preserve the existing offline recognition,
focus checks, paste safeguards, and privacy boundaries.

## Approaches

For launching, a foreground process is simpler and matches the current app.
The selected approach starts a background process so the terminal is free.
This needs process coordination and explicit startup and shutdown reporting.

For installation, use `uv tool install` from a local checkout, with a console
entry point. Running via `uv run` from the checkout is an alternative, but it
does not meet the goal of an installed command usable from any directory.

## GitHub templates

- Add a concise issue template under `.github/ISSUE_TEMPLATE/`. Ask for the
  problem, steps to reproduce, expected and actual behavior, and environment.
  Remind reporters not to include audio, transcripts, clipboard contents, or
  other private information. Allow space for relevant diagnostics.
- Add `.github/pull_request_template.md`. Ask for a summary, test results, and
  known limitations. Include a short checklist for privacy and safe insertion
  when the change affects those areas. Link to `CONTRIBUTING.md`.
- Keep both templates useful for a small personal project. Do not require a
  complex issue workflow or automation.

## Local package and commands

1. Add a Python build backend and configure package discovery in
   `pyproject.toml`. Remove the setting that disables packaging.
2. Add a `yat` console entry point and retain `python -m transcriber` for
   existing users. Keep development dependencies out of the installed tool.
3. Document local installation with `uv tool install` from a checkout, PATH
   setup with `uv tool update-shell` if needed, updates, and uninstall.
   Python dependencies may still come from their configured package sources;
   the project itself does not need publication to an index.
4. Keep the existing one-time setup for the pinned speech engine and models.
   Explain its build tools, network needs, and `%USERPROFILE%\.yat` assets.
   Installing the Python package must not silently download runtime models.
5. Update the README and contribution instructions for the new commands and
   preserve the existing setup and safety guidance.

### `yat start`

Launch one detached background instance and return control to the terminal.
Report success only after the child confirms asset checks and hotkey
registration. Report a useful error and nonzero exit status if startup fails
or times out. An already-running instance must not create a second instance.
The app must work regardless of the terminal's current directory.

### `yat stop`

Request a clean shutdown of the running instance and report the result. The
command must work from another terminal and be safe when no instance exists.
Use process coordination that verifies instance identity; do not terminate an
unrelated process because of a stale or reused process ID. Release the hotkey
and microphone and clean temporary audio through the normal shutdown path.

### `yat doctor`

Check the supported environment, Python runtime, required local assets and
their integrity, and microphone availability without recording audio. Report
actionable failures and exit nonzero for required checks that fail. Check
whether the shortcut is available only when doing so is safe; distinguish an
active instance from an independent shortcut conflict or an unknown result.
Do not print or log transcripts, audio, clipboard content, or window titles.

## Verification

- Run the existing automated tests and add tests for packaging and CLI behavior.
- Test start, duplicate start, stop, repeated stop, startup failure, stale
  process state, and doctor success and failure without real audio capture.
- Install the tool from a local checkout and run `yat` commands from another
  directory. Verify the background instance remains active after its launching
  terminal closes and stops cleanly from a second terminal.
- Verify the existing dictation safeguards remain intact. State which manual
  checks were not performed.
- Check that GitHub recognizes both template paths and that the README gives a
  complete setup path for a fresh user.
