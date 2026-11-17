# Neo-Brutalist dictation indicator

Date: 2026-11-17
Issue: [#2 — Polish the dictation UI and status indicators](https://github.com/TheAdaptoid/yet-another-transcriber/issues/2)

## Intent

Turn the current functional but basic Windows corner overlay into an intentionally designed, professional utility. The chosen visual direction is the Neo Brutalism concept from the browser comparison: a compact stacked notice with a colored top ribbon, emphatic status text, hard rules, and a small offset shadow. It should feel distinctive without competing with the app receiving dictation.

## Goals and boundaries

- Make recording, transcribing, error, and copy-result states distinct by **words, layout, and color**; do not rely on animation or color alone.
- Keep the indicator small and bottom-right, hidden while idle, topmost without activating or stealing focus. Preserve the existing hotkey and insertion safety behavior.
- Add restrained motion only while recording or transcribing, using an honest activity cue rather than fake audio levels or percentage progress. Error and copy-result are static. Honor Windows reduced-animation preferences where feasible, with a static fallback.
- Preserve the full selectable transcript, the Copy, Dismiss, and Exit actions, and visible copy-success and copy-failure messages. A long error or transcription must remain readable and within the usable display area.
- Create durable design-language reference materials under `docs/design/` so future visual changes can follow the same Neo Brutalist system rather than treating a browser mockup as the source of truth.
- Check rendering and interaction on Windows 11 at common display scaling, including the focus-sensitive dictation path; document any hardware/manual scenarios that could not be exercised.

Non-goals: a settings window, themes, new dictation features, a live waveform, a toolkit replacement, changes to recognition or paste behavior, and recreating the HTML/CSS mockup pixel-for-pixel. Avoid motion that flashes or suggests progress that the app cannot measure.

## Approaches

1. **Chosen — style the existing Tk overlay.** Compose a compact bordered panel with Tk widgets or Canvas where useful; draw the offset shadow *within* the same window, and schedule/cancel small animation steps on Tk's UI event loop. This delivers most of the visual identity while retaining the current, tested non-activating Win32 window handling and keeping dependencies unchanged. Tradeoff: a real shadow extending beyond the window or true native visual effects are out of scope.
2. **Native Windows window effects.** A layered/shaped companion window or DWM effects could achieve a more literal outer silhouette. Tradeoff: additional HWND, DPI, hit-testing, focus, and window-lifecycle risks for a cosmetic benefit.
3. **New UI toolkit.** More rendering freedom, but a disproportionate dependency and lifecycle rewrite for a small background utility.

Prior mockup exploration compared Gen X Soft Club, Acidwave, Neo Swiss, Liquid Glass–inspired, and Neo Brutalism; the user chose Neo Brutalism and prioritized reliability over a literal outside shadow.

## Surface and behavior

- **Recording:** coral ribbon with a readable `RECORDING` label; the main line says `Recording…`; the existing `Win+Alt+S to stop` hint remains. A small stepped signal in the ribbon changes at a slow, comfortable cadence. Exit remains available.
- **Transcribing:** blue ribbon labeled `TRANSCRIBING`; main line says `Transcribing…`; a different small stepped activity cue shows that work is ongoing without claiming measurable progress. Exit remains available.
- **Error:** warm yellow ribbon labeled `ERROR`; show the actual error string, or `Dictation failed.` when absent. No motion. Dismiss hides this result without quitting; Exit still quits.
- **Copy result:** warm yellow ribbon labeled `RESULT`; the status explains that automatic paste did not occur; display the complete transcription in a readable, selectable text area with Copy, Dismiss, and Exit. Copy success and failure visibly update status without removing the text.
- All four states share a warm cream panel, near-black square border and separator rules, a contained offset black shadow, and compact uppercase ribbon text. Only the ribbon accent and meaningful content change between states. Keep the body text naturally cased for legibility.
- Keep controls visually distinct from the banner and text. The non-activating indicator's actions are pointer-only; keyboard focus cannot reach them. Maintain clear text contrast and usable target sizes, and ensure dynamic errors can wrap without covering controls.
- Keep the existing `Indicator` adapter API and `SessionController` state flow. Drawing, animation callbacks, status updates, and window geometry remain on Tk's UI thread. Stop pending callbacks when the state changes, the overlay hides, or it closes.
- Retain the current `WS_EX_NOACTIVATE` / tool-window and no-activate show/position behavior. Determine placement from the usable Windows display area where practical; make geometry and text behave sensibly at supported DPI scales and with longer copy results.

## Design language reference

Ship these materials alongside the UI, and keep them consistent with the **implemented** result rather than the aspirational HTML studies:

- `docs/design/README.md`: an entry point explaining the product's Neo Brutalist direction, its scope, and where to find the rules and a worked example.
- `docs/design/neo-brutalism.md`: the reusable visual language — palette and semantic state colors (with final color values), type hierarchy, spacing/shape/border/shadow rules, compact layout principles, purposeful motion and reduced-motion behavior, contrast and focus guidance, and clear do/don't examples. Distinguish foundational rules from indicator-specific choices so later surfaces can reuse them.
- `docs/design/indicator.md`: the indicator as a worked example, with the four real states, control placement, copy-result and long-text behavior, animation cues, and a visual state reference (a diagram or capture that reflects the shipped implementation). Explain the focus-safety and scaling constraints that a future redesign must preserve.
- Update `CONTRIBUTING.md` to link to `docs/design/README.md` and direct contributors to consult the design references before changing visual UI. Place this guidance near the existing instructions for checking indicator changes.

These documents describe the design; they do not add a runtime dependency or expand this issue into other UI surfaces.

## Builder decisions left open

Choose the smallest Tk composition that renders the hard border/shadow cleanly, uses consistent font sizes/spacing in logical units, and keeps native Text selection working. Animation should stay well below flashing speed, at roughly one change per second. If the system's animation preference cannot be read reliably, show a static activity mark instead; do not introduce a new dependency solely to query it. Keep copy and error text factual; do not invent new recovery promises. Treat wrapping and a scrollable result as preferable to clipping or an overlay that grows beyond the usable screen.

## Verification

Automated tests should cover state-specific controls and text, copy-result selection/copy feedback, animation callback cleanup and reduced-motion behavior where testable, and geometry that does not clip under representative scaling/long text. Check the `docs/design/` references against the final colors, components, and motion rather than merely the mockup; verify the link from `CONTRIBUTING.md`. Run the repository's formatting, lint, type, and test checks. Manually verify on Windows that recording and processing do not take focus, fallback text remains selectable, Dismiss and Exit behave correctly, and visual hierarchy/readability hold at available display scaling settings (100%, 125%, and 150% if accessible). Record any untested scaling or device combinations.
