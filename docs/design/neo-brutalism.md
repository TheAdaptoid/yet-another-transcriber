# Neo-Brutalist visual language

## Intent and scope

Use confident type, flat semantic accents, square edges, near-black rules, and
a small contained offset shadow. Keep the notice subordinate to the window
receiving dictation. This is a design direction for future utility surfaces,
not a requirement to add borders or animation to every UI element.

## Foundational rules

| Role | Color | Use |
| --- | --- | --- |
| Paper | `#F8EFD2` | Primary panel and button surface |
| Ink | `#151515` | Text, border, separator, activity mark, and contained shadow |
| Reading surface | `#FFF8E6` | Selectable transcript and long-error text |
| Recording | `#F36746` | Recording ribbon only |
| Processing | `#A6D4EF` | Transcribing ribbon only |
| Attention/result | `#F5CB5E` | Error and copy-result ribbons; button active surface |
| Selection | `#151515` / `#FFFFFF` | Selected text background / foreground |

Use near-black text on the paper and on all three state ribbons. The words
`RECORDING`, `TRANSCRIBING`, `ERROR`, and `RESULT` carry the state even without
color. Never encode state only in hue or in an animation.

- **Type:** Segoe UI, with the system's fallback. In the indicator, status is
  bold 13-point, ribbon and buttons bold 9-point, and hint and selectable text
  10-point. Keep long body text naturally cased; reserve uppercase for the
  compact state ribbon. Do not simulate an audio meter with type or symbols.
- **Shape and depth:** square 2-pixel ink border, 2-pixel horizontal separator,
  and an ink offset visible for 7 pixels at the right and bottom *inside the
  same window*. The shadow is intentionally hard-edged for this chosen visual
  world; it is not a second window or a focusable companion.
- **Grouping:** ribbon content has 11 pixels of horizontal and 5 pixels of
  vertical inset. The message uses 12/9 pixels; actions use 10/7 pixels and
  sit below the separator. Buttons have a 2-pixel square border, 7/3 pixels
  internal padding, and a visible keyboard focus highlight. Use breathing room
  between distinct groups, not between a label and its meaning.
- **Motion:** a tiny ink mark moves horizontally for recording; three stepped
  bars cycle for transcribing. A Tk callback changes one step about every
  1,000 ms. Neither mark represents sound levels or percentage complete.
  Errors, results, and idle are static. If Windows reports client-area
  animations disabled or its preference cannot be queried, show a static
  activity mark without scheduling a callback. Cancel pending motion when
  the state changes, hides, or closes.
- **Contrast and focus:** test text against every accent, including selected
  transcript text. Keep the native selectable Text and scrollbar, visible
  button keyboard focus, and large enough button targets. The overlay must
  never activate merely to display a new state.

## Applying the system

**Do:** label the status in words and put recovery controls in a separate,
consistent action row. Keep complete results scrollable when the available
screen area is small. Let the UI remain legible with animation turned off.

**Don't:** use blinking, a fake waveform, rounded glass cards, pastel text on a
pastel ribbon, or a decorative second HWND that risks focus changes. Do not
cut off an error or transcription to preserve a fixed visual height.

See the [indicator example](indicator.md) for actual state layouts and
Windows placement rules.
