import logging
from functools import singledispatch

import mutagen
import mutagen.mp3
import mutagen.mp4

logger = logging.getLogger(__name__)


@singledispatch
def set_track_number(file, track_number: int, total_tracks: int):
    raise NotImplementedError(f"set_track_number not implemented for file: {file}")


@set_track_number.register
def set_track_number_str(file: str, track_number: int, total_tracks: int):
    file = mutagen.File(file)
    return set_track_number(file, track_number, total_tracks)


@set_track_number.register
def set_track_number_mp3(file: mutagen.mp3.MP3, track_number: int, total_tracks: int):
    logger.debug("Opened file as MP3")

    major, minor, patch = file.tags.version
    logger.debug("Manipulating ID3 version %s.%s.%s", major, minor, patch)
    assert major == 2, "ID3 version is not 2.*.*"

    TRCK = mutagen.id3.TRCK(encoding=0, text=f"{track_number}/{total_tracks}")

    existing_TRCK = file.tags.get("TRCK")
    if existing_TRCK:
        logger.info("Already has TRCK tag: %r", existing_TRCK)
        if existing_TRCK == TRCK:
            return

    logger.info("Setting TRCK tag: %r", TRCK)
    file.tags.add(TRCK)
    logger.debug("Saving file: %s", file.filename)
    file.save(v2_version=minor)


@set_track_number.register
def set_track_number_mp4(file: mutagen.mp4.MP4, track_number: int, total_tracks: int):
    logger.debug("Opened file as MP4")

    existing_trkn = file.tags.get("trkn", [])
    assert len(existing_trkn) < 2, "Too many trkn tags"

    trkn = [(track_number, total_tracks)]
    if existing_trkn:
        logger.info("Already has trkn tags: %r", existing_trkn)
        if existing_trkn == trkn:
            return

    logger.info("Setting trkn tags: %r", trkn)
    file.tags["trkn"] = trkn
    logger.debug("Saving file: %s", file.filename)
    file.save()


def get_duration(file: str) -> float:
    logger.debug("Reading duration of file: %s", file)
    file = mutagen.File(file)
    return file.info.length
