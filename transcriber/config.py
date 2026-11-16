from dataclasses import dataclass
from pathlib import Path

MAX_SECONDS = 60
SAMPLE_RATE = 16000
MODEL_NAME = "ggml-base.en.bin"


@dataclass(frozen=True)
class Paths:
    root: Path
    model: Path
    cli: Path
    tmp: Path
    log: Path

    @classmethod
    def for_home(cls, home: Path) -> "Paths":
        root = home / ".yat"
        return cls(
            root=root,
            model=root / "models" / MODEL_NAME,
            cli=root / "bin" / "whisper-cli.exe",
            tmp=root / "tmp",
            log=root / "logs" / "app.jsonl",
        )
