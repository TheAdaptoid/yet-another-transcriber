"""Command-line interface for Yet Another Transcriber."""

import json
import os
import tempfile
from pathlib import Path

import typer
from rich.console import Console

app = typer.Typer(no_args_is_help=True)
console = Console()
microphone_app = typer.Typer(no_args_is_help=True)
app.add_typer(
    microphone_app, name="microphone", help="List or select input microphones."
)
model_app = typer.Typer(no_args_is_help=True)
app.add_typer(model_app, name="model", help="View or select the speech model.")


@model_app.command("list")
def model_list() -> None:
    """Show supported models and the selected model."""
    from transcriber.config import MODEL_FILES, Paths

    try:
        home = Path(os.environ["USERPROFILE"])
        selected = Paths.for_home(home).model.name
        for name, filename in MODEL_FILES.items():
            console.print(f"{name}{' (selected)' if filename == selected else ''}")
    except (KeyError, OSError, ValueError) as exc:
        console.print(f"Cannot read model selection: {exc}")
        raise typer.Exit(code=1) from exc


@model_app.command("select")
def model_select(name: str) -> None:
    """Select base.en or small.en for the next start."""
    from transcriber.config import MODEL_FILES

    if name not in MODEL_FILES:
        console.print("Choose base.en or small.en.")
        raise typer.Exit(code=1)
    tmp = None
    try:
        root = Path(os.environ["USERPROFILE"]) / ".yat"
        root.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=root, delete=False
        ) as file:
            tmp = Path(file.name)
            json.dump({"model": name}, file)
        os.replace(tmp, root / "model.json")
    except (KeyError, OSError) as exc:
        console.print("Cannot save model selection; check profile permissions.")
        raise typer.Exit(code=1) from exc
    finally:
        if tmp is not None:
            tmp.unlink(missing_ok=True)
    console.print(f"Selected {name}. Restart YAT for the change to take effect.")


@microphone_app.command("list")
def microphone_list() -> None:
    """List input microphones and the current selection."""
    from transcriber import microphones

    try:
        try:
            selection = microphones.read_selection()
            selection_error = None
        except microphones.MicrophoneError as exc:
            selection = None
            selection_error = exc
        for index, name, api in microphones.input_devices():
            default = " (default)" if index == microphones.sd.default.device[0] else ""
            selected = " (selected)" if (name, api) == selection else ""
            console.print(f"{index}: {name} [{api}]{default}{selected}", markup=False)
        if selection_error is not None:
            raise selection_error
        if selection is None:
            console.print("Selection: Windows default input.")
        else:
            microphones.resolve_device()
    except microphones.MicrophoneError as exc:
        console.print(str(exc))
        raise typer.Exit(code=1) from exc


@microphone_app.command("select")
def microphone_select(index: int) -> None:
    """Select an input microphone by its current list index."""
    from transcriber import microphones

    try:
        microphones.select_device(index)
    except microphones.MicrophoneError as exc:
        console.print(str(exc))
        raise typer.Exit(code=1) from exc
    console.print("Microphone selected.")


@microphone_app.command("clear")
def microphone_clear() -> None:
    """Use the default input microphone."""
    from transcriber import microphones

    try:
        microphones.clear_selection()
    except microphones.MicrophoneError as exc:
        console.print(str(exc))
        raise typer.Exit(code=1) from exc
    console.print("Using the default input microphone.")


@app.command()
def start() -> None:
    """Start dictation in the background."""
    from transcriber.service import start_service

    ok, message = start_service()
    console.print(message)
    if not ok:
        raise typer.Exit(code=1)


@app.command()
def stop() -> None:
    """Stop the background dictation process."""
    from transcriber.service import stop_service

    ok, message = stop_service()
    console.print(message)
    if not ok:
        raise typer.Exit(code=1)


@app.command()
def doctor() -> None:
    """Check the local installation."""
    from transcriber.doctor import run_checks

    checks = run_checks()
    for name, status, detail in checks:
        label = "OK" if status is True else "UNKNOWN" if status is None else "FAIL"
        console.print(f"{name}: {label} — {detail}")
    if any(status is False for _, status, _ in checks):
        raise typer.Exit(code=1)
