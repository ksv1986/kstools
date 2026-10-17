from struct import Struct
from typing import IO

from .core import FormatError, ImageParser, ImageSize, PreadStream, b2x

bmp_exts = ("bmp", "dib")


HEADER = Struct("<2sIHHI")
OS2HDR = Struct("<IHHHH")
WINHDR = Struct("<III")
WINIDS = (b"BM",)
OS2IDS = (b"BA", b"CI", b"CP", b"IC", b"PT")


class BmpParser(ImageParser):
    def __init__(self, stream: IO[bytes]):
        self.stream = PreadStream(stream)

    def image_size(self) -> ImageSize:
        data = self.stream.pread(0, 26)
        if len(data) < 26:
            raise FormatError("EOF")

        sig = HEADER.unpack(data[:14])[0]
        if sig in WINIDS:
            w, h = WINHDR.unpack(data[14:])[1:3]
        elif sig in OS2IDS:
            w, h = OS2HDR.unpack(data[14:])[1:3]
        else:
            raise FormatError(f"Unknown BMP type: {b2x(sig)}")

        return ImageSize(w, h)


def bmp_image_size(stream: IO[bytes]) -> ImageSize:
    return BmpParser(stream).image_size()
