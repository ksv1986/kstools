from typing import IO, Tuple

from .isobmff import Box, BoxParser

Result = Tuple[str, str]


class MP4Parser(BoxParser):
    def __init__(self, stream: IO[bytes]):
        super().__init__(stream)

    def find_recursive(self, offs: int, *args: str) -> Tuple[Box, str]:
        end = self.end
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

        chain = ("moov", "trak", "mdia", "minf", "stbl", "stsd")
        b, err = self.find_recursive(b.end, *chain)
        if err:
            return (None, err)

        if b.size < 8 + 8:
            return (None, f"stsd atom size={b.size} is too small")

        cc = self.stream.pread(b.start + 8 + 4, 4)
        return (cc, None)


def get_mp4_codec(stream: IO[bytes]) -> Result:
    return MP4Parser(stream).get_codec()


if __name__ == "__main__":
    import sys

    with open(sys.argv[1], "rb") as f:
        cc, err = get_mp4_codec(f)
    if err:
        print(err, file=sys.stderr)
    else:
        print(cc.decode("ascii", errors="replace"))
