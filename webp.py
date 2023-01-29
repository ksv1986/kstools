from struct import Struct
from typing import IO

from .types import ImageParser, ImageSize, ImageSizeResult, PreadStream, b2x, le16

webp_exts = ("webp",)

CHUNK = Struct("<4sI")


def le24(data: bytes) -> int:
    return int.from_bytes(data[:3], "little")


# https://datatracker.ietf.org/doc/html/draft-zern-webp
class WebpParser(ImageParser):
    def __init__(self, stream: IO[bytes]):
        self.stream = PreadStream(stream)

    def image_size(self) -> ImageSizeResult:
        data = self.stream.pread(0, 12)
        if len(data) < 12:
            return (None, "Empty file")
        cc, sz = CHUNK.unpack(data[: CHUNK.size])
        if cc != b"RIFF":
            return (None, f"Invalid file fourcc {b2x(cc)}")
        if sz < 4:
            return (None, f"Too small file size {sz}")
        cc = data[8:]
        if cc != b"WEBP":
            return (None, f"Invalid first chunk fourcc {b2x(cc)}")
        data = self.stream.read(CHUNK.size)
        if len(data) < CHUNK.size:
            return (None, f"Unexpected EOF at {self.stream.offs}")
        cc, sz = CHUNK.unpack(data)
        if cc == b"VP8X":
            data = self.stream.pread(12 + 8 + 4, 6)
            if len(data) < 6:
                return (None, f"Unexpected EOF at {self.stream.offs}")
            w, h = le24(data) + 1, le24(data[3:]) + 1
        elif cc == b"VP8 ":
            # https://www.rfc-editor.org/rfc/rfc6386.txt
            data = self.stream.pread(12 + 8 + 3, 3 + 4)
            code, data = data[:3], data[3:]
            if code != b"\x9D\x01\x2A":
                return (None, f"Invalid VP8 start code {b2x(code)}")
            w, h = le16(data) & 0x3FFF, le16(data[2:]) & 0x3FFF
        elif cc == b"VP8L":
            data = self.stream.pread(12 + 8 + 4, 5)
            if len(data) < 6:
                return (None, f"Unexpected EOF at {self.stream.offs}")
            if data[0] != b"\x2F":
                return (None, f"Invalid VP8L signature byte {b2x(data[0])}")
            # w and h are 14 bits little endian
            i = int.from_bytes(data[1:5], "little") >> 4
            m = (1 << 14) - 1
            w, h = (i >> 14) + 1, (i & m) + 1
        else:
            return (None, f"Unknown chunk {b2x(cc)}")

        return (ImageSize(w, h), None)


def webp_image_size(stream: IO[bytes]) -> ImageSizeResult:
    return WebpParser(stream).image_size()
