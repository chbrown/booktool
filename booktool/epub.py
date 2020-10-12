from pathlib import Path
import os
import zipfile

from filesystemlib.errors import file_not_found, not_a_directory

MIMETYPE = "application/epub+zip"


def compress(source: Path, target: Path, mode: str = "x"):
    """
    Zip up the EPUB file structure at `source` and write the resulting zip file to `target`.

    The `mode` option controls how the `target` file is opened; use "w" to clobber.
    """
    # various checks
    if not source.is_dir():
        raise not_a_directory(source)
    mimetype_path = source / "mimetype"
    if mimetype_path.read_text() != MIMETYPE:
        raise ValueError(f"{mimetype_path} does not consist of {MIMETYPE!r}")
    container_path = source / "META-INF" / "container.xml"
    if not container_path.exists():
        raise file_not_found(container_path)
    # okay, done with checks
    with zipfile.ZipFile(target, mode=mode, compression=zipfile.ZIP_DEFLATED) as zf:
        # The `mimetype` file is special:
        # it must be the first file in the archive, and should not be compressed
        zf.write(mimetype_path, "mimetype", compress_type=zipfile.ZIP_STORED)
        for dirpath, _, filenames in os.walk(source):
            for filename in filenames:
                if filename != "mimetype":
                    filepath = os.path.join(dirpath, filename)
                    arcname = os.path.relpath(filepath, source)
                    zf.write(filepath, arcname)
    # TODO: set time like `zip -o|--latest-time ...`, which uses the the oldest mtime
    # of the files the zip archive contains. For now, simply copy filesystem timestamps
    # from source to target:
    source_st = source.stat()
    os.utime(target, ns=(source_st.st_atime_ns, source_st.st_mtime_ns))


def decompress(source: Path, target: Path):
    """
    Unpack the zipped EPUB file at `source` into file structure at `target`.

    Clobbers by default.
    Doesn't remove extraneous files in `target` that are missing from `source`.
    """
    with zipfile.ZipFile(source) as zf:
        zf.extractall(path=target)
