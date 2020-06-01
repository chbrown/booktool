from typing import NamedTuple, Optional
from functools import singledispatch
import logging
import os
import re

import mutagen
import mutagen.mp3
import mutagen.mp4

from booktool.audio import is_audio

logger = logging.getLogger(__name__)


class Part(NamedTuple):
    index: Optional[int] = None
    total: Optional[int] = None

    @classmethod
    def from_path(cls, path: str):
        dirname, basename = os.path.split(path)
        total = len(list(filter(is_audio, os.listdir(dirname))))
        root, _ = os.path.splitext(basename)
        match = re.search(r"\d+", root)
        index = int(match.group(0)) if match else None
        return cls(index, total)

    @classmethod
    def from_string(cls, string: str):
        split_at = string.find("/")
        index_string, total_string = (
            (string[:split_at], string[split_at + 1 :])
            if split_at != -1
            else (string, "")
        )
        index = int(index_string) if index_string else None
        total = int(total_string) if total_string else None
        return cls(index, total)

    def merge(self, other: "Part", raise_on_conflicts: bool = True) -> "Part":
        # prefer `self` to `other` (treating 0's like None's)
        index = self.index or other.index
        total = self.total or other.total
        # check for conflicts
        if raise_on_conflicts:
            if other.index and index != other.index:
                raise ValueError(
                    f"Cannot merge with conflicts (index): {index} ≠ {other.index}"
                )
            if other.total and total != other.total:
                raise ValueError(
                    f"Cannot merge with conflicts (total): {total} ≠ {other.total}"
                )
        return Part(index, total)


###########################
# get_track dispatch


@singledispatch
def get_track(file, ignore_conflicts: bool = False) -> Part:
    """
    Read tuple of (index, total) from file.
    1. Read it from the metadata
    2. Infer it from filesystem (filename and other audio files in directory)
    Unless ignore_conflicts is True, raise a ValueError if these two sources conflict.
    """
    raise NotImplementedError(f"get_track not implemented for file: {file}")


@get_track.register
def get_track_str(file: str, ignore_conflicts: bool = False) -> Part:
    file = mutagen.File(file)
    return get_track(file, ignore_conflicts)


@get_track.register
def get_track_mp3(file: mutagen.mp3.MP3, ignore_conflicts: bool = False) -> Part:
    logger.debug("Opened %r as MP3", file.filename)
    metadata = Part.from_string(str(file.tags.get("TRCK", "")))
    filesystem = Part.from_path(file.filename)
    # merge, prefering metadata when available, checking for conflicts if specified
    part = metadata.merge(filesystem, not ignore_conflicts)
    # check for validity
    if part.index is None or part.total is None:
        raise ValueError(
            f"Cannot read/infer Part from metadata/filesystem for {file.filename}"
        )
    return part


@get_track.register
def get_track_mp4(file: mutagen.mp4.MP4, ignore_conflicts: bool = False) -> Part:
    logger.debug("Opened %r as MP4", file.filename)
    # lots of my files seem to come with (0, 0) as the default, which iTunes treats as if missing
    trkn, *trkns = file.tags.get("trkn", []) or [(0, 0)]
    # not sure when having more than one "trkn" tags might come up :|
    if trkns:
        raise ValueError("Too many trkn tags")
    # seems like trkn items are always 2-tuples?
    metadata = Part(*trkn)
    filesystem = Part.from_path(file.filename)
    # merge, prefering metadata when available, checking for conflicts if specified
    part = metadata.merge(filesystem, not ignore_conflicts)
    # check for validity
    if part.index is None or part.total is None:
        raise ValueError(
            f"Cannot read/infer Part from metadata/filesystem for {file.filename}"
        )
    return part


###########################
# set_track dispatch


@singledispatch
def set_track(file, part: Part, dry_run: bool = False):
    raise NotImplementedError(f"set_track not implemented for file: {file}")


@set_track.register
def set_track_str(file: str, part: Part, dry_run: bool = False):
    file = mutagen.File(file)
    return set_track(file, part, dry_run=dry_run)


