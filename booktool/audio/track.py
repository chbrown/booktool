from typing import NamedTuple
from functools import singledispatch
import logging
import os
import re

import mutagen
import mutagen.mp3
import mutagen.mp4

from booktool.audio import is_audio

logger = logging.getLogger(__name__)


class TrackInfo(NamedTuple):
    track_number: int
    total_tracks: int

    @classmethod
    def from_path(cls, path: str):
        dirname, basename = os.path.split(path)
        total_tracks = len(list(filter(is_audio, os.listdir(dirname))))
        root, _ = os.path.splitext(basename)
        match = re.search(r"\d+", root)
        if not match:
            raise ValueError(
                f"Cannot create {cls.__name__} from path: {path!r}; "
                "expected one or more digits in path stem"
            )
        track_number = int(match.group(0))
        return cls(track_number, total_tracks)

    @classmethod
    def from_string(cls, string: str):
        parts = list(map(int, string.split("/", maxsplit=1)))
        if len(parts) != 2:
            raise ValueError(
                f"Cannot create {cls.__name__} from string: {string!r}; "
                "expected two numbers separated by a '/'"
            )
        return cls(*parts)


###########################
# get_track_info dispatch


@singledispatch
def get_track_info(file, ignore_conflicts: bool = False) -> TrackInfo:
    """
    Read tuple of (track_number, total_tracks) from file.
    1. Try to read it from the file's metadata; failing that:
    2. Infer it from filesystem
       * If the track_number inferred from the filename conflicts with the file's
       metadata, raise a ValueError.
    """
    raise NotImplementedError(f"get_track_info not implemented for file: {file}")


@get_track_info.register
def get_track_info_str(file: str, ignore_conflicts: bool = False) -> TrackInfo:
    file = mutagen.File(file)
    return get_track_info(file, ignore_conflicts)


@get_track_info.register
def get_track_info_mp3(
    file: mutagen.mp3.MP3, ignore_conflicts: bool = False
) -> TrackInfo:
    logger.log(logging.NOTSET, "Reading file as MP3")
    text = str(file.tags.get("TRCK", ""))
    try:
        return TrackInfo.from_string(text)
    except Exception as exc:
        logger.debug("Unable to parse TRCK tag: %s", exc)
    track_number = TrackInfo.from_path(file.filename)
    if not ignore_conflicts and text and int(text) != track_number.track_number:
        raise ValueError(
            "Metadata conflicts with filename: "
            f"{int(text)} ≠ {track_number.track_number}"
        )
    return track_number


@get_track_info.register
def get_track_info_mp4(
    file: mutagen.mp4.MP4, ignore_conflicts: bool = False
) -> TrackInfo:
    logger.log(logging.NOTSET, "Reading file as MP4")
    # not sure when having more than one "trkn" tags might come up :|
    tags = file.tags.get("trkn", [])
    if len(tags) > 1:
        raise ValueError("Too many trkn tags")
    if tags:
        tag = tags[0]
        if len(tag) > 2:
            raise ValueError("Too many trkn tag parts")
        if len(tag) == 2:
            return TrackInfo(*tag)
    track_number = TrackInfo.from_path(file.filename)
    if not ignore_conflicts and tags and int(tags[0][0]) != track_number.track_number:
        raise ValueError("Metadata conflicts with filename")
    return track_number


###########################
# set_track_info dispatch


@singledispatch
def set_track_info(file, track_info: TrackInfo, dry_run: bool = False):
    raise NotImplementedError(f"set_track_info not implemented for file: {file}")


@set_track_info.register
def set_track_info_str(file: str, track_info: TrackInfo, dry_run: bool = False):
    file = mutagen.File(file)
    return set_track_info(file, track_info, dry_run=dry_run)


@set_track_info.register
def set_track_info_mp3(
    file: mutagen.mp3.MP3, track_info: TrackInfo, dry_run: bool = False
):
    logger.log(logging.NOTSET, "Opened file as MP3")

    logger.debug("Manipulating ID3 version %s", ".".join(map(str, file.tags.version)))

    track_number, total_tracks = track_info
    TRCK = mutagen.id3.TRCK(encoding=0, text=f"{track_number}/{total_tracks}")

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


@set_track_info.register
def set_track_info_mp4(
    file: mutagen.mp4.MP4, track_info: TrackInfo, dry_run: bool = False
):
    logger.log(logging.NOTSET, "Opened file as MP4")

    existing_trkn = file.tags.get("trkn", [])
    if len(existing_trkn) > 1:
        raise ValueError("Too many trkn tags")

    trkn = [tuple(track_info)]
    if existing_trkn:
        logger.debug("Already has trkn tags: %r", existing_trkn)
        if existing_trkn == trkn:
            return

    logger.info("Saving new trkn tags %r to file: %s", trkn, file.filename)
    file.tags["trkn"] = trkn
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
    logger.log(logging.NOTSET, "Reading file as MP3")
    # the id3.TextFrame instance returned by id3.ID3.get stringifies nicely
    text = str(file.tags.get("TPE1"))
    # get the first name
    return next(iter(text.split("/")))


@get_artist.register
def get_artist_mp4(file: mutagen.mp4.MP4) -> str:
    logger.log(logging.NOTSET, "Reading file as MP4")
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
    logger.log(logging.NOTSET, "Reading file as MP3")
    return str(file.tags.get("TALB"))


@get_album.register
def get_album_mp4(file: mutagen.mp4.MP4) -> str:
    logger.log(logging.NOTSET, "Reading file as MP4")
    return " ".join(file.tags.get("©alb"))


def get_duration(file: str) -> float:
    logger.debug("Reading duration of file: %s", file)
    file = mutagen.File(file)
    return file.info.length
