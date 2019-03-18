"""
Booktool CLI
"""
from typing import Iterable, Iterator, List
import logging
import os
import re

import click
import mutagen

import booktool
from booktool.audio import is_audio
from booktool.audio.track import set_track_number, get_duration

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
    for path in paths:
        logger.info("Fixing track numbers in book: %s", path)
        filenames = list(filter(is_audio, os.listdir(path)))
        total_tracks = len(filenames)
        logger.info("Found %d chapters", total_tracks)
        for filename in filenames:
            logger.info("Fixing track number in file: %s", filename)
            filepath = os.path.join(path, filename)
            file = mutagen.File(filepath)

            track_filename = os.path.basename(filename)
            track_number = int(re.search(r"\d+", track_filename).group(0))
            set_track_number(file, track_number, total_tracks)


@cli.command()
@click.argument("paths", type=click.Path(exists=True), nargs=-1)
def duration(paths: List[str]):
    """
    Sum total duration of all indicated audio files.

    For each supplied directory, expand to all audio files immediately inside.
    For each file, find the duration and sum the total seconds.
    """

    def get_durations(paths: Iterable[str]) -> Iterator[float]:
        for path in paths:
            if os.path.isdir(path):
                for filename in os.listdir(path):
                    if is_audio(filename):
                        filepath = os.path.join(path, filename)
                        yield get_duration(filepath)
            else:
                yield get_duration(path)

    total_duration = round(sum(get_durations(paths)))
    print(total_duration)


main = cli.main

if __name__ == "__main__":
    main(prog_name=f"python -m {booktool.__name__}")
