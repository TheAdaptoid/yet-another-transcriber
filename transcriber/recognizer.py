import logging
import subprocess
import time

import numpy as np

from transcriber.audio import write_temp_wav
from transcriber.config import Paths
from transcriber.diagnostics import log_event


class RecognitionError(Exception):
    def __init__(self, category: str):
        super().__init__(category)
        self.category = category


class Recognizer:
    def __init__(
        self, logger: logging.Logger, popen=subprocess.Popen, clock=time.monotonic
    ):
        self.logger = logger
        self.popen = popen
        self.clock = clock

    def transcribe(self, samples: np.ndarray, paths: Paths, session_id: str) -> str:
        if samples.size == 0 or not np.any(samples):
            return ""
        start = self.clock()
        wav = write_temp_wav(samples, paths.tmp)
        log_event(
            self.logger,
            session_id,
            "wav_write",
            duration_ms=(self.clock() - start) * 1000,
        )
        try:
            if not paths.cli.is_file():
                raise RecognitionError("cli_missing")
            args = [
                str(paths.cli),
                "-m",
                str(paths.model),
                "-f",
                str(wav),
                "-l",
                "en",
                "-ng",
                "-np",
                "-nt",
            ]
            start = self.clock()
            try:
                process = self.popen(
                    args,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                )
            except OSError:
                raise RecognitionError("cli_missing") from None
            log_event(
                self.logger,
                session_id,
                "cli_start",
                duration_ms=(self.clock() - start) * 1000,
            )
            start = self.clock()
            try:
                stdout, _ = process.communicate(timeout=300)
            except subprocess.TimeoutExpired:
                process.kill()
                process.communicate()
                raise RecognitionError("cli_timeout") from None
            log_event(
                self.logger,
                session_id,
                "inference",
                duration_ms=(self.clock() - start) * 1000,
            )
            if process.returncode != 0:
                raise RecognitionError("cli_failed")
            return stdout.strip()
        finally:
            wav.unlink(missing_ok=True)
