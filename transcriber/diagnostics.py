"""Write strictly allowlisted local diagnostic events."""

import json
import logging
import re
from logging.handlers import RotatingFileHandler
from pathlib import Path

from transcriber.config import MODEL_NAME

_NUMERIC_FIELDS = {
    "duration_ms",
    "audio_duration_ms",
    "output_characters",
}
_STRING_VALUES = {
    "model": {MODEL_NAME},
    "process_name": {"WindowsTerminal.exe", "Obsidian.exe"},
    "error_category": {
        "microphone",
        "model",
        "cli_missing",
        "cli_failed",
        "cli_timeout",
        "focus",
        "clipboard",
        "paste",
        "hotkey",
        "unknown",
    },
}
_TOKEN = re.compile(r"^[a-zA-Z0-9_-]{1,64}$")
_EVENTS = {
    "mic_open",
    "recording",
    "audio",
    "wav_write",
    "cli_start",
    "inference",
    "focus_check",
    "clipboard_write",
    "paste",
    "stop_to_insertion",
    "error",
    "result",
    "target",
}


def make_logger(path: Path) -> logging.Logger:
    """Create a five-file rotating JSON-lines logger."""
    path.parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger(f"yat.{path.resolve()}")
    logger.setLevel(logging.INFO)
    logger.propagate = False
    if not logger.handlers:
        handler = RotatingFileHandler(
            path, maxBytes=5 * 1024 * 1024, backupCount=4, encoding="utf-8"
        )
        handler.setFormatter(logging.Formatter("%(message)s"))
        logger.addHandler(handler)
    return logger


def log_event(
    logger: logging.Logger, session_id: str, event: str, **metrics: float | str
) -> None:
    """Write one event after rejecting non-allowlisted metadata."""
    if not _TOKEN.fullmatch(session_id) or event not in _EVENTS:
        raise ValueError("Invalid event identity")
    for key, value in metrics.items():
        if key in _NUMERIC_FIELDS:
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValueError("Invalid numeric metric")
        elif key not in _STRING_VALUES or value not in _STRING_VALUES[key]:
            raise ValueError("Invalid metric")
    logger.info(json.dumps({"session_id": session_id, "event": event, **metrics}))
