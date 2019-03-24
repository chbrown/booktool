import re
from string import punctuation


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
