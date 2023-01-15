from struct import Struct
from typing import IO

from .types import ImageSize, ImageSizeResult, PreadStream, b2x

GIF87 = b"GIF87a"
GIF89 = b"GIF89a"
GIFS = (GIF87, GIF89)
WH = Struct("<HH")


gif_exts = ("gif",)


class GifParser:
    def __init__(self, stream: IO[bytes]):
        self.stream = PreadStream(stream)

    def image_size(self) -> ImageSizeResult:
        data = self.stream.pread(0, 10)
        if len(data) < 10:
            return (None, "EOF")

        sig, wh = data[:6], data[6:]

        if sig not in GIFS:
            return (None, f"Wrong GIF signature {b2x(sig)}")

        w, h = WH.unpack(wh)
        return (ImageSize(w, h), None)


def gif_image_size(stream: IO[bytes]) -> ImageSizeResult:
    return GifParser(stream).image_size()
