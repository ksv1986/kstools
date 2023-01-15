from typing import IO

from .types import ImageSize, ImageSizeResult, PreadStream, b2x, le16

GIF87 = b"GIF87a"
GIF89 = b"GIF89a"
GIFS = (GIF87, GIF89)

gif_exts = ("gif",)


class GifParser:
    def __init__(self, stream: IO[bytes]):
        self.stream = PreadStream(stream)

    def image_size(self) -> ImageSizeResult:
        data = self.stream.pread(0, 10)
        if len(data) < 10:
            return (None, "EOF")

        sig = data[:6]
        if sig not in GIFS:
            return (None, f"Wrong GIF signature {b2x(sig)}")

        w = le16(data[6:8])
        h = le16(data[8:10])
        return (ImageSize(w, h), None)


def gif_image_size(stream: IO[bytes]) -> ImageSizeResult:
    return GifParser(stream).image_size()
