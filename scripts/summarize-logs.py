"""Summarize known latency events without displaying log content."""

import argparse
import json
import math
import statistics
from pathlib import Path

STAGES = {
    "mic_open",
    "recording",
    "wav_write",
    "cli_start",
    "inference",
    "focus_check",
    "clipboard_write",
    "paste",
    "stop_to_insertion",
}


def summarize(path: Path) -> dict[str, object]:
    """Return count, median, and nearest-rank p95 for each observed stage."""
    values: dict[str, list[float]] = {}
    with path.open(encoding="utf-8-sig") as source:
        for line in source:
            try:
                record = json.loads(line)
                if not isinstance(record, dict):
                    continue
                event = record.get("event")
                duration = record.get("duration_ms")
                if (
                    isinstance(event, str)
                    and event in STAGES
                    and isinstance(duration, (int, float))
                    and not isinstance(duration, bool)
                    and math.isfinite(duration)
                    and duration >= 0
                ):
                    values.setdefault(event, []).append(duration)
            except (ValueError, TypeError):
                continue
    result: dict[str, object] = {}
    for stage, durations in values.items():
        durations.sort()
        result[stage] = {
            "count": len(durations),
            "median_ms": statistics.median(durations),
            "p95_ms": durations[math.ceil(len(durations) * 0.95) - 1],
        }
    return result


def main() -> None:
    """Print only the aggregate stage values."""
    parser = argparse.ArgumentParser(description="Summarize local dictation timings.")
    parser.add_argument("path", type=Path, help="JSON-lines log file")
    args = parser.parse_args()
    try:
        print(json.dumps(summarize(args.path), indent=2, sort_keys=True))
    except OSError:
        parser.exit(1, "Could not read log file.\n")


if __name__ == "__main__":
    main()
