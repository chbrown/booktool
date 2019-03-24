import os
import re
import logging
from string import punctuation

logger = logging.getLogger(__name__)


def is_sanitized(string: str) -> bool:
    return re.fullmatch(r"[0-9A-Za-z][-0-9A-Za-z_]+[0-9A-Za-z]", string)


def sanitize(string: str) -> str:
    # remove periods after initials; ensure a space follows
    string = re.sub(r"\b([A-Z])(\. ?| )", r"\1 ", string)
    # spell out ampersands / plus signs
    string = re.sub(r"\s*[&+]\s*", r" and ", string)
    # spell out at-sign
    string = re.sub(r"\s*@\s*", r" at ", string)
    # collapse hyphenations and delete apostrophes that mark contractions
    string = re.sub(r"([A-Za-z])[-']([A-Za-z])", r"\1\2", string)
    # replace separator punctuation with a hyphen
    string = re.sub(r"\s*[!.:;?]\s*", r"-", string)
    # replace parentheticals by separating with hyphen
    string = re.sub(r"\s*\(([^)]*)\)\s*", r"-\1-", string)
    string = re.sub(r"\s*\[([^]]*)\]\s*", r"-\1-", string)
    # replace any other remaining punctuation (within reason) with a space
    string = re.sub(r"""["$%',]""", r" ", string)
    # replace whitespace with underscore
    string = re.sub(r"\s+", r"_", string)
    # remove leading/trailing punctuation
    string = string.strip(punctuation)
    # done!
    assert is_sanitized(string), f"{string!r} failed sanitization"
    return string


def chmod(path: str, mode: int = 0o644, dry_run: bool = False):
    """
    Set the access permissions of the file/directory at `path` to `mode`.
    Checks first if the file's mode already matches the given mode, in which
    case it does nothing.
    """
    current_mode = os.stat(path).st_mode & 0o777
    # short-circuit if current mode matches
    if current_mode != mode:
        logger.info("%s: chmod %o -> %o", path, current_mode, mode)
        if not dry_run:
            os.chmod(path, mode)


def move(src: str, dst: str, dry_run: bool = False) -> str:
    """
    Move `src` to `dst`. If `src` and `dst` refer to the same path, do nothing.
    If they are different and `dst` already exists, raise a FileExistsError.
    """
    # short-circuit if src and dst refer to the same thing
    # os.path.samefile(src, dst) doesn't work because it calls os.stat on each argument
    if os.path.realpath(src) != os.path.realpath(dst):
        if os.path.exists(dst):
            raise FileExistsError(dst)
        logger.info("%s: move -> %s", src, dst)
        if not dry_run:
            os.renames(src, dst)
            return dst
    return src
