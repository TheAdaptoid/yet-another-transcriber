"""Run the pinned local speech recognizer without logging speech."""

import logging
import subprocess
import threading
import time

import numpy as np

from transcriber.audio import write_temp_wav
from transcriber.config import Paths
from transcriber.diagnostics import log_event


class RecognitionError(Exception):
    """Represent a sanitized recognition failure category."""

    def __init__(self, category: str):
        """Save the safe failure category."""
        super().__init__(category)
        self.category = category


class Recognizer:
    """Run one offline CLI invocation per nonempty utterance."""

    def __init__(
        self, logger: logging.Logger, popen=subprocess.Popen, clock=time.monotonic
    ):
        """Initialize injectable process and clock ports."""
        self.logger = logger
        self.popen = popen
        self.clock = clock
        self._lock = threading.Lock()
        self._closed = False
        self._process = None
        self._done = threading.Event()
        self._done.set()

    def close(self):
        """Terminate a running CLI before the application exits."""
        with self._lock:
            self._closed = True
            if self._process is not None:
                try:
                    self._process.kill()
                except OSError:
                    pass
        self._done.wait(timeout=3)

    def transcribe(self, samples: np.ndarray, paths: Paths, session_id: str) -> str:
        """Transcribe samples and always remove the temporary WAV."""
        # A small PCM noise floor is not evidence of speech. This gate does
        # not replace voice activity detection in noisy rooms.
        if samples.size == 0 or np.max(np.abs(samples.astype(np.int32))) <= 64:
            return ""
        start = self.clock()
        wav = write_temp_wav(samples, paths.tmp)
        process = None
        finished = False
        try:
            log_event(
                self.logger,
                session_id,
                "wav_write",
                duration_ms=(self.clock() - start) * 1000,
            )
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
                with self._lock:
                    if self._closed:
                        raise RecognitionError("cli_failed")
                    self._done.clear()
                    process = self.popen(
                        args,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        encoding="utf-8",
                        errors="replace",
                        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                    )
                    self._process = process
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
                finished = True
            except subprocess.TimeoutExpired:
                process.kill()
                process.communicate()
                finished = True
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
            if process is not None and not finished:
                try:
                    process.kill()
                    process.communicate()
                except OSError:
                    pass
            with self._lock:
                self._process = None
            wav.unlink(missing_ok=True)
            self._done.set()
