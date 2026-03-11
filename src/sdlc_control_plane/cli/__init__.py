"""CLI entry points for the SDLC Control Plane."""

import click


@click.group()
@click.version_option()
def main() -> None:
    """SDLC Control Plane -- certificate-driven development governance."""


@main.command()
def validate() -> None:
    """Validate certificate artifacts against the schema bundle."""
    click.echo("sdlc validate: not yet implemented (Session 1)")
