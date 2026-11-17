"""Command-line interface for Yet Another Transcriber."""

import typer
from rich.console import Console

app = typer.Typer(no_args_is_help=True)
console = Console()


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
