"""Capture bounded mono audio and manage temporary WAV files."""

import tempfile
import threading
import wave
from pathlib import Path

import numpy as np
import sounddevice as sd

from transcriber.config import MAX_SECONDS, SAMPLE_RATE


class Recorder:
    """Capture samples in memory, rejecting stale stream callbacks."""

    def __init__(self, stream_factory=sd.InputStream):
        """Initialize the recorder with an injectable stream factory."""
        self._stream_factory = stream_factory
        self._lock = threading.Lock()
        self._generation = 0
        self._active = False
        self._chunks = []
        self._count = 0
        self._stream = None

    def start(self):
        """Start one capture stream."""
        with self._lock:
            if self._active:
                raise RuntimeError("Already recording")
            self._generation += 1
            generation = self._generation
            self._chunks = []
            self._count = 0
            self._active = True

        def callback(indata, frames, time_info, status):
            del frames, time_info, status
            with self._lock:
                if not self._active or generation != self._generation:
                    return
                remaining = SAMPLE_RATE * MAX_SECONDS - self._count
                if remaining > 0:
                    chunk = np.asarray(indata[:remaining, 0], dtype=np.int16).copy()
                    self._chunks.append(chunk)
                    self._count += chunk.size

        try:
            self._stream = self._stream_factory(
                samplerate=SAMPLE_RATE, channels=1, dtype="int16", callback=callback
            )
            self._stream.start()
        except Exception:
            self.close()
            raise

    def stop(self):
        """Stop the stream and return a copy of the recorded samples."""
        with self._lock:
            self._active = False
            chunks = self._chunks
            self._chunks = []
            stream, self._stream = self._stream, None
        if stream is not None:
            try:
                stream.stop()
            finally:
                stream.close()
        return np.concatenate(chunks).copy() if chunks else np.empty(0, dtype=np.int16)

    def close(self):
        """Close the current stream if one is active."""
        self.stop()


def write_temp_wav(samples: np.ndarray, directory: Path) -> Path:
    """Write the provided signed PCM samples to an owned temporary WAV."""
    directory.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        prefix="yat-", suffix=".wav", dir=directory, delete=False
    ) as f:
        path = Path(f.name)
    try:
        with wave.open(str(path), "wb") as output:
            output.setnchannels(1)
            output.setsampwidth(2)
            output.setframerate(SAMPLE_RATE)
            output.writeframes(np.asarray(samples, dtype="<i2").tobytes())
    except Exception:
        path.unlink(missing_ok=True)
        raise
    return path


def cleanup_temp_wavs(directory: Path) -> None:
    """Remove only WAV files owned by this application."""
    if directory.exists():
        for path in directory.glob("yat-*.wav"):
            if path.is_file():
                path.unlink()
