import logging
import sys
from pathlib import Path
from typing import Callable, NoReturn, Optional, Tuple

# Valid CUE file encodings
VALID_ENCODINGS = {
    "ascii",
    "UTF-8-SIG",
}

# Map to fix wrongly guessed encodings
ENCODING_MAP = {
    "MacCyrillic": "windows-1251",
}

# Logging helpers
L = logging.getLogger("kstools.cue")


def trace(msg: str, **kwargs) -> None:
    L.debug(msg, **kwargs)


def info(msg: str, **kwargs) -> None:
    L.info(msg, **kwargs)


def warn(msg: str, **kwargs) -> None:
    L.warn(msg, **kwargs)


def error(msg: str, **kwargs) -> None:
    L.error(msg, **kwargs)


def q(s: str) -> str:
    return f"'{s}'"


# Colored output
def green(msg: str) -> str:
    return "\x1b[32m" + msg + "\x1b[39m"


def yellow(msg: str) -> str:
    return "\x1b[33m" + msg + "\x1b[39m"


Y = yellow
G = green


def detect_encoding(data) -> str:
    try:
        from chardet import detect

        trace("using chardet")

        def _detect_encoding(data: bytes) -> str:
            e = detect(data)["encoding"]
            return ENCODING_MAP.get(e, e)

    except ModuleNotFoundError:
        warn("chardet module not found, cue file encoding could not be detected.")
        warn('Use "pip install chardet" to enable the feature.')

        def _detect_encoding(data: bytes) -> str:
            if data.startswith(b"\xef\xbb\xbf"):
                return "UTF-8-SIG"
            for i in data:
                if i > 0x7F:
                    return "mbcs" if sys.platform.startswith("win") else "utf-8"
            return "ascii"

    globals()["detect_encoding"] = _detect_encoding
    return detect_encoding(data)


def quote(s: str) -> str:
    return f'"{s}"'


def nop(s: str) -> str:
    return s


def get_string(line: str) -> Tuple[str, str]:
    """Returns string value and line remainder"""
    line = line.lstrip()
    if line[0] != '"':
        # simple case, unquoted string, no remainder
        return line, ""

    # CUE has no quote escaping
    # find second quote, return what's inside and line remainder
    end = line.find('"', 1)
    if end > 1:
        return line[1:end], line[end + 1 :].lstrip()
    return line[1:], ""


def get_token(line: str) -> Tuple[str, str]:
    """Returns next token and line remainder"""
    s = line.find(" ")
    if s < 0:
        return line, ""
    else:
        return line[:s], line[s + 1 :].lstrip()


def get_ts(line: str) -> Tuple[str, str]:
    return get_token(line)


def get_index(line: str) -> Tuple[int, str]:
    idx, line = get_token(line)
    return int(idx, 10), line


def njoin(line: str, next: str) -> str:
    """Join two strings with new line"""
    return "\n".join((line, next)) if line else next


class CueException(Exception):
    pass


Fn = Callable[[str], str]


class Track:
    performer = None
    songwriter = None
    title = None
    pregap = None
    postgap = None
    end = None
    flags = None
    isrc = None

    def __init__(self, index: int, ttype: str, file: str, ftype: str):
        self.index = index
        self.file = file
        self.ftype = ftype
        self.ttype = ttype
        self.rem = []
        self.indices = []

    def add_rem(self, rem: str, value: str, do_quote: bool = False) -> None:
        self.rem.append((rem, value, quote if do_quote else nop))

    def njoin_map(self, content: str, ind: str, op: Fn, *names: str) -> str:
        for name in names:
            val = getattr(self, name.lower(), None)
            if not val:
                continue
            content = njoin(content, f"{ind}{name} {op(val)}")
        return content

    def njoin(self, content: str, ind: str, *names: str) -> str:
        return self.njoin_map(content, ind, nop, *names)

    def njoin_quote(self, content: str, ind: str, *names: str) -> str:
        return self.njoin_map(content, ind, quote, *names)

    def build(self) -> str:
        content = ""
        if self.file:
            content = njoin(content, f"FILE {quote(self.file)} {self.ftype}")
        ind = "  "
        content = njoin(content, f"{ind}TRACK {self.index:02d} {self.ttype}")
        ind = "    "
        content = self.njoin_quote(content, ind, "TITLE", "PERFORMER", "SONGWRITER")
        for rem, value, do_quote in self.rem:
            if do_quote:
                value = quote(value)
            content = njoin(content, f"{ind}REM {rem} {value}")
        content = self.njoin(content, ind, "FLAGS", "ISRC", "PREGAP")
        for i in self.indices:
            content = njoin(content, f"{ind}INDEX {i[0]:02d} {i[1]}")
        content = self.njoin(content, ind, "POSTGAP")
        return content


