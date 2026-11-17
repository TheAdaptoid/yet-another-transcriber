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


class Cancellation:
    """Own cancellation and the process for one recognition invocation."""

    def __init__(self):
        """Create an independent cancellation handle."""
        self._lock = threading.Lock()
        self._canceled = False
        self._process = None

    def cancel(self):
        """Mark this invocation canceled and terminate its process if present."""
        with self._lock:
            self._canceled = True
            if self._process is not None:
                try:
                    self._process.kill()
                except OSError:
                    pass

    def check(self):
        """Raise if the invocation was canceled."""
        with self._lock:
            if self._canceled:
                raise RecognitionError("canceled")

    def register(self, process):
        """Associate a process, terminating it if cancellation won the race."""
        with self._lock:
            self._process = process
            if self._canceled:
                try:
                    process.kill()
                except OSError:
                    pass

    def unregister(self):
        """Release the process after it has been reaped."""
        with self._lock:
            self._process = None


class Recognizer:
    """Run one offline CLI invocation per nonempty utterance."""

    def __init__(
        self, logger: logging.Logger, popen=subprocess.Popen, clock=time.monotonic
    ):
        """Initialize injectable process and clock ports."""
        self.logger = logger
        self.popen = popen
        self.clock = clock
        self._lock = threading.Condition()
        self._closed = False
        self._active = set()

    def close(self):
        """Terminate a running CLI before the application exits."""
        with self._lock:
            self._closed = True
            active = tuple(self._active)
        for cancellation in active:
            cancellation.cancel()
        with self._lock:
            while self._active:
                self._lock.wait()

    def transcribe(
        self,
        samples: np.ndarray,
        paths: Paths,
        session_id: str,
        cancellation: Cancellation | None = None,
    ) -> str:
        """Transcribe samples and always remove the temporary WAV."""
        cancellation = cancellation or Cancellation()
        with self._lock:
            if self._closed:
                raise RecognitionError("cli_failed")
            self._active.add(cancellation)
        try:
            cancellation.check()
            with _lock_vad_file(paths):
                return self._transcribe(samples, paths, session_id, cancellation)
        finally:
            with self._lock:
                self._active.remove(cancellation)
                self._lock.notify_all()

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

    def _transcribe(
        self,
        samples: np.ndarray,
        paths: Paths,
        session_id: str,
        cancellation: Cancellation,
    ) -> str:
        self._verify_vad(paths)
        cancellation.check()
        # A small PCM noise floor is not evidence of speech. This gate does
        # not replace voice activity detection in noisy rooms.
        if samples.size == 0 or np.max(np.abs(samples.astype(np.int32))) <= 64:
            return ""
        start = self.clock()
        wav = write_temp_wav(samples, paths.tmp)
        process = None
        finished = False
        try:
            cancellation.check()
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
                cancellation.check()
                process = self.popen(
                    args,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                )
                cancellation.register(process)
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
            cancellation.unregister()
            wav.unlink(missing_ok=True)
