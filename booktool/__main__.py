"""
Booktool CLI
"""
from typing import List
import logging
import os

import click

import booktool
from booktool.audio import find_audio
from booktool.audio.track import (
    get_album,
    get_artist,
    get_duration,
    get_track_number,
    set_track_number,
)
from booktool.util import chmod, move, sanitize

logger = logging.getLogger(booktool.__name__)


@click.group(help=__doc__)
@click.version_option(booktool.__version__)
@click.option("-v", "--verbose", count=True, help="Increase logging verbosity")
def cli(verbose: int):
    level = logging.WARNING - (verbose * 10)
    logging.basicConfig(format="%(levelname)-7s %(name)s - %(message)s", level=level)
    logging.debug("Set logging level to %s [%d]", logging.getLevelName(level), level)


@cli.command()
@click.argument("paths", type=click.Path(exists=True), nargs=-1)
@click.option(
    "-d",
    "--destination",
    type=click.Path(exists=True, file_okay=False),
    default=os.getcwd(),
    show_default=True,
    help="Destination directory",
)
@click.option(
    "-n",
    "--dry-run",
    is_flag=True,
    help="Don't actually do anything, just log any changes that would be made",
)
def canonicalize(paths: List[str], destination: str, dry_run: bool):
    """
    Rearrange audio files into canonical structure.

    1. restructure directories and filenames
    2. fix file permissions
    2. fix track numbers
    """
    for path in find_audio(*paths):
        artist = sanitize(get_artist(path))
        album = sanitize(get_album(path))
        _, ext = os.path.splitext(os.path.basename(path))
        track_number, total_tracks = get_track_number(path)
        part_width = len(str(total_tracks))

        new_filename = f"{track_number:0{part_width}}{ext}".lower()
        new_filepath = os.path.join(destination, artist, album, new_filename)

        # move to destination
        path = move(path, new_filepath, dry_run=dry_run)
        # fix permissions on files
        chmod(path, 0o644, dry_run=dry_run)
        # fix track numbers in audio
        set_track_number(path, track_number, total_tracks)
        # ignore xattrs; they're dropped when syncing to cloud storage anyway


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
