from typing import IO

from .isobmff import Box, BoxParser

Result = tuple[list[str] | None, str | None]


class MP4Parser(BoxParser):
    def __init__(self, stream: IO[bytes]):
        super().__init__(stream)

    def find_recursive(self, offs: int, end: int, *args: str) -> tuple[Box, str]:
        b = None
        for text in args:
            b = self.find_box(text.encode("ascii"), offs, end)
            if not b:
                return (None, text + " not found")
            offs = b.start
            end = b.end
        return (b, None)

    def get_codec(self) -> Result:
        b = self.read_box(0)
        if not b:
            return (None, "Empty file")

        if b.text != b"ftyp":
            return (None, "No ftyp box")

        moov = self.find_box(b"moov", b.end, self.end)
        if not moov:
            return (None, "No moov box")

        tracks = []
        err = "trak not found"
        offs = moov.start
        while trak := self.find_box(b"trak", offs, self.end):
            offs = trak.end

            chain = ("mdia", "minf", "stbl", "stsd")
            b, err = self.find_recursive(trak.start, trak.end, *chain)
            if err:
                continue
            if b.size < 8 + 8:
                err = f"stsd atom size={b.size} is too small"
                continue

            cc = self.stream.pread(b.start + 8 + 4, 4)
            tracks.append(cc)
        if tracks:
            return tracks, None
        else:
            return None, err
        return tracks


def get_mp4_codec(stream: IO[bytes]) -> Result:
    return MP4Parser(stream).get_codec()


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        name = __file__.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
        print("Usage:", name, "<file.mp4>")
        sys.exit(1)

    with open(sys.argv[1], "rb") as f:
        cc, err = get_mp4_codec(f)
    if err:
        print(err, file=sys.stderr)
    else:
        for c in cc:
            print(c.decode("ascii", errors="replace"))
