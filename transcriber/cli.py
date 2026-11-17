"""Command-line interface for Yet Another Transcriber."""

import typer
from rich.console import Console

app = typer.Typer(no_args_is_help=True)
console = Console()


def _not_implemented() -> None:
    console.print("This command is not implemented yet.")
    raise typer.Exit(code=1)


@app.command()
def start() -> None:
    """Start dictation in the background."""
    _not_implemented()


@app.command()
def stop() -> None:
    """Stop the background dictation process."""
    _not_implemented()


@app.command()
def doctor() -> None:
    """Check the local installation."""
    _not_implemented()
