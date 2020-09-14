__version__ = None

try:
    import pkg_resources

    __version__ = pkg_resources.get_distribution("booktool").version
except Exception:
    pass


# 3 digits, optional, followed by 9 digits, followed by a digit or "X"
ISBN_PATTERN = r"^(\d{3})?\d{9}[0-9X]$"


def isbn13to10(isbn13: str) -> str:
    """
    Convert ISBN-13 to ISBN-10 (without checking validity of input).
    """
    isbn9 = isbn13[3:12]
    # for the checksum, isbn9 is zipped with [10, 9, ... 2]
    weights = range(10, 1, -1)
    checksum: int = sum(weight * int(digit) for weight, digit in zip(weights, isbn9))
    checkdigit: int = 11 - (checksum % 11)
    checkdigit_str: str = "X" if checkdigit == 10 else str(checkdigit)
    return isbn9 + checkdigit_str
