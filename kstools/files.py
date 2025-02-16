from os import walk
from os.path import splitext


def lowerext(name: str) -> str:
    """Returns file extension in lower case"""
    e = splitext(name)[1].lower()
    return e[1:] if e else ""


def lowername(name: str) -> str:
    """Returns file name without extension in lower case"""
    return splitext(name)[0].lower()


def filelist(path: str, **kwargs) -> list[str]:
    """Returns list of files in given directory"""
    """  **kwargs will be passed to underlaying os.walk() call"""
    return next(walk(path, **kwargs))[2]
