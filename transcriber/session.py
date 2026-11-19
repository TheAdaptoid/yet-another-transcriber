"""Coordinate one recording and guard every insertion."""

import threading
import time
import uuid

from transcriber.config import MAX_SECONDS, SAMPLE_RATE
from transcriber.diagnostics import log_event
from transcriber.insertion import (
    ClipboardOutcome,
    PasteOutcome,
    WindowsInsertion,
    paste_text_result,
    safe_text,
)
from transcriber.microphones import MicrophoneError
from transcriber.recognizer import Cancellation
from transcriber.targets import (
    TargetOutcome,
    TargetResult,
    capture_target_result,
    check_focus,
)


def _focus_matches(outcome):
    return outcome is True or outcome == TargetOutcome.MATCH


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
        capture=capture_target_result,
        focused=check_focus,
        paste=paste_text_result,
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
        self._hotkey_lock = threading.Lock()
        self._hotkey_epoch = 0
        self._cancellation = None

    def enqueue_hotkey(self, post):
        """Discard presses received while busy, including delayed queue entries."""
        with self._hotkey_lock:
            if self.closed or self.state not in {"idle", "recording"}:
                return
            epoch = self._hotkey_epoch

        def deliver():
            with self._hotkey_lock:
                current = epoch == self._hotkey_epoch
            if current:
                self.on_hotkey()

        post(deliver)

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
            captured = self.capture()
            if isinstance(captured, TargetResult):
                self.target = captured.target
                log_event(
                    self.logger, self.session_id, "target", outcome=captured.outcome
                )
            else:
                self.target = captured
            started = self.clock()
            self.recorder.start()
            self._event("mic_open", started)
            self.record_start = self.clock()
            self.state = "recording"
            self.show_state("recording", None)
            self.schedule(MAX_SECONDS, lambda: self._limit_for(generation))
        except Exception as exc:
            self.state = "idle"
            log_event(
                self.logger, self.session_id, "error", error_category="microphone"
            )
            message = (
                str(exc)
                if isinstance(exc, MicrophoneError)
                else "Microphone could not be opened."
            )
            self.show_state("error", message)

    def _limit_for(self, generation):
        if generation == self.generation:
            self.on_limit()

    def on_limit(self):
        """Stop an active recording at the time limit."""
        if not self.closed and self.state == "recording":
            self._stop()

    def _stop(self):
        with self._hotkey_lock:
            self.state = "transcribing"
            self._hotkey_epoch += 1
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
            cancellation = Cancellation()
            self._cancellation = cancellation

            def job():
                try:
                    text = self.recognizer.transcribe(
                        samples, self.paths, session_id, cancellation
                    )
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

    def cancel(self):
        """Discard the active utterance on the UI thread."""
        if self.closed or self.state not in {"recording", "transcribing"}:
            return
        previous = self.state
        with self._hotkey_lock:
            self.generation += 1
            self._hotkey_epoch += 1
            self.state = "idle"
        if previous == "transcribing":
            if self._cancellation is not None:
                self._cancellation.cancel()
                self._cancellation = None
        else:
            try:
                self.recorder.close()
            except Exception:
                log_event(
                    self.logger, self.session_id, "error", error_category="microphone"
                )
                self.show_state("error", "Recording could not be closed.")
                return
        self.show_state("idle", None)

    def _final_focus_guard(self, target):
        try:
            return self.focused(target)
        except Exception:
            return TargetOutcome.AUTOMATION_ERROR

    def _log_final_focus(self, outcome):
        if isinstance(outcome, TargetOutcome):
            log_event(
                self.logger,
                self.session_id,
                "focus_check",
                outcome=outcome,
                stage="final",
            )

    def _initial_focus(self, target):
        started = self.clock()
        try:
            focus = (
                self.focused(target)
                if target is not None
                else TargetOutcome.UNAVAILABLE
            )
        except Exception:
            focus = TargetOutcome.AUTOMATION_ERROR
        self._event("focus_check", started)
        if isinstance(focus, TargetOutcome):
            log_event(
                self.logger,
                self.session_id,
                "focus_check",
                outcome=focus,
                stage="initial",
            )
        return focus

    def _log_paste_result(self, result):
        if not isinstance(result, PasteOutcome):
            return
        log_event(self.logger, self.session_id, "paste", outcome=result)
        if result != PasteOutcome.UNKNOWN:
            log_event(
                self.logger,
                self.session_id,
                "clipboard_write",
                outcome=(
                    "clipboard_failed"
                    if result == PasteOutcome.CLIPBOARD_FAILED
                    else "clipboard_succeeded"
                ),
            )

    def on_transcription_done(self, text: str | None, error: str | None):
        """Handle recognition completion on the UI thread."""
        if self.closed or self.state != "transcribing":
            return
        if error is not None:
            self.state = "idle"
            log_event(self.logger, self.session_id, "error", error_category=error)
            message = {
                "cli_timeout": "Transcription timed out. Try a shorter recording.",
                "cli_missing": "Speech engine unavailable. Run setup.",
                "model": "Speech model unavailable or invalid. Run setup.",
                "cli_failed": "Speech engine failed. Check local assets and run setup.",
            }.get(error, "Transcription failed.")
            self.show_state("error", message)
            return
        if not text or not text.strip():
            self.state = "idle"
            self.show_state("idle", None)
            return
        log_event(
            self.logger,
            self.session_id,
            "result",
            output_characters=len(text),
            model=self.paths.model.name,
        )
        self.state = "inserting"
        target = self.target
        focus = self._initial_focus(target)
        valid = _focus_matches(focus)
        output = safe_text(text)
        success = False
        result = None
        if valid and target is not None and output:
            started = self.clock()
            final_focus = None

            def guard():
                nonlocal final_focus
                final_focus = self._final_focus_guard(target)
                return _focus_matches(final_focus)

            result = self.paste(
                output,
                guard=guard,
                on_clipboard=lambda duration: log_event(
                    self.logger,
                    self.session_id,
                    "clipboard_write",
                    duration_ms=duration,
                ),
            )
            self._log_final_focus(final_focus)
            success = result is True or result == PasteOutcome.INPUT_SUBMITTED
            self._log_paste_result(result)
            self._event("paste", started)
        if success:
            self._event("stop_to_input_submission", self.stop_time)
            self.state = "idle"
            self.show_state("idle", None)
        else:
            try:
                copy_result = self.copy(output)
                copied = copy_result is True or copy_result == ClipboardOutcome.COPIED
            except Exception:
                copied = False
            log_event(
                self.logger,
                self.session_id,
                "fallback",
                outcome="copy_succeeded" if copied else "copy_failed",
            )
            self.state = "idle"
            copy_state = {
                PasteOutcome.CLIPBOARD_FAILED: "copy_clipboard",
                PasteOutcome.FOCUS_REJECTED: "copy_focus",
                PasteOutcome.INPUT_REJECTED: "copy_input",
            }.get(
                result,
                "copy_focus"
                if isinstance(focus, TargetOutcome) and not valid
                else "copy",
            )
            if not copied:
                copy_state = "copy_failed"
            self.show_state(copy_state, output)

    def close(self):
        """Stop recording and discard any late completion on shutdown."""
        self.closed = True
        self.generation += 1
        if self.state == "recording":
            self.recorder.close()
        self.recognizer.close()
        self.state = "idle"
