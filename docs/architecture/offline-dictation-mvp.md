# Offline dictation MVP — architecture

This is the architecture for Windows 11 personal dictation. All processing remains on the PC; setup can fetch the model and runtime once, but dictation has no cloud dependency. The runtime is a Python 3.13 background process, started from a `uv`-managed virtual environment. It records a temporary WAV for a CPU-only `whisper-cli` invocation per utterance. Application data lives under `~\.yat` (`%USERPROFILE%\.yat`): models in `models\`, the CLI in `bin\`, temporary audio in `tmp\`, and logs in `logs\`. The text remains on the clipboard after insertion.

```mermaid
flowchart LR
  User["User in a target application"] -->|Win + Alt + S| Hotkey["Windows global hotkey"]
  subgraph Local["Background Windows app — local only"]
    Hotkey --> Coordinator["Python session coordinator"]
    Coordinator -->|start| Focus["Remember foreground window + UIA focused element"]
    Coordinator -->|start / stop| Audio["Microphone capture<br/>temporary WAV"]
    Coordinator -->|state| Indicator["Non-activating corner indicator<br/>recording / transcribing / error"]
    Audio -->|after stop or 60-second limit| ASR["English speech recognition<br/>CPU whisper-cli + local base.en model"]
    ASR --> Transcript["Transcript in memory"]
    Transcript --> Target{"Original target<br/>still focused?"}
    Focus --> Target
    Target -->|yes| Safe["Single-line text<br/>no control characters"]
    Safe --> Paste["Clipboard + Ctrl+V<br/>no Enter key"]
    Paste -->|success| Done["Transcript stays on clipboard"]
    Paste -->|uncertain / failed| Recovery["Copyable transcript<br/>no automatic retry"]
    Target -->|no / uncertain| Recovery
    Audio -->|capture error| Error["Visible error"]
    ASR -->|model / inference error| Error
  end
  Done --> User
  Recovery --> User
  Error --> User
```

## Dictation sequence

```mermaid
sequenceDiagram
  actor User
  participant Target as Target application
  participant App as Python background app
  participant UI as Corner indicator
  participant Mic as Microphone
  participant ASR as Local whisper-cli
  participant Clip as Windows clipboard

  User->>Target: Focus a text field
  User->>App: Press Win + Alt + S
  App->>Target: Record window and focused element identity
  App->>Mic: Start audio capture
  App->>UI: Show Recording without taking focus
  alt User stops recording
    User->>App: Press Win + Alt + S again
  else 60-second limit
    App->>App: Stop recording automatically
  end
  App->>Mic: Stop capture
  App->>UI: Show Transcribing
  App->>ASR: Transcribe temporary WAV with base.en on CPU
  ASR-->>App: English transcript or error
  App->>App: Remove temporary audio and only log timings and not content

  alt Capture or transcription failed
    App->>UI: Show error
  else Transcript available
    App->>Target: Verify original window and element still have focus
    alt Focus changed or cannot be verified
      App->>UI: Show copyable transcript, do not paste
    else Original target still focused
      App->>App: Collapse controls and newlines
      App->>Clip: Set transcript as Unicode text
      App->>Target: Send Ctrl + V only
      alt Paste succeeded
        App->>UI: Dismiss indicator
        Note over Clip: Transcript stays on clipboard
      else Paste failed or result uncertain
        App->>UI: Show copyable transcript, do not attempt a retry
      end
    end
  end
```

**Safety boundary:** the corner indicator never becomes the input target; the transcript is never sent to a cloud service. Test terminal paste to confirm that text stays editable and no command is submitted. If focus or paste success cannot be verified, prefer a copyable result over guessing. Audio is temporary, with orphan cleanup on the next launch; there is no history.

**Diagnostics boundary:** structured local logs record stage durations, state changes, and sanitized errors. They exclude audio, transcript text, clipboard data, field contents, and window titles. `ruff`, `ty`, and `pytest` are required development checks; packaging is deferred.
