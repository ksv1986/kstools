from typing import IO

from .core import FormatError
from .isobmff import Box, BoxParser


class MP4Parser(BoxParser):
    def __init__(self, stream: IO[bytes]):
        super().__init__(stream)

    def find_recursive(self, offs: int, end: int, *args: str) -> Box | None:
        b = None
        for text in args:
            b = self.find_box(text.encode("ascii"), offs, end)
            if not b:
                return None
            offs = b.start
            end = b.end
        return b

    def get_codec(self) -> list[bytes]:
        b = self.read_box(0)
        if not b:
            raise FormatError("Empty file")

        if b.text != b"ftyp":
            raise FormatError("No ftyp box")

        moov = self.find_box(b"moov", b.end, self.end)
        if not moov:
            raise FormatError("No moov box")

        tracks = []
        err = "trak not found"
        offs = moov.start
        while trak := self.find_box(b"trak", offs, self.end):
            offs = trak.end

            chain = ("mdia", "minf", "stbl", "stsd")
            b = self.find_recursive(trak.start, trak.end, *chain)
            if not b:
                continue
            if b.size < 8 + 8:
                err = f"stsd atom size={b.size} is too small"
                continue

            cc = self.stream.pread(b.start + 8 + 4, 4)
            tracks.append(cc)

        if not tracks:
            raise FormatError(err)

        return tracks


def get_mp4_codec(stream: IO[bytes]) -> list[bytes]:
    return MP4Parser(stream).get_codec()


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        name = __file__.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
        print("Usage:", name, "<file.mp4>")
        sys.exit(1)

    with open(sys.argv[1], "rb") as f:
        try:
            cc = get_mp4_codec(f)
            for c in cc:
                print(c.decode("ascii", errors="replace"))
        except FormatError as err:
            print(err, file=sys.stderr)
