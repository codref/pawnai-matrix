import logging
import importlib.metadata
from typing import Optional
from pathlib import Path

import typer
from typing_extensions import Annotated
from pawnai_matrix.app import App

app = typer.Typer()


@app.command()
def _command(
    config_file_path: Annotated[
        Optional[Path],
        typer.Argument(help="Path to the configuration file.")
    ] = None,
):
    """Bob the Bot of Bots."""
    version = importlib.metadata.version('pawnai_matrix')
    typer.echo(f"Bob v{version} starting up...")
    logging.basicConfig(
        format='▸ %(asctime)s.%(msecs)03d %(filename)s:%(lineno)d %(levelname)s %(message)s',
        level=logging.INFO,
        datefmt='%H:%M:%S',
    )
    bot = App()
    return bot.main_loop(config_file_path)


def main():
    app()
