"""Command-line interface for Yet Another Transcriber."""

import typer
from rich.console import Console

app = typer.Typer(no_args_is_help=True)
console = Console()
microphone_app = typer.Typer(no_args_is_help=True)
app.add_typer(
    microphone_app, name="microphone", help="List or select input microphones."
)


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
