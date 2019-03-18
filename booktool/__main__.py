"""
Booktool CLI
"""
import logging

import click

import booktool

logger = logging.getLogger(booktool.__name__)


@click.group(help=__doc__)
@click.version_option(booktool.__version__)
@click.option("-v", "--verbose", count=True, help="Increase logging verbosity.")
def cli(verbose: int):
    level = logging.WARNING - (verbose * 10)
    logging.basicConfig(
        format="%(asctime)14s %(levelname)-7s %(name)s - %(message)s", level=level
    )
    logging.debug("Set logging level to %s [%d]", logging.getLevelName(level), level)


main = cli.main

if __name__ == "__main__":
    main(prog_name=f"python -m {booktool.__name__}")
