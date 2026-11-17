# Neo-Brutalist Dictation Indicator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a compact, professionally styled Neo-Brutalist Windows dictation overlay and durable design references without changing focus, paste, or fallback safety.

**Architecture:** Keep the existing `Indicator` adapter and `_TkOverlay` in Tk. Build a single square bordered panel with a contained offset shadow, state ribbon, text, controls, and scrollable transcript; use the existing non-activating Win32 window path. Compute screen placement after layout, then add cancellable Tk `after` activity cues with a Windows animation-preference check. Document the shipped visual language under `docs/design/`.

**Tech Stack:** Windows 11 x64, Python 3.13, tkinter, ctypes/Win32, pytest, uv, Ruff, ty; no new runtime dependencies.

**Spec:** `docs/superpowers/specs/2026-11-17-neo-brutalist-dictation-indicator-design.md`

## Global Constraints

- Keep the overlay bottom-right, topmost, hidden while idle, and non-activating; retain `WS_EX_NOACTIVATE`, tool-window, and no-activate show/position behavior.
- Keep `Indicator.show(state: str, text: str | None = None)`, `close()`, and `clipboard_owner()` and the existing `SessionController` state flow.
- Preserve the exact functional copy `Recording…`, `Transcribing…`, `Win+Alt+S to stop`, `Dictation failed.`, `Could not paste. Select or copy this result.`, `Copied. You can dismiss this result.`, and `Copy failed. Select the text and try again.`; dynamic errors take precedence over the default.
- Keep all drawing, state updates, geometry, and scheduled callbacks on Tk's UI thread; never alter recognition, hotkey, target, clipboard, or paste behavior.
- The full fallback transcript stays selectable and copyable; Copy, Dismiss, and Exit remain available in the appropriate states.
- Use a warm cream body (`#F8EFD2`), near-black ink/rules (`#151515`), coral recording (`#F36746`), blue transcribing (`#A6D4EF`), and yellow error/result (`#F5CB5E`); document final values if visual testing changes them.
- Animate recording and transcribing only, well below flashing speed; respect `SPI_GETCLIENTAREAANIMATION` when available and stay static if the query fails. Do not imply audio amplitude or percent complete.
- Do not add a new toolkit, settings surface, runtime dependency, or separate native shadow window. Do not log or commit audio, transcripts, clipboard contents, or window titles.

## Review Focus

- Long unbroken error text: wrapping and clamping keep the message and controls visible (Task 2 test).
- Long multiline fallback: the whole result remains in the selectable, scrollable Text widget rather than being truncated (Task 1 test; Task 2 bounds test).
- Fast recording → transcribing → idle → close transitions: no old animation callback updates a hidden or destroyed widget (Task 3 test).
- Animations disabled or Win32 query unavailable: the active state remains readable and static with no scheduled callback (Task 3 test).
- Small work area or changed Tk scaling: geometry stays inside the work area and focus still belongs to the original app (Task 2 test and Task 4 manual check).

## File map

- `transcriber/indicator.py`: Neo-Brutalist Tk layout, state presentation, cancellable motion, Win32 no-activate display, and placement.
- `tests/test_indicator.py`: focused Windows Tk/widget, animation, fallback, and geometry tests; supplement existing `tests/test_runtime.py` adapter tests without rewriting unrelated tests.
- `docs/design/README.md`: index and scope for future visual contributors.
- `docs/design/neo-brutalism.md`: implemented palette, hierarchy, shape, spacing, motion, contrast, and design do/don't rules.
- `docs/design/indicator.md`: annotated state diagram/visual reference and constraints for this worked example.
- `CONTRIBUTING.md`: link to design references near indicator testing guidance.

### Task 1: State-specific Tk panel and fallback

**Files:**
- Modify: `transcriber/indicator.py`
- Create: `tests/test_indicator.py`

**Interfaces:**
- Consumes: existing `_TkOverlay(root, on_close)`, `present(state: str, text: str | None)`, `hide()`, `close()`, `clipboard_owner()`, `_copy()`; existing `Indicator` facade unchanged.
- Produces: `_TkOverlay.ribbon`, `.state_label`, `.label`, `.hint_label`, `.activity_label`, `.transcript`, `.copy_button`, `.dismiss_button`, `.close_button`, and top-level `_PAPER`, `_INK`, `_STATE_COLORS: dict[str, str]`. Task 2 uses the layout and Text widget; Task 3 uses `activity_label`.

