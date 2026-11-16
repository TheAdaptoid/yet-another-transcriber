import importlib.util
import json
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "summarize-logs.py"
spec = importlib.util.spec_from_file_location("summary", SCRIPT)
summary = importlib.util.module_from_spec(spec)
spec.loader.exec_module(summary)


def test_summary_ignores_malformed_and_private_fields(tmp_path):
    path = tmp_path / "events.jsonl"
    records = [
        {"session_id": "a", "event": "inference", "duration_ms": 10},
        {"session_id": "b", "event": "inference", "duration_ms": 30},
        {
            "session_id": "c",
            "event": "inference",
            "duration_ms": 20,
            "transcript": "secret",
        },
        {"session_id": "a", "event": "mic_open", "duration_ms": 4},
        {"session_id": "a", "event": "secret_words", "duration_ms": 1},
        {"session_id": "a", "event": "paste", "duration_ms": "secret"},
    ]
    path.write_text("\n".join(json.dumps(record) for record in records) + "\n{broken\n")
    result = summary.summarize(path)
    assert result["inference"] == {"count": 3, "median_ms": 20, "p95_ms": 30}
    assert result["mic_open"] == {"count": 1, "median_ms": 4, "p95_ms": 4}
    assert "paste" not in result and "wav_write" not in result
    output = subprocess.check_output(
        [sys.executable, str(SCRIPT), str(path)], text=True
    )
    assert "secret" not in output
    assert str(path) not in output


def test_summary_accepts_utf8_bom(tmp_path):
    path = tmp_path / "events.jsonl"
    path.write_text('{"event":"inference","duration_ms":120}\n', encoding="utf-8-sig")
    assert summary.summarize(path)["inference"]["median_ms"] == 120
