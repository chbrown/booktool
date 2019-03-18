EXTENSIONS = (".mp3", ".mp4", ".m4a", ".m4b", ".m4p")


def is_audio(path: str) -> bool:
    return not path.startswith(".") and path.endswith(EXTENSIONS)
