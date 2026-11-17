# Dictation indicator: worked example

The current implementation is `_TkOverlay` in
[`transcriber/indicator.py`](../../transcriber/indicator.py), behind the
existing `Indicator` adapter. All four states use this structure:

```text
┌── COLORED STATE RIBBON ────────── activity (active states only) ┐
│ Bold status or message; recording also shows the stop hint      │
│ ┌─ Full selectable transcript / long error ──┐ (when needed)   │
├────────────────────── near-black rule ──────────────────────────┤
│                                            actions by state      │
└────────────────── cream panel + contained offset shadow ───────┘
```

The diagram shows reading order, not a pixel-accurate capture. The transcript
or long-error text comes **before** the separator and action row. Long text
scrolls in a read-only, selectable Text widget; its stored contents are not
truncated.

| State | Ribbon | Main message | Additional content | Actions |
| --- | --- | --- | --- | --- |
| Recording | Coral `RECORDING`, moving single mark | `Recording…` | `Win+Alt+S to stop` hint | Exit |
| Transcribing | Blue `TRANSCRIBING`, stepped three-bar mark | `Transcribing…` | None | Exit |
| Error | Yellow `ERROR`, static | Actual error or `Dictation failed.` | Very long error moves to a scrollable detail area, with the complete text | Dismiss, Exit |
| Copy result | Yellow `RESULT`, static | `Could not paste. Select or copy this result.` | Entire selectable, scrollable transcript | Copy, Dismiss, Exit |

When Copy succeeds, the status reads `Copied. You can dismiss this result.`;
when it fails, it reads `Copy failed. Select the text and try again.` The
transcript stays intact in both cases. Dismiss hides the overlay without
quitting; Exit closes the application via its existing callback.
These actions are pointer-only: the non-activating overlay does not accept
keyboard focus, so Tab cannot reach the buttons.

## Size, placement, and interaction

The panel is approximately 260 pixels wide in short active states at the
reference Tk scaling; more text can grow it up to approximately 385 logical
pixels, subject to the usable work area. A 20-pixel scaled margin keeps it near
the bottom-right of the primary work area, above the taskbar. The contained
shadow uses seven pixels of that window. At smaller work areas and different
Tk scaling, the panel and the visible Text height shrink before clipping
actions; the underlying transcript and long error remain selectable and
scrollable. The precise rendered dimensions depend on fonts and DPI.

Rendering and status updates remain on the Tk UI thread. The HWND keeps
`WS_EX_NOACTIVATE` and tool-window styling; Win32 shows and positions it with
non-activating flags. Do not transfer focus when recording starts, changes to
transcribing, or displays a result. Preserve the original target-window and
focused-element checks before any automatic paste; showing this notice must
not weaken them. Keep recording and recognition local.

See the [shared design language](neo-brutalism.md) for color values, typography,
motion, and focus guidance. Test this screen manually on Windows when changing
focus, geometry, insertion, or any of its controls; record cases not tested in
the pull request.
