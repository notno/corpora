"""Main CLI application for corpora."""

import typer

from corpora.cli.parse import parse_command

app = typer.Typer(
    name="corpora",
    help="Corpora: Extract vocabulary from documents into structured JSON",
    add_completion=False,
)

# Register subcommands
app.command(name="parse")(parse_command)


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: bool = typer.Option(
        False, "--version", "-V", help="Show version and exit"
    ),
) -> None:
    """Corpora: Extract vocabulary from documents into structured JSON."""
    if version:
        from corpora import __version__
        typer.echo(f"corpora {__version__}")
        raise typer.Exit()

    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())
