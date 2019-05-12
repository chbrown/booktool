"""
Booktool CLI
"""
from typing import List, Tuple
from itertools import groupby
import logging
import os

import click

import booktool
from booktool.audio import find_audio
from booktool.audio.track import (
    get_album,
    get_artist,
    get_duration,
    get_track_info,
    set_track_info,
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
    def path_key(path: str) -> Tuple[str, str]:
        return get_artist(path), get_album(path)

    audio_paths = sorted(find_audio(*paths), key=path_key)

    for (artist, album), group_paths in groupby(audio_paths, key=path_key):
        group_paths = list(group_paths)

        # if all paths in a group are the only audio files in that directory,
        # move the entire directory
        commonpath = os.path.commonpath(group_paths)
        commonpath_audio_paths = set(find_audio(commonpath))
        if os.path.isdir(commonpath) and commonpath_audio_paths == set(group_paths):
            logger.debug("Canonicalizing commonpath %r", commonpath)
            # relativize each path in group to commonpath, so that we can later rejoin
            # to the canonicalized commonpath, which might or might not be different,
            # depending on the existing file structure and dry_run setting.
            group_relpaths = [os.path.relpath(path, commonpath) for path in group_paths]
            new_commonpath = os.path.join(
                destination, sanitize(artist), sanitize(album)
            )
            commonpath = move(commonpath, new_commonpath, dry_run=dry_run)
            group_paths = [
                os.path.join(commonpath, relpath) for relpath in group_relpaths
            ]

        for path in group_paths:
            logger.debug("Canonicalizing %r", path)
            _, ext = os.path.splitext(os.path.basename(path))
            track_number, total_tracks = get_track_info(path)
            part_width = len(str(total_tracks))

            new_filepath = os.path.join(
                destination,
                sanitize(artist),
                sanitize(album),
                f"{track_number:0{part_width}}{ext}".lower(),
            )

            # move to destination
            path = move(path, new_filepath, dry_run=dry_run)
            # fix permissions on files
            chmod(path, 0o644, dry_run=dry_run)
            # fix track numbers in audio
            set_track_info(path, (track_number, total_tracks), dry_run=dry_run)
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
