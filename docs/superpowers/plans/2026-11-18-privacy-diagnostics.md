# Privacy-safe Diagnostics Implementation Plan

**Goal:** Make dictation failures diagnosable without exposing private data.

**Architecture:** Preserve bounded outcomes at the Windows focus and insertion boundaries, and translate them into allowlisted diagnostic fields and user-facing messages on the UI thread. Keep existing safety checks and never claim input submission proves insertion.

**Spec:** https://github.com/TheAdaptoid/yet-another-transcriber/issues/17#issuecomment-6999315914

**Constraints:** Windows 11 and Python 3.13; local only; no sensitive logs; fail closed on uncertain focus; Ctrl+V only.

## Tasks

- [x] Add tested typed outcomes for target capture and focus verification.
- [x] Add tested typed outcomes for clipboard, guarded input submission, and fallback copying.
- [x] Log allowlisted stage outcomes and surface actionable failure messages; retain selectable fallback.
- [x] Distinguish recognition and startup failure messages without disclosing raw exceptions.
- [x] Run privacy, safety, and full regression checks; document manual tests not performed.
- [ ] Review the diff, commit, push, and open a PR referencing issue 17.