- [ ] **Step 1: Write failing widget tests** in `tests/test_indicator.py`: `test_states_have_distinct_ribbons_and_real_text`, `test_error_uses_dynamic_text_and_keeps_actions`, `test_copy_result_is_complete_selectable_and_reports_clipboard_outcomes`. Create/destroy a real `tk.Tk()` per test; verify ribbon labels/colors, recording hint, exact copy/error messages, correct Copy/Dismiss/Exit visibility, a long multiline result returned intact by `transcript.get("1.0", "end-1c")`, selection via `tag_add("sel", ...)`, and success/failure messages via a fake `WindowsInsertion`. Preserve existing `tests/test_runtime.py` behavior.
- [ ] **Step 2: Run** `uv run pytest -q tests/test_indicator.py` and confirm the new tests fail on the old layout.
- [ ] **Step 3: Implement** the layout in `transcriber/indicator.py`: keep `.label` as the visible primary status so existing tests still inspect it; add a square bordered cream panel, internal black offset shadow, compact uppercase colored ribbon, separately grouped controls with visible focus, a recording hint, and a fixed-height scrollable `tk.Text` with `exportselection=False`. Keep the current Win32 non-activation path and exact copy feedback; do not truncate the underlying transcript or invent recovery messages. Add the specified module-level colors.
- [ ] **Step 4: Run** `uv run pytest -q tests/test_indicator.py tests/test_runtime.py`; expect all tests to pass.
- [ ] **Step 5: Commit** `transcriber/indicator.py`, `tests/test_indicator.py`, and the approved spec/plan if they are still untracked: `git commit -m "feat: style dictation indicator states"`.

### Task 2: Work-area placement and scalable long-content layout

**Files:**
- Modify: `transcriber/indicator.py`
- Modify: `tests/test_indicator.py`

**Interfaces:**
- Consumes: Task 1 widgets and `_TkOverlay.present`.
- Produces: `_TkOverlay._work_area() -> tuple[int, int, int, int]` (left, top, right, bottom; primary Windows usable area, with Tk screen fallback) and `_TkOverlay._place() -> None` (fit width/height, anchor inside work area, call the existing no-activate Win32 show/position sequence).

- [ ] **Step 1: Write failing** `test_long_error_and_result_stay_within_work_area` and `test_layout_respects_tk_scaling` in `tests/test_indicator.py`. Stub `_work_area` with a constrained rectangle; present a very long error without spaces and many result lines; after `update_idletasks()`, assert root geometry lies inside the rectangle, buttons are mapped in the relevant state, and the full error and result remain accessible in their respective scrollable views. Repeat at representative `tk scaling` values while restoring the original scaling afterward.
- [ ] **Step 2: Run** `uv run pytest -q tests/test_indicator.py::test_long_error_and_result_stay_within_work_area tests/test_indicator.py::test_layout_respects_tk_scaling`; expect failures before placement adapts.
- [ ] **Step 3: Implement** `_work_area()` using `SystemParametersInfoW(SPI_GETWORKAREA=0x0030)` and `wintypes.RECT`, with a Tk screen-size fallback on API failure; keep geometry in the same coordinate space as Tk on the supported Windows setup. Implement `_place()` by constraining panel width, text wrap, and visible transcript height to the work-area dimensions before computing geometry, preserving a modest edge margin where possible. When an error exceeds available height, show its complete message in a scrollable read-only text view instead of clipping controls; keep the full result scrollable too. Keep `GetWindowLongPtrW`/`SetWindowLongPtrW`, `ShowWindow(..., SW_SHOWNOACTIVATE=4)`, and `SetWindowPos(..., SWP_NOACTIVATE | SWP_SHOWWINDOW)` intact.
- [ ] **Step 4: Run** `uv run pytest -q tests/test_indicator.py tests/test_runtime.py`; expect all tests to pass.
- [ ] **Step 5: Commit** `transcriber/indicator.py` and `tests/test_indicator.py`: `git commit -m "fix: fit indicator within usable display area"`.

### Task 3: Accessible, cancellable state motion

**Files:**
- Modify: `transcriber/indicator.py`
- Modify: `tests/test_indicator.py`