@set_track.register
def set_track_mp3(file: mutagen.mp3.MP3, part: Part, dry_run: bool = False):
    logger.debug("Opened %r as MP3", file.filename)

    logger.debug("Manipulating ID3 version %s", ".".join(map(str, file.tags.version)))

    index, total = part
    TRCK = mutagen.id3.TRCK(encoding=0, text=f"{index}/{total}")

    existing_TRCK = file.tags.get("TRCK")
    if existing_TRCK:
        logger.debug("Already has TRCK tag: %r", existing_TRCK)
        if existing_TRCK == TRCK:
            return

    logger.info("Saving new TRCK tag %r to file: %s", TRCK, file.filename)
    file.tags.add(TRCK)
    major, minor = file.tags.version[:2]
    if major < 2:
        logger.info("Upgrading unsupported ID3 version %s.%s -> 2.3", major, minor)
        major, minor = 2, 3
    if minor < 3:
        logger.info("Upgrading unsupported ID3 version 2.%s -> 2.3", minor)
        minor = 3
        # otherwise, mutagen raises a ValueError: "Only 3 or 4 allowed for v2_version"
    if not dry_run:
        file.save(v2_version=minor)


@set_track.register
def set_track_mp4(file: mutagen.mp4.MP4, part: Part, dry_run: bool = False):
    logger.debug("Opened %r as MP4", file.filename)

    existing_trkn = file.tags.get("trkn", [])
    if len(existing_trkn) > 1:
        raise ValueError("Too many trkn tags")

    trkn = [tuple(part)]
    if existing_trkn:
        logger.debug("Already has trkn tags: %r", existing_trkn)
        if existing_trkn == trkn:
            return

    logger.info("Saving new trkn tags %r to file: %s", trkn, file.filename)
    file.tags["trkn"] = trkn
    if not dry_run:
        file.save()


####################
# get_disc dispatch


@singledispatch
def get_disc(file) -> Part:
    raise NotImplementedError(f"get_disc not implemented for file: {file}")


@get_disc.register
def get_disc_str(file: str) -> Part:
    file = mutagen.File(file)
    return get_disc(file)


@get_disc.register
def get_disc_mp3(file: mutagen.mp3.MP3) -> Part:
    logger.debug("Opened %r as MP3", file.filename)
    return Part.from_string(str(file.tags.get("TPOS", "")))


@get_disc.register
def get_disc_mp4(file: mutagen.mp4.MP4) -> Part:
    logger.debug("Opened %r as MP4", file.filename)
    disk, = file.tags.get("disk", [(0, 0)])
    return Part(*disk)


####################
# del_disc dispatch


@singledispatch
def del_disc(file, dry_run: bool = False):
    raise NotImplementedError(f"del_disc not implemented for file: {file}")


@del_disc.register
def del_disc_str(file: str, dry_run: bool = False):
    file = mutagen.File(file)
    return del_disc(file)


@del_disc.register
def del_disc_mp3(file: mutagen.mp3.MP3, dry_run: bool = False):
    logger.debug("Opened %r as MP3", file.filename)
    file.tags.delall("TPOS")
    if not dry_run:
        file.save()


@del_disc.register
def del_disc_mp4(file: mutagen.mp4.MP4, dry_run: bool = False):
    logger.debug("Opened %r as MP4", file.filename)
    file.tags.delall("disk")
    if not dry_run:
        file.save()


#####################
# get_artist dispatch


@singledispatch
def get_artist(file) -> str:
    raise NotImplementedError(f"get_artist not implemented for file: {file}")


@get_artist.register
def get_artist_str(file: str) -> str:
    file = mutagen.File(file)
    return get_artist(file)


@get_artist.register
def get_artist_mp3(file: mutagen.mp3.MP3) -> str:
    logger.debug("Opened %r as MP3", file.filename)
    # the id3.TextFrame instance returned by id3.ID3.get stringifies nicely
    text = str(file.tags.get("TPE1"))
    # get the first name
    return next(iter(text.split("/")))


@get_artist.register
def get_artist_mp4(file: mutagen.mp4.MP4) -> str:
    logger.debug("Opened %r as MP4", file.filename)
    # MP4Tags.get returns a list of strings
    return next(iter(file.tags.get("©ART")))


####################
# get_album dispatch


@singledispatch
def get_album(file) -> str:
    raise NotImplementedError(f"get_album not implemented for file: {file}")


@get_album.register
def get_album_str(file: str) -> str:
    file = mutagen.File(file)
    return get_album(file)


@get_album.register
def get_album_mp3(file: mutagen.mp3.MP3) -> str:
    logger.debug("Opened %r as MP3", file.filename)
    return str(file.tags.get("TALB"))


@get_album.register
def get_album_mp4(file: mutagen.mp4.MP4) -> str:
    logger.debug("Opened %r as MP4", file.filename)
    return " ".join(file.tags.get("©alb"))


def get_duration(file: str) -> float:
    logger.debug("Reading duration of file: %s", file)
    file = mutagen.File(file)
    return file.info.length
