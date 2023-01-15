from struct import Struct
from typing import IO

from .types import ImageSize, ImageSizeResult, PreadStream, b2x

CHUNK = Struct(">I4s")
IHDR = Struct(">IIBBBBB")
PNG = b"\x89PNG\x0D\x0A\x1A\x0A"


png_exts = ("png",)


class PngParser:
    def __init__(self, stream: IO[bytes]):
        self.stream = PreadStream(stream)

    def image_size(self) -> ImageSizeResult:
        data_len = len(PNG) + CHUNK.size + IHDR.size
        data = self.stream.pread(0, data_len)
        if len(data) < data_len:
            return (None, "EOF")

        sig, chunk, ihdr = data[:8], data[8:16], data[16:]

        if sig != PNG:
            return (None, f"Wrong PNG signature: {b2x(sig)}")

        size, text = CHUNK.unpack(chunk)
        if text != b"IHDR":
            return (None, f"Wrong first chunk: {b2x(text)}")

        if size != IHDR.size:
            return (None, f"Invalid IHDR size {size}")

        w, h = IHDR.unpack(ihdr)[:2]
        return (ImageSize(w, h), None)


def png_image_size(stream: IO[bytes]) -> ImageSizeResult:
    return PngParser(stream).image_size()
