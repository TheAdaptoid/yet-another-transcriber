# Yet Another Transcriber (YAT)

**"We have WisperFlow at home"**

Yet Another Transcriber is a small Windows dictation utility.
Press **Win+Alt+S** to start recording.
Press **Win+Alt+S** again to stop recording. The app transcribes English speech on your PC and
pastes the result at the original cursor.

This is an early personal utility. We tested it on one Windows 11 PC.
Behavior can differ with your microphone, apps, and shortcut assignments.

## What it does

- Runs CPU-only [whisper.cpp](https://github.com/ggml-org/whisper.cpp) with the
  `base.en` model and local Silero voice activity detection.
- Records one utterance at a time, up to 60 seconds.
- Shows a corner indicator while recording and transcribing.
- Checks the original window **and** focused element before pasting.
- Keeps automatically pasted text on one line and sends **Ctrl+V**, never Enter.
- Shows a copyable result if it cannot confirm the original target or if paste
  fails.

> **Review before submitting.** Speech recognition and voice detection can make
> mistakes. Background speech or noise can produce unwanted text.
> The app can miss quiet speech.

## Requirements

- Windows 11, x64, and a working microphone.
- [Git](https://git-scm.com/), [CMake](https://cmake.org/), and the MSVC x64
  C++ build tools and Windows SDK. Install Visual Studio or Visual Studio Build
  Tools. Include the **Desktop development with C++** workload.
- [uv](https://docs.astral.sh/uv/) and Python 3.13. `uv` can install Python.
- A target application that accepts Ctrl+V and exposes a stable focused element.
- Network access for the first setup. Setup downloads source code and models.

## Set up

Clone this repository. Open PowerShell in its root directory. Install the local
Python tool. Set up the speech engine and models:

```powershell
uv tool install --python 3.13 .
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/setup-local.ps1
```

The Python tool does not need a package-index release. Its Python dependencies
can still come from the configured package sources. The separate setup script
builds the pinned CPU CLI and downloads the English speech model and VAD
model. It checks the model hashes and writes an installation manifest under
`%USERPROFILE%\.yat`. The speech model download is approximately 142 MiB.

If setup reports an existing installation, it will not overwrite its manifest.
For an existing installation that needs the VAD model, run:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/setup-vad.ps1
```

If the terminal cannot find `yat`, run `uv tool update-shell`. Open a new terminal.
Keep the checkout for asset setup and local updates.

## Run and dictate

From any terminal directory, check the installation. Start the app:

```powershell
yat doctor
yat start
```

`yat start` runs the app in the background, so you can close the terminal.

### Choose a microphone

By default, YAT uses the current Windows default input. To choose another:

```powershell
yat microphone list
yat microphone select 2  # Replace 2 with an input index from the list.
yat doctor
```

Run `yat microphone clear` to use the default again. Selection changes take
effect at the next recording, even if YAT is already running. The selection
stores the device name and host API in `%USERPROFILE%\.yat\microphone.json`,
not its temporary index. If the device is disconnected, renamed, or has the
same name and host API as another input, YAT refuses to choose a replacement.
Reconnect it or list and select a unique device again. Identically named
replacement hardware may be indistinguishable; device changes between lookup
and stream opening are also possible.

`yat doctor` checks whether the chosen input supports 16 kHz mono int16
without recording. A successful check does not guarantee a later stream will
open, since devices can change or become busy.

> **CAUTION:** The app replaces the Windows clipboard and does not restore its
> previous contents. Fallback text is sanitized to one line, but you should
> still review it before pasting into a terminal.

1. Click an input in the target application.
2. Press **Win+Alt+S**.
3. Speak.
4. Press **Win+Alt+S** again. The app also stops recording after 60 seconds.
5. Review the pasted text. Submit it yourself if you want to.

The app ignores shortcut presses while it transcribes or inserts text. A
shortcut conflict or microphone problem appears as an error. If focus changes,
the app shows a copyable result instead of pasting automatically.

To stop the app, run `yat stop` from a terminal. Alternatively, click **Exit**
on the indicator. The app hides the indicator while idle. Press the shortcut
to show it if you need its Exit button.

## Update or uninstall

After updating your checkout, install the new version from its root:

```powershell
uv tool install --force --python 3.13 .
```

Stop the app before updating. To remove the Python tool, run:

```powershell
uv tool uninstall yet-another-transcriber
```

Uninstalling the tool does not remove the separate assets and logs under
`%USERPROFILE%\.yat`.

## Privacy and limitations

- Recognition and voice detection run locally. Setup downloads assets, but the
  application code does not download models at runtime. A full offline restart
  test is still outstanding.
- Audio stays in memory except for a temporary WAV under `%USERPROFILE%\.yat\tmp`.
  The app removes that file after use and cleans up orphan WAVs on the next
  launch.
- The app stores local diagnostic logs under `%USERPROFILE%\.yat\logs`. The logs
  have stage timings and allowlisted outcome codes for focus, clipboard, and
  input submission. They do not have audio, transcript text, or window identities.
  Input submission does not confirm that the target application pasted the text.
- The app replaces the Windows clipboard with the result and does not restore
  its previous contents. Review fallback text before manually pasting it into
  a terminal.
- The app requires the same foreground window and UI Automation element before
  paste. It rejects elements reported as disabled or password fields. Applications
  differ in their UI Automation and Ctrl+V support; compatibility is not guaranteed.
  A focus check and Ctrl+V cannot be atomic. Sending Ctrl+V does not prove that
  the target accepted the text. Check the result before you submit it.
- Clipboard-bound transcripts and displayed fallback results are sanitized to a
  single line without terminal control sequences. The app shows a copyable
  result if it cannot confirm a target or send the paste.

## Contributing and license

See [CONTRIBUTING.md](CONTRIBUTING.md) for development and testing instructions.
This project's source is available under the [MIT License](LICENSE).

The setup script downloads [whisper.cpp](https://github.com/ggml-org/whisper.cpp)
and its [Whisper](https://huggingface.co/ggerganov/whisper.cpp) and
[Silero VAD](https://huggingface.co/ggml-org/whisper-vad) model assets separately.
Those projects and other dependencies have their own licenses.
