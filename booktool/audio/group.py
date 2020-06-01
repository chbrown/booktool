from collections import Counter
from typing import List
import logging

from booktool.audio.track import (
    del_disc,
    get_disc,
    get_track,
    set_track,
)

logger = logging.getLogger(__name__)


def flatten_discs(paths: List[str], dry_run: bool = False):
    """
    Flatten multi-disc sets, if applicable. Checks that both the following apply:
    * each file has a disc and a track number
    * there's more than one disc represented
    If so:
    * each track number is incremented by the total number of tracks on preceding discs
    * the disc field is removed/zeroed out

    `paths` is assumed to be a group (each audio file has the same artist and album).
    """
    discs = list(map(get_disc, paths))
    disc_counts = Counter(disc.index for disc in discs)
    if (
        all(get_track(path, ignore_conflicts=True) for path in paths)
        and all(disc_counts)
        and len(disc_counts) > 1
    ):
        logger.debug("Canonicalizing disc set")
        disc_increments = {
            index: sum(count for i, count in disc_counts.items() if i < index)
            for index in disc_counts
        }
        for path in paths:
            track_disc, _ = get_disc(path)
            # discard existing number of tracks
            track_number, _ = get_track(path, ignore_conflicts=True)
            set_track(
                path,
                (track_number + disc_increments[track_disc], len(paths)),
                dry_run=dry_run,
            )
            # delete disc metadata
            del_disc(path, dry_run=dry_run)
