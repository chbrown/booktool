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
        track_number = int(re.search(r"\d+", root).group(0))
        return cls(track_number, total_tracks)

    @classmethod
    def from_string(cls, string: str):
        parts = list(map(int, string.split("/", maxsplit=1)))
        if len(parts) != 2:
            raise ValueError(f"Cannot create {cls.__name__} from string: {string!r}")
        return cls(*parts)


###########################
# get_track_info dispatch


@singledispatch
def get_track_info(file) -> TrackInfo:
    """
    Read tuple of (track_number, total_tracks) from file.
    1. Try to read it from the file's metadata; failing that:
    2. Infer it from filesystem
       * If the track_number inferred from the filename conflicts with the file's
       metadata, raise an AssertionError.
    """
    raise NotImplementedError(f"get_track_info not implemented for file: {file}")


@get_track_info.register
def get_track_info_str(file: str) -> TrackInfo:
    file = mutagen.File(file)
    return get_track_info(file)


@get_track_info.register
def get_track_info_mp3(file: mutagen.mp3.MP3) -> TrackInfo:
    logger.log(logging.NOTSET, "Reading file as MP3")
    text = str(file.tags.get("TRCK", ""))
    try:
        return TrackInfo.from_string(text)
    except Exception:
        track_number = TrackInfo.from_path(file.filename)
        assert (
            not text or int(text) == track_number.track_number
        ), "Metadata conflicts with filename"
        return track_number


@get_track_info.register
def get_track_info_mp4(file: mutagen.mp4.MP4) -> TrackInfo:
    logger.log(logging.NOTSET, "Reading file as MP4")
    # not sure when having more than one "trkn" tags might come up :|
    tags = file.tags.get("trkn", [])
    assert len(tags) < 2, "Too many trkn tags"
    if tags:
        tag = tags[0]
        assert len(tag) < 3, "Too many trkn tag parts"
        if len(tag) == 2:
            return TrackInfo(*tag)
    track_number = TrackInfo.from_path(file.filename)
    assert (
        not tags or int(tags[0][0]) == track_number.track_number
    ), "Metadata conflicts with filename"
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

    major, minor, patch = file.tags.version
    logger.debug("Manipulating ID3 version %s.%s.%s", major, minor, patch)
    assert major == 2, "ID3 version is not 2.*.*"

    track_number, total_tracks = track_info
    TRCK = mutagen.id3.TRCK(encoding=0, text=f"{track_number}/{total_tracks}")

    existing_TRCK = file.tags.get("TRCK")
    if existing_TRCK:
        logger.debug("Already has TRCK tag: %r", existing_TRCK)
        if existing_TRCK == TRCK:
            return

    logger.info("Saving new TRCK tag %r to file: %s", TRCK, file.filename)
    file.tags.add(TRCK)
    if not dry_run:
        file.save(v2_version=minor)


@set_track_info.register
def set_track_info_mp4(
    file: mutagen.mp4.MP4, track_info: TrackInfo, dry_run: bool = False
):
    logger.log(logging.NOTSET, "Opened file as MP4")

    existing_trkn = file.tags.get("trkn", [])
    assert len(existing_trkn) < 2, "Too many trkn tags"

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
