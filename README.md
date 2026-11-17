# Yet Another Transcriber

**Speak locally. Paste deliberately.**

Yet Another Transcriber is a small Windows dictation utility for OpenCode in
Windows Terminal and for Obsidian. Press **Win+Alt+S** to start recording, and
press it again to stop. The app transcribes English speech on your PC and
pastes the result at the original cursor.

This is an early personal utility. It has been
tested on one Windows 11 PC; your microphone, apps, and shortcut assignments
may behave differently. See [verification results](docs/verification.md).

## What it does

- Runs CPU-only [whisper.cpp](https://github.com/ggml-org/whisper.cpp) with the
  `base.en` model and local Silero voice activity detection.
- Records one utterance at a time, up to 60 seconds.
- Shows a corner indicator while recording and transcribing.
- Checks the original window **and** focused element before pasting.
- Keeps Terminal input on one line and sends **Ctrl+V**, never Enter.
- Shows a copyable result if the original target can no longer be verified or
  a paste fails.

> **Review before submitting.** Speech recognition and voice detection can make
> mistakes. Background speech or noise can produce unwanted text, and quiet
> speech can be missed.

## Requirements

- Windows 11, x64, and a working microphone.
- [Git](https://git-scm.com/), [CMake](https://cmake.org/), and the MSVC x64
  C++ build tools and Windows SDK. The **Desktop development with C++**
  workload in Visual Studio or Visual Studio Build Tools provides these.
- [uv](https://docs.astral.sh/uv/) and Python 3.13. `uv` can install Python.
- Windows Terminal with OpenCode, or Obsidian.
- Network access for the first setup. Setup downloads source code and models.

## Set up

Clone this repository and open PowerShell in its root directory. Install the
local Python tool and set up the speech engine and models:

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

If `yat` is not found, run `uv tool update-shell` and open a new terminal.
Keep the checkout for asset setup and local updates.

## Run and dictate

From any terminal directory, check the installation and start the app:

```powershell
yat doctor
yat start
```

`yat start` runs the app in the background, so you can close the terminal.

1. Click the input in OpenCode or the note in Obsidian.
2. Press **Win+Alt+S** and speak.
3. Press **Win+Alt+S** again. The app also stops recording after 60 seconds.
4. Review the pasted text. In OpenCode, submit it yourself if you want to.

The app ignores shortcut presses while it transcribes or inserts text. A
shortcut conflict or microphone problem appears as an error. If focus changes,
the app shows a copyable result instead of pasting automatically.

To stop the app, run `yat stop` from a terminal or select **Exit** on the
indicator. The indicator is hidden while the app is idle; press the shortcut
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
- Local diagnostic logs are stored under `%USERPROFILE%\.yat\logs`. They contain
  stage timings and error categories, not audio or transcript text.
- The app replaces the Windows clipboard with the result and does not restore
  its previous contents. If you manually paste a fallback into a terminal,
  check that it is a single line first.
- Automatic insertion is limited to supported Windows Terminal and Obsidian
  windows whose focused elements can be identified. Other targets use the
  copyable fallback.

## Contributing and license

See [CONTRIBUTING.md](CONTRIBUTING.md) for development and testing instructions.
This project's source is available under the [MIT License](LICENSE).

The setup script obtains [whisper.cpp](https://github.com/ggml-org/whisper.cpp)
and its [Whisper](https://huggingface.co/ggerganov/whisper.cpp) and
[Silero VAD](https://huggingface.co/ggml-org/whisper-vad) model assets separately.
Those projects and other dependencies have their own licenses.
