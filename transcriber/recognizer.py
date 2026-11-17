"""Run the pinned local speech recognizer without logging speech."""

import ctypes
import hashlib
import logging
import subprocess
import threading
import time
from contextlib import contextmanager
from ctypes import wintypes

import numpy as np

from transcriber.audio import write_temp_wav
from transcriber.config import VAD_SHA256, Paths
from transcriber.diagnostics import log_event


@contextmanager
def _lock_vad_file(paths: Paths):
    """Deny model modification and replacement until the CLI finishes."""
    kernel = ctypes.windll.kernel32
    create = kernel.CreateFileW
    create.argtypes = [
        wintypes.LPCWSTR,
        wintypes.DWORD,
        wintypes.DWORD,
        ctypes.c_void_p,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.HANDLE,
    ]
    create.restype = wintypes.HANDLE
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    handle = create(str(paths.vad_model), 0x80000000, 1, None, 3, 0x80, None)
    if handle == ctypes.c_void_p(-1).value:
        raise RecognitionError("model")
    try:
        yield
    finally:
        kernel.CloseHandle(handle)


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
        self._done.wait()

    def transcribe(self, samples: np.ndarray, paths: Paths, session_id: str) -> str:
        """Transcribe samples and always remove the temporary WAV."""
        with self._lock:
            if self._closed:
                raise RecognitionError("cli_failed")
            self._done.clear()
        try:
            with _lock_vad_file(paths):
                return self._transcribe(samples, paths, session_id)
        finally:
            self._done.set()

    def _verify_vad(self, paths: Paths) -> None:
        try:
            with paths.vad_model.open("rb") as model:
                valid_vad = (
                    hashlib.file_digest(model, "sha256").hexdigest() == VAD_SHA256
                )
        except OSError:
            valid_vad = False
        if not valid_vad:
            raise RecognitionError("model")

    def _transcribe(self, samples: np.ndarray, paths: Paths, session_id: str) -> str:
        self._verify_vad(paths)
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
                "--vad",
                "-vm",
                str(paths.vad_model),
            ]
            start = self.clock()
            try:
                with self._lock:
                    if self._closed:
                        raise RecognitionError("cli_failed")
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
            text = stdout.strip()
            return "" if text == "[BLANK_AUDIO]" else text
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
