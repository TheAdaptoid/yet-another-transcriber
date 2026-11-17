"""Fixed settings and per-user storage locations."""

from dataclasses import dataclass
from pathlib import Path

MAX_SECONDS = 60
SAMPLE_RATE = 16000
MODEL_NAME = "ggml-base.en.bin"
VAD_MODEL_NAME = "ggml-silero-v5.1.2.bin"
VAD_SHA256 = "29940d98d42b91fbd05ce489f3ecf7c72f0a42f027e4875919a28fb4c04ea2cf"


@dataclass(frozen=True)
class Paths:
    """App-specific data paths under a single user profile."""

    root: Path
    model: Path
    vad_model: Path
    cli: Path
    tmp: Path
    log: Path

    @classmethod
    def for_home(cls, home: Path) -> "Paths":
        """Create app paths without creating files or directories."""
        root = home / ".yat"
        return cls(
            root=root,
            model=root / "models" / MODEL_NAME,
            vad_model=root / "models" / VAD_MODEL_NAME,
            cli=root / "bin" / "whisper-cli.exe",
            tmp=root / "tmp",
            log=root / "logs" / "app.jsonl",
        )
