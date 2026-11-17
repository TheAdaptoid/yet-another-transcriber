# Background service console

## Intent and constraints

Start and stop YAT on Windows without opening or flashing a separate console.
Preserve the existing readiness reporting, singleton and shutdown behavior, and
the safety boundaries for dictation and insertion.

## Approaches

- Use `CREATE_NO_WINDOW` instead of `DETACHED_PROCESS`, retaining the existing
  interpreter, process group, and redirected standard handles. The user chose
  this approach after a successful installed-service experiment.
- Use `pythonw.exe`. This requires further verification of virtual-environment
  selection and redirected readiness reporting, without a demonstrated benefit.

## Design and verification

Change only the service child launch flags and add regression tests for the
flags and existing lifecycle behavior. Run the repository checks. Preserve
startup errors and timeout handling. The investigation already exercised the
installed service, restart, duplicate start, missing assets, hotkey conflict,
timeout, launcher exit, and live dictation; the user observed no terminal flash.
Do not change recognizer, audio, focus, insertion, or indicator behavior.
