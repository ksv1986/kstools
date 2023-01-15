from dataclasses import dataclass
from struct import Struct
from typing import IO

from .types import ImageSize, ImageSizeResult, PreadStream, b2x

CHUNK = Struct(">I4s")
IHDR = Struct(">IIBBBBB")
PNG = b"\x89PNG\x0D\x0A\x1A\x0A"


png_exts = ("png",)


@dataclass
class Chunk:
    offs: int
    size: int
    text: bytes

    @property
    def start(self) -> int:
        return self.offs + 8

    @property
    def end(self) -> int:
        return self.offs + self.size + 12


class PngParser:
    def __init__(self, stream: IO[bytes]):
        stream.seek(0, 2)
        self.end = stream.tell()
        self.stream = PreadStream(stream)

    def read_chunk(self, offs: int) -> Chunk:
        data = self.stream.pread(offs, CHUNK.size)
        if len(data) < CHUNK.size:
            return None
        return Chunk(offs, *CHUNK.unpack(data))

    def image_size(self) -> ImageSizeResult:
        sig = self.stream.pread(0, 8)
        if len(sig) < 8:
            return (None, "No signature")

        if sig != PNG:
            return (None, f"Wrong PNG signature {b2x(sig)}")

        c = self.read_chunk(8)
        if not c:
            return (None, "EOF")

        if c.text != b"IHDR":
            return (None, "No IHDR chunk")

        if c.size != IHDR.size:
            return (None, f"Invalid IHDR size {c.size}")

        data = self.stream.read(IHDR.size)
        if len(data) != IHDR.size:
            return (None, "EOF")

        w, h = IHDR.unpack(data)[:2]
        return (ImageSize(w, h), None)


def png_image_size(stream: IO[bytes]) -> ImageSizeResult:
    return PngParser(stream).image_size()
