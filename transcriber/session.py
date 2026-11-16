"""Coordinate one recording and guard every insertion."""

import time
import uuid

from transcriber.config import MAX_SECONDS, SAMPLE_RATE
from transcriber.diagnostics import log_event
from transcriber.insertion import WindowsInsertion, paste_text, safe_text
from transcriber.targets import capture_target, still_focused


class SessionController:
    """Own state on the UI thread while delegating recognition to a worker."""

    def __init__(
        self,
        *,
        paths,
        logger,
        recorder,
        recognizer,
        show_state,
        schedule,
        worker,
        post,
        capture=capture_target,
        focused=still_focused,
        paste=paste_text,
        copy=None,
        clock=time.monotonic,
    ):
        """Store injected platform and scheduling ports."""
        self.paths = paths
        self.logger = logger
        self.recorder = recorder
        self.recognizer = recognizer
        self.show_state = show_state
        self.schedule = schedule
        self.worker = worker
        self.post = post
        self.capture = capture
        self.focused = focused
        self.paste = paste
        self.copy = copy or WindowsInsertion().set_clipboard
        self.clock = clock
        self.state = "idle"
        self.target = None
        self.session_id = ""
        self.generation = 0
        self.closed = False
        self.record_start = 0.0
        self.stop_time = 0.0

    def _event(self, event, started):
        log_event(
            self.logger,
            self.session_id,
            event,
            duration_ms=(self.clock() - started) * 1000,
        )

    def on_hotkey(self):
        """Start or stop recording; ignore the shortcut while processing."""
        if self.closed:
            return
        if self.state == "recording":
            self._stop()
        elif self.state == "idle":
            self._start()

    def _start(self):
        self.generation += 1
        generation = self.generation
        self.session_id = uuid.uuid4().hex
        try:
            self.target = self.capture()
            started = self.clock()
            self.recorder.start()
            self._event("mic_open", started)
            self.record_start = self.clock()
            self.state = "recording"
            self.show_state("recording", None)
            self.schedule(MAX_SECONDS, lambda: self._limit_for(generation))
        except Exception:
            self.state = "idle"
            log_event(
                self.logger, self.session_id, "error", error_category="microphone"
            )
            self.show_state("error", "Microphone could not be opened.")

    def _limit_for(self, generation):
        if generation == self.generation:
            self.on_limit()

    def on_limit(self):
        """Stop an active recording at the time limit."""
        if not self.closed and self.state == "recording":
            self._stop()

    def _stop(self):
        self.state = "transcribing"
        self.stop_time = self.clock()
        try:
            samples = self.recorder.stop()
            self._event("recording", self.record_start)
            log_event(
                self.logger,
                self.session_id,
                "audio",
                audio_duration_ms=samples.size * 1000 / SAMPLE_RATE,
            )
            self.show_state("transcribing", None)
            session_id = self.session_id
            generation = self.generation

            def job():
                try:
                    text = self.recognizer.transcribe(samples, self.paths, session_id)
                    error = None
                except Exception as exc:
                    text = None
                    error = getattr(exc, "category", "unknown")
                    if error not in {
                        "cli_missing",
                        "cli_failed",
                        "cli_timeout",
                        "model",
                    }:
                        error = "unknown"
                self.post(lambda: self._complete_for(generation, text, error))

            self.worker(job)
        except Exception:
            self.state = "idle"
            log_event(
                self.logger, self.session_id, "error", error_category="microphone"
            )
            self.show_state("error", "Recording could not be stopped.")

    def _complete_for(self, generation, text, error):
        if not self.closed and generation == self.generation:
            self.on_transcription_done(text, error)

    def on_transcription_done(self, text: str | None, error: str | None):
        """Handle recognition completion on the UI thread."""
        if self.closed or self.state != "transcribing":
            return
        if error is not None:
            self.state = "idle"
            log_event(self.logger, self.session_id, "error", error_category=error)
            self.show_state("error", "Transcription failed.")
            return
        if not text or not text.strip():
            self.state = "idle"
            self.show_state("idle", None)
            return
        self.state = "inserting"
        target = self.target
        started = self.clock()
        try:
            valid = target is not None and self.focused(target)
        except Exception:
            valid = False
        self._event("focus_check", started)
        output = safe_text(text, target.kind) if target is not None else text
        success = False
        if valid and target is not None and output:
            started = self.clock()
            success = self.paste(
                output,
                guard=lambda: self.focused(target),
                on_clipboard=lambda duration: log_event(
                    self.logger,
                    self.session_id,
                    "clipboard_write",
                    duration_ms=duration,
                ),
            )
            self._event("paste", started)
        if success:
            self._event("stop_to_insertion", self.stop_time)
            self.state = "idle"
            self.show_state("idle", None)
        else:
            try:
                self.copy(output)
            except Exception:
                pass
            self.state = "idle"
            self.show_state("copy", output)

    def close(self):
        """Stop recording and discard any late completion on shutdown."""
        self.closed = True
        self.generation += 1
        if self.state == "recording":
            self.recorder.close()
        self.state = "idle"
