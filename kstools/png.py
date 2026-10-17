from struct import Struct
from typing import IO

from .core import FormatError, ImageParser, ImageSize, PreadStream, b2x

CHUNK = Struct(">I4s")
IHDR = Struct(">IIBBBBB")
PNG = b"\x89PNG\x0d\x0a\x1a\x0a"


png_exts = ("png",)


class PngParser(ImageParser):
    def __init__(self, stream: IO[bytes]):
        self.stream = PreadStream(stream)

    def image_size(self) -> ImageSize:
        data_len = len(PNG) + CHUNK.size + IHDR.size
        data = self.stream.pread(0, data_len)
        if len(data) < data_len:
            raise FormatError("EOF")

        sig, chunk, ihdr = data[:8], data[8:16], data[16:]

        if sig != PNG:
            raise FormatError(f"Wrong PNG signature: {b2x(sig)}")

        size, text = CHUNK.unpack(chunk)
        if text != b"IHDR":
            raise FormatError(f"Wrong first chunk: {b2x(text)}")

        if size != IHDR.size:
            raise FormatError(f"Invalid IHDR size {size}")

        w, h = IHDR.unpack(ihdr)[:2]
        return ImageSize(w, h)


def png_image_size(stream: IO[bytes]) -> ImageSize:
    return PngParser(stream).image_size()
