from typing import IO, Tuple

from .types import ImageParser, ImageSize, ImageSizeResult, PreadStream, b2x

tiff_exts = ("tiff",)

# https://www.itu.int/itudoc/itu-t/com16/tiff-fx/docs/tiff6.pdf

ImageWidth: int = 256
"""The number of columns in the image, i.e., the number of pixels per row."""

ImageLength: int = 257
"""The number of rows of pixels in the image."""


def getint(data: bytes, order: str) -> Tuple[int, str]:
    t = int.from_bytes(data[2:4], order)
    if t == 3:
        return (int.from_bytes(data[8:10], order), None)
    if t == 4:
        return (int.from_bytes(data[8:12], order), None)
    return (0, f"Invalid type {b2x(data[2:4])} ({t})")


class TiffParser(ImageParser):
    def __init__(self, stream: IO[bytes]):
        self.stream = PreadStream(stream)

    def image_size_endian(self, order: str) -> ImageSizeResult:
        data = self.stream.pread(2, 6)
        if len(data) < 6:
            return (None, "EOF")

        magic = int.from_bytes(data[:2], order)
        if magic != 42:
            return (None, f"Invalid TIFF magic {b2x(data[:2])}")

        idx = 0
        w = h = None
        data = data[2:6]
        offs = int.from_bytes(data, order)
        while offs:
            if offs & 3:
                return (None, f"Invalid IFD#{idx} offset {b2x(data)} ({offs})")

            data = self.stream.pread(offs, 2)
            if len(data) < 2:
                return (None, "EOF")

            offs += 2
            nr = int.from_bytes(data, order)
            while nr > 0:
                data = self.stream.pread(offs, 12)
                if len(data) < 12:
                    return (None, "EOF")

                tag = int.from_bytes(data[:2], order)

                if tag == ImageLength:
                    h, err = getint(data, order)
                    if err:
                        return (None, err)
                    if w is not None:
                        return (ImageSize(w, h), None)

                if tag == ImageWidth:
                    w, err = getint(data, order)
                    if err:
                        return (None, err)
                    if h is not None:
                        return (ImageSize(w, h), None)

                nr -= 1
                offs += 12

            data = self.stream.pread(offs, 4)
            if len(data) < 4:
                return (None, "EOF")

            idx += 1
            offs = int.from_bytes(data, order)

        return (None, "Not found")

    def image_size(self) -> ImageSizeResult:
        order = self.stream.pread(0, 2)
        if len(order) < 2:
            return (None, "EOF")

        if order == b"II":
            return self.image_size_endian("little")
        if order == b"MM":
            return self.image_size_endian("big")

        return (None, f"Invalid byte order {b2x(order)}")


def tiff_image_size(stream: IO[bytes]) -> ImageSizeResult:
    return TiffParser(stream).image_size()
