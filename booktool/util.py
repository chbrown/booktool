import os
import re
import logging
import unicodedata
from string import punctuation

logger = logging.getLogger(__name__)


def is_sanitized(string: str) -> bool:
    return re.fullmatch(r"[0-9A-Za-z][-0-9A-Za-z_]+[0-9A-Za-z]", string)


def sanitize(string: str) -> str:
    # remove accents (Mn = Modifier Letter)
    string = "".join(
        char
        for char in unicodedata.normalize("NFKD", string)
        if unicodedata.category(char) != "Mn"
    )
    # remove periods after initials; ensure a space follows
    string = re.sub(r"\b([A-Z])(\. ?| )", r"\1 ", string)
    # spell out ampersands / plus signs
    string = re.sub(r"\s*[&+]\s*", r" and ", string)
    # spell out at-sign
    string = re.sub(r"\s*@\s*", r" at ", string)
    # collapse hyphenations and delete apostrophes that mark contractions
    string = re.sub(r"([A-Za-z])[-']([A-Za-z])", r"\1\2", string)
    # replace separator punctuation with a hyphen
    string = re.sub(r"\s*[!*./:;?]\s*", r"-", string)
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
    if not is_sanitized(string):
        raise ValueError(f"{string!r} failed sanitization")
    return string


def _gethome() -> str:
    home = os.getenv("HOME")
    if home:
        return home
    import pwd  # pylint: disable=import-outside-toplevel

    return pwd.getpwuid(os.getuid()).pw_dir


def relativize_path(path: str) -> str:
    """
    If `path` starts with the current working directory, replace that prefix with `.`.
    If it starts with the user's home path, replace that with the symbol `~`.
    """
    # prepare cwd and home (must check that cwd != home before using cwd)
    cwd = os.getcwd()
    home = _gethome()
    # try cwd
    if cwd != home and path.startswith(cwd):
        return os.curdir + path[len(cwd) :]
    # try home
    if path.startswith(home):
        return "~" + path[len(home) :]
    # return unchanged
    return path