FILE_TYPES = {
    "AIFF",
    "BINARY",
    "FLAC",
    "MOTOROLA",
    "MP3",
    "WAVE",
}

TRACK_TYPES = {
    "AUDIO",  # Audio/Music (2352 — 588 samples)
    "CDG",  # Karaoke CD+G (2448)
    "MODE1/2048",  # CD-ROM Mode 1 Data (cooked)
    "MODE1/2352",  # CD-ROM Mode 1 Data (raw)
    "MODE2/2048",  # CD-ROM XA Mode 2 Data (form 1) *
    "MODE2/2324",  # CD-ROM XA Mode 2 Data (form 2) *
    "MODE2/2336",  # CD-ROM XA Mode 2 Data (form mix)
    "MODE2/2352",  # CD-ROM XA Mode 2 Data (raw)
    "CDI/2336",  # CDI Mode 2 Data
    "CDI/2352",  # CDI Mode 2 Data
}


class Cue:
    valid = True
    can_fix = False
    path = None
    file = None
    ftype = None
    nr_files = 0
    performer = None
    composer = None
    genre = None
    title = None
    date = None
    comment = None
    i = 0
    errors = 0

    def pre(self) -> str:
        return f"{Y(self.path)}:{self.i}: "

    def trace(self, message: str) -> None:
        trace(self.pre() + message)

    def warn(self, message: str) -> None:
        warn(self.pre() + message)

    def err(self, message: str) -> None:
        self.warn(message)
        self.errors += 1
        self.valid = False

    def throw(self, message) -> NoReturn:
        raise CueException(self.pre() + message)

    def current(self) -> Optional[Track]:
        return self.tracks[-1] if self.tracks else None

    def set_end(self, ts) -> None:
        prev = self.tracks[-2] if len(self.tracks) > 1 else None
        if prev and not prev.end:
            prev.end = ts

    def check_empty(self, line: str, tag: str) -> None:
        if line:
            self.err(f"unused content after {tag} statement")

    def check_track(self, tag: str) -> None:
        if not self.current():
            self.throw(f"{tag} outside TRACK definition")

    def parse_tag(self, line: str, tag: str) -> None:
        attr = tag.lower()
        value, line = get_string(line)
        if self.current():
            setattr(self.current(), attr, value)
        else:
            setattr(self, attr, value)
            self.header.append(f"{tag} {quote(value)}")
        self.check_empty(line, tag)

    def parse_TITLE(self, line: str, tag: str) -> None:
        self.parse_tag(line, tag)

    def parse_PERFORMER(self, line: str, tag: str) -> None:
        self.parse_tag(line, tag)

    def parse_FILE(self, line: str, tag: str) -> None:
        file, line = get_string(line)
        ftype, line = get_token(line)
        if ftype not in FILE_TYPES:
            return self.err(f"unknown FILE type '{ftype}'")
        if self.current() and not self.current().file:
            self.current().file = file
            self.current().ftype = ftype
        else:
            self.file = file
            self.ftype = ftype
        self.nr_files += 1

    def parse_TRACK(self, line: str, tag: str) -> None:
        index, line = get_index(line)
        ttype, line = get_token(line)
        self.check_empty(line, tag)

        if not index:
            self.throw("TRACK has no index")
        for t in self.tracks:
            if t.index == index:
                self.err(f"duplicate TRACK index {index}")
                break
        if ttype not in TRACK_TYPES:
            self.throw(f"unknown TRACK type '{ttype}'")

        track = Track(index, ttype, self.file, self.ftype)
        self.tracks.append(track)
        if track.index != len(self.tracks):
            msg = f"unexpected TRACK index {index:02d}, expected {len(self.tracks):02d}"
            self.err(msg)

        self.file = None
        self.ftype = None

    def parse_INDEX(self, line: str, tag: str) -> None:
        index, line = get_index(line)
        ts, line = get_ts(line)
        self.check_empty(line, tag)
        self.check_track(tag)
        self.current().indices.append((index, ts))
        self.set_end(ts)

    def parse_PREGAP(self, line: str, tag: str) -> None:
        ts, line = get_ts(line)
        self.check_empty(line, tag)
        self.check_track(tag)
        self.current().pregap = ts

    def parse_SONGWRITER(self, line: str, tag: str) -> None:
        self.check_track(tag)
        self.parse_tag(line, tag)

    def parse_FLAGS(self, line: str, tag: str) -> None:
        self.check_track(tag)
        self.current().flags = line

    def parse_ISRC(self, line: str, tag: str) -> None:
        self.check_track(tag)
        self.current().isrc = line

    def parse_CATALOG(self, line: str, tag: str) -> None:
        self.header.append(f"CATALOG {line}")

    # REM
    def rem_check_empty(self, line: str, rem: str) -> None:
        return self.check_empty(line, f"REM {rem}")

    def rem_check_is_global(self, rem: str) -> None:
        if self.current():
            self.err(f"REM {rem} must be global")

    def rem_get_string(self, line: str, rem: str) -> Tuple[bool, str]:
        is_quoted = line[0] == '"'
        value, line = get_string(line)
        self.rem_check_empty(line, rem)
        return is_quoted, value

    def rem_string(self, line: str, rem: str) -> None:
        attr = rem.lower()
        is_quoted, value = self.rem_get_string(line, rem)
        if self.current():
            return self.current().add_rem(rem, value, is_quoted)

        if hasattr(self, attr):
            setattr(self, attr, value)
        if is_quoted:
            value = quote(value)
        self.header.append(f"REM {rem} {value}")

    def rem_DISCID(self, line: str, rem: str) -> None:
        self.rem_check_is_global(rem)
        is_quoted, value = self.rem_get_string(line, rem)
        if is_quoted:
            value = quote(value)
        self.header.append(f"REM {rem} {value}")

    def parse_REM(self, line: str, tag: str) -> None:
        rem, line = get_token(line)
        if rem == "DISCID":
            self.rem_DISCID(line, rem)
        else:
            self.rem_string(line, rem)

    def parse_line(self, i: int, line: str) -> None:
        self.i = i
        if not line:
            return

        ind = 0
        while line[0] == " ":
            ind += 1
            line = line[1:]

        if not line:
            return

        token, line = get_token(line)
        parse_token = getattr(self, "parse_" + token, None)
        if parse_token:
            parse_token(line, token)
        else:
            self.err(f"unknown token '{token}'")

    def update(self, attr: str, value: str, rem=False, do_quote=False) -> None:
        setattr(self, attr, value)
        attr = attr.upper()
        if rem:
            attr = "REM " + attr
        if do_quote:
            value = quote(value)
        for i, h in enumerate(self.headers):
            if h.startswith(attr):
                self.headers[i] = f"{attr} {value}"
                break
        else:
            self.headers.append(f"{attr} {value}")

    def rem_update(self, attr: str, value: str, do_quote=False) -> None:
        self.update(attr, value, rem=True, do_quote=do_quote)

    def compare(self, content: str) -> Tuple[int, str]:
        self.warn(f" errors: {self.errors}")
        content = content.splitlines()
        build = self.build().splitlines()

        n = max(len(content), len(build))
        while len(content) < n:
            content.append("")
        while len(build) < n:
            build.append("")

        out = ""
        any = 0
        for i in range(0, n):
            left = content[i]
            right = build[i]
            line = f"{content[i]:100s} | {build[i]}"
            if left.strip() != right.strip():
                out = njoin(out, f"{i:02d}:{Y(line)}")
                any += 1
            else:
                out = njoin(out, f"{i:02d}:{line}")
        out = njoin(out, "")
        return any, out

    def build(self) -> str:
        """Construct CUE file contents from parsed parts"""
        content = "\n".join(self.header)
        for track in self.tracks:
            content = "\n".join((content, track.build()))
        return content

    def utf8(self) -> bytes:
        """Construct CUE file contents from parsed parts in UTF-8 encoding"""
        return self.build().encode("UTF-8-SIG")

    def files(self) -> list[str]:
        """List of files referenced by CUE"""
        return [x.file for x in self.tracks if x.file]

    def __init__(self, path: str, data: bytes = None):
        """Parse CUE file data and return True if no problems found"""
        self.path = path
        self.header = []
        self.tracks = []

        if data is None:
            data = Path(path).read_bytes()

        if not data:
            self.warn("empty file")
            self.valid = False
            return

        e = detect_encoding(data)
        if e not in VALID_ENCODINGS:
            self.warn(f"Invalid encoding {Y(e)}")
            self.valid = False
            self.can_fix = True

        content = data.decode(e)
        try:
            for i, line in enumerate(content.splitlines()):
                line = line.strip()
                self.parse_line(i, line)
        except CueException as e:
            self.warn(e)

        self.trace(f"valid={self.valid} can_fix={self.can_fix} errors={self.errors}")
        self.trace(f"tracks={len(self.tracks)} files={len(self.files())}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    print(Cue(sys.argv[1]).build())
