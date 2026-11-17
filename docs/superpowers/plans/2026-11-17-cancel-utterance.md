# Cancel utterance implementation plan

**Goal:** Resolve issue #7 without allowing canceled speech to be inserted or retained.

**Architecture:** Create a cancellation handle for each recognition job before scheduling it. Each job owns its process and WAV; cancellation kills only that process, while shutdown waits for all active jobs. The UI controller invalidates generations and queued hotkeys before returning to idle. The indicator invokes cancellation on the UI thread.

**Tech stack:** Python 3.13, Tk, pytest, Windows subprocesses.

**Spec:** GitHub issue #7 and its investigation comment.

## Constraints and review focus

- Preserve local-only recognition, VAD validation, focus checks and temporary WAV cleanup.
- A cancellation before worker entry, during WAV creation, or while launching must prevent or terminate the CLI.
- Old success and error callbacks must not affect a new recording or clipboard.
- Shutdown must wait for all active jobs, and cancellation must not kill a later job.
- Capture-close failure must not submit audio; repeated cancellation is harmless.
- Manual Windows microphone, focus, and indicator interaction must be reported honestly.

## Tasks

1. Add failing controller tests for recording cancellation, stale timers/hotkeys, late completions and reuse; implement UI-thread cancellation and per-job token creation.
2. Add failing recognizer race tests using threading events for pre-launch and active cancellation, overlapping jobs, cleanup and shutdown; implement per-job process ownership and cancellation.
3. Add failing indicator and runtime tests for button visibility, callback and constrained layouts; wire the button to the controller.
4. Run locked setup, lint, format, type checks and the full test suite; document baseline failures and manual cases not tested, then create a PR using the repository template.
