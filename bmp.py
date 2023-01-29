from struct import Struct
from typing import IO

from .types import ImageParser, ImageSize, ImageSizeResult, PreadStream, b2x

bmp_exts = ("bmp", "dib")


HEADER = Struct("<2sIHHI")
OS2HDR = Struct("<IHHHH")
WINHDR = Struct("<III")
WINIDS = (b"BM",)
OS2IDS = (b"BA", b"CI", b"CP", b"IC", b"PT")


class BmpParser(ImageParser):
    def __init__(self, stream: IO[bytes]):
        self.stream = PreadStream(stream)

    def image_size(self) -> ImageSizeResult:
        data = self.stream.pread(0, 26)
        if len(data) < 26:
            return (None, "EOF")

        sig = HEADER.unpack(data[:14])[0]
        if sig in WINIDS:
            w, h = WINHDR.unpack(data[14:])[1:3]
        elif sig in OS2IDS:
            w, h = OS2HDR.unpack(data[14:])[1:3]
        else:
            return (None, f"Unknown BMP type: {b2x(sig)}")

        return (ImageSize(w, h), None)


def bmp_image_size(stream: IO[bytes]) -> ImageSizeResult:
    return BmpParser(stream).image_size()
