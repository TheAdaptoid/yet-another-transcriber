"""Manage microphone selection without capturing audio."""

import json
import os
import tempfile
from pathlib import Path

import sounddevice as sd

from transcriber.config import SAMPLE_RATE

CHANNELS = 1
DTYPE = "int16"
GUIDANCE = "Run 'yat microphone list' and select a microphone, or clear the selection."


class MicrophoneError(RuntimeError):
    """A safe, actionable microphone configuration error."""


def settings_path() -> Path:
    """Return the current user's selection path."""
    home = os.environ.get("USERPROFILE")
    if not home:
        raise MicrophoneError("USERPROFILE is unavailable; check your Windows profile.")
    return Path(home) / ".yat" / "microphone.json"


def read_selection() -> tuple[str, str] | None:
    """Load a selection, rejecting invalid or unreadable settings."""
    path = settings_path()
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None
    except (OSError, UnicodeError) as exc:
        raise MicrophoneError(f"Cannot read microphone settings. {GUIDANCE}") from exc
    try:
        data = json.loads(text)
        if (
            not isinstance(data, dict)
            or set(data) != {"name", "hostapi"}
            or not all(isinstance(data[k], str) and data[k] for k in data)
        ):
            raise ValueError
        return data["name"], data["hostapi"]
    except (ValueError, UnicodeError) as exc:
        raise MicrophoneError(f"Invalid microphone settings. {GUIDANCE}") from exc


def input_devices() -> list[tuple[int, str, str]]:
    """List input device indices, names and host API names."""
    try:
        devices = sd.query_devices()
        hostapis = sd.query_hostapis()
        return [
            (index, device["name"], hostapis[device["hostapi"]]["name"])
            for index, device in enumerate(devices)
            if device["max_input_channels"] > 0
        ]
    except Exception as exc:
        raise MicrophoneError(f"Cannot list microphones. {GUIDANCE}") from exc


def resolve_device() -> int | None:
    """Resolve the stored identity against the current device inventory."""
    selection = read_selection()
    if selection is None:
        return None
    matches = [
        index for index, name, api in input_devices() if (name, api) == selection
    ]
    if len(matches) != 1:
        problem = "missing" if not matches else "ambiguous"
        raise MicrophoneError(f"Selected microphone is {problem}. {GUIDANCE}")
    return matches[0]


def select_device(index: int) -> None:
    """Persist a unique current input device identity, not its unstable index."""
    devices = input_devices()
    selected = next(((name, api) for i, name, api in devices if i == index), None)
    if selected is None:
        raise MicrophoneError(f"Input device index not found. {GUIDANCE}")
    if sum((name, api) == selected for _, name, api in devices) != 1:
        raise MicrophoneError(f"Selected microphone is ambiguous. {GUIDANCE}")
    path = settings_path()
    tmp = None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=path.parent, delete=False
        ) as f:
            tmp = Path(f.name)
            json.dump({"name": selected[0], "hostapi": selected[1]}, f)
        os.replace(tmp, path)
    except OSError as exc:
        raise MicrophoneError(
            "Cannot save microphone settings; check profile permissions."
        ) from exc
    finally:
        if tmp is not None:
            tmp.unlink(missing_ok=True)


def clear_selection() -> None:
    """Restore default-device behavior."""
    try:
        settings_path().unlink(missing_ok=True)
    except OSError as exc:
        raise MicrophoneError(
            "Cannot clear microphone settings; check profile permissions."
        ) from exc


def check_format(device: int | None) -> None:
    """Validate the recording format without opening a recording stream."""
    try:
        sd.check_input_settings(
            device=device, samplerate=SAMPLE_RATE, channels=CHANNELS, dtype=DTYPE
        )
    except Exception as exc:
        raise MicrophoneError(
            "Microphone does not support 16 kHz mono int16 input or is unavailable. "
            f"{GUIDANCE}"
        ) from exc
