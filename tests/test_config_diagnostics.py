import json
import logging.handlers
from pathlib import Path

import pytest

from transcriber.config import MODEL_NAME, Paths
from transcriber.diagnostics import log_event, make_logger


def test_paths_are_under_user_home():
    paths = Paths.for_home(Path("C:/Users/Test"))
    assert paths.root == Path("C:/Users/Test/.yat")
    assert paths.model == paths.root / "models" / MODEL_NAME
    assert paths.vad_model == paths.root / "models" / "ggml-silero-v5.1.2.bin"
    assert paths.cli == paths.root / "bin" / "whisper-cli.exe"
    assert paths.tmp == paths.root / "tmp"
    assert paths.log == paths.root / "logs" / "app.jsonl"


def test_rotating_logger_and_allowed_event(tmp_path):
    logger = make_logger(tmp_path / "app.jsonl")
    handler = logger.handlers[0]
    assert isinstance(handler, logging.handlers.RotatingFileHandler)
    assert handler.maxBytes == 5 * 1024 * 1024
    assert handler.backupCount == 4
    log_event(logger, "abc", "recording", duration_ms=123.0, model=MODEL_NAME)
    data = json.loads((tmp_path / "app.jsonl").read_text())
    assert data["duration_ms"] == 123.0
    assert data["session_id"] == "abc"


@pytest.mark.parametrize(
    "field",
    ["transcript", "audio", "clipboard", "window_title", "exception", "process_name"],
)
def test_rejects_private_fields(tmp_path, field):
    logger = make_logger(tmp_path / "app.jsonl")
    with pytest.raises(ValueError):
        log_event(logger, "abc", "error", **{field: "dictated secret words"})
    assert "dictated secret words" not in (tmp_path / "app.jsonl").read_text()


def test_rejects_exception_as_category(tmp_path):
    logger = make_logger(tmp_path / "app.jsonl")
    with pytest.raises(ValueError):
        log_event(logger, "abc", "error", error_category="dictated secret words")
    assert "dictated secret words" not in (tmp_path / "app.jsonl").read_text()


def test_rejects_content_in_event_name(tmp_path):
    logger = make_logger(tmp_path / "app.jsonl")
    with pytest.raises(ValueError):
        log_event(logger, "abc", "secretword", duration_ms=1)
    assert "secretword" not in (tmp_path / "app.jsonl").read_text()
