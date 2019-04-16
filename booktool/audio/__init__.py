from typing import Iterable, Iterator, List
import os

EXTENSIONS = (".mp3", ".mp4", ".m4a", ".m4b", ".m4p")


def is_audio(path: str) -> bool:
    return not path.startswith(".") and path.endswith(EXTENSIONS)


def find_audio(*paths: Iterable[str]) -> Iterator[str]:
    for path in paths:
        if os.path.isdir(path):
            for filename in os.listdir(path):
                yield from find_audio(os.path.join(path, filename))
        else:
            basename = os.path.basename(path)
            if is_audio(basename):
                yield os.path.normpath(path)