**Interfaces:**
- Consumes: Task 1 `.activity_label` and stateful `present`/`hide`/`close`.
- Produces: `_TkOverlay._animations_enabled() -> bool`, `_TkOverlay._start_animation(state: str) -> None`, `_TkOverlay._stop_animation() -> None`; `_animation_job: str | None` holds the pending Tk `after` token.

- [ ] **Step 1: Write failing** `test_activity_moves_only_in_active_states_and_cancels_on_transition`, `test_hide_and_close_cancel_pending_activity`, and `test_disabled_or_unavailable_animation_is_static` in `tests/test_indicator.py`. Patch `_animations_enabled` and use a spy/fake for Tk `after`/`after_cancel`; verify recording and transcribing schedule a roughly 1-second change with distinct static/dynamic glyphs; error, copy, hide, and close leave no pending token; simulate a stale callback after close and assert it never touches a destroyed widget. With preference false or query failure, check a visible static mark and no timer.
- [ ] **Step 2: Run** `uv run pytest -q tests/test_indicator.py -k 'activity or animation'`; expect failures before adding animation.
- [ ] **Step 3: Implement** `_animations_enabled()` with `SystemParametersInfoW(SPI_GETCLIENTAREAANIMATION=0x1042)` and a BOOL, returning `False` if the query fails. Implement distinct small stepped cues on `activity_label` at about 1 change per second through Tk `after`; cancel/clear before every state transition, hide, and destroy. Guard each callback against a stale state or closed overlay; never infer live sound amplitude.
- [ ] **Step 4: Run** `uv run pytest -q tests/test_indicator.py tests/test_runtime.py`; expect all tests to pass.
- [ ] **Step 5: Commit** `transcriber/indicator.py` and `tests/test_indicator.py`: `git commit -m "feat: add accessible dictation activity cues"`.

### Task 4: Design language, contributor guidance, and release checks

**Files:**
- Create: `docs/design/README.md`
- Create: `docs/design/neo-brutalism.md`
- Create: `docs/design/indicator.md`
- Modify: `CONTRIBUTING.md`

**Interfaces:**
- Consumes: actual final colors/widgets/motion from Tasks 1–3.
- Produces: a navigable design reference from `CONTRIBUTING.md` to `docs/design/README.md`, onward to the system and indicator example.

- [ ] **Step 1: Write** `docs/design/neo-brutalism.md` with implemented hex colors and semantic roles, Segoe UI/type hierarchy, measurements for border, shadow, spacing, state ribbon and controls, motion and reduced-motion rules, contrast/focus guidance, and examples of good/bad application. Write `docs/design/indicator.md` with an annotated four-state diagram matching the shipped layout, exact action visibility, long-text/copy-result behavior, and focus/DPI constraints; no private transcript sample. Add `docs/design/README.md` as the entry point, and link it from `CONTRIBUTING.md` by the existing indicator-testing paragraph.
- [ ] **Step 2: Verify** that every relative Markdown link resolves (`Test-Path docs/design/README.md`, `Test-Path docs/design/neo-brutalism.md`, `Test-Path docs/design/indicator.md`, and `Select-String -Path CONTRIBUTING.md -Pattern 'docs/design/README.md'`) and that documented colors, copy, sizes, activity behavior, and state visuals agree with `transcriber/indicator.py`. Expect no broken links or mockup-only claims.
- [ ] **Step 3: Run** from repository root: `uv sync --locked`, `uv run ruff check .`, `uv run ruff format --check .`, `uv run ty check`, and `uv run pytest -q`; expect all to pass.
- [ ] **Step 4: With the user's permission before stopping any running instance, manually test on Windows 11**: record/stop in Terminal and Obsidian, confirm original focus remains and insertion only goes to the original focused element, check no Enter is sent, inspect recording/transcribing/error/copy UI and animation, select/copy a fallback, test Dismiss and Exit, and inspect 100%, 125%, 150% scaling where available plus reduced-animation mode. Record what passed and what could not be tested in the PR or final handoff; do not publish real dictated text.
- [ ] **Step 5: Commit** `docs/design/README.md`, `docs/design/neo-brutalism.md`, `docs/design/indicator.md`, and `CONTRIBUTING.md`: `git commit -m "docs: record indicator design language"`.

After implementation, compare the rendered Windows overlay against the selected Neo Brutalism mockup and correct visual defects before claiming completion; the HTML mockup is not an implementation test.
