"""
Booktool CLI
"""
from typing import List
import logging

import click

import booktool
from booktool.audio import find_audio
from booktool.audio.track import get_duration, get_track_number, set_track_number

logger = logging.getLogger(booktool.__name__)


@click.group(help=__doc__)
@click.version_option(booktool.__version__)
@click.option("-v", "--verbose", count=True, help="Increase logging verbosity")
def cli(verbose: int):
    level = logging.WARNING - (verbose * 10)
    logging.basicConfig(
        format="%(asctime)14s %(levelname)-7s %(name)s - %(message)s", level=level
    )
    logging.debug("Set logging level to %s [%d]", logging.getLevelName(level), level)


@cli.command()
@click.argument("paths", type=click.Path(exists=True, file_okay=False), nargs=-1)
def fix_track_numbers(paths: List[str]):
    """
    Fix track numbers in audiobook(s)
    """
    for path in find_audio(*paths):
        track_number, total_tracks = get_track_number(path)
        set_track_number(path, track_number, total_tracks)


@cli.command()
@click.argument("paths", type=click.Path(exists=True), nargs=-1)
def duration(paths: List[str]):
    """
    Sum total duration of all indicated audio files.

    For each directory, recursively expand to all files within.
    For each file, exclude if the name does not match known audio extensions.
    """
    total_duration = round(sum(map(get_duration, find_audio(*paths))))
    print(total_duration)


main = cli.main

if __name__ == "__main__":
    main(prog_name=f"python -m {booktool.__name__}")
