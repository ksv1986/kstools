from typing import IO, Literal

from .core import FormatError, ImageParser, ImageSize, PreadStream, b2x

tiff_exts = ("tiff",)

# https://www.itu.int/itudoc/itu-t/com16/tiff-fx/docs/tiff6.pdf

ByteOrder = Literal["little", "big"]

ImageWidth: int = 256
"""The number of columns in the image, i.e., the number of pixels per row."""

ImageLength: int = 257
"""The number of rows of pixels in the image."""


def getint(data: bytes, order: ByteOrder) -> int:
    t = int.from_bytes(data[2:4], order)
    if t == 3:
        return int.from_bytes(data[8:10], order)
    if t == 4:
        return int.from_bytes(data[8:12], order)
    raise FormatError(f"Invalid type {b2x(data[2:4])} ({t})")


class TiffParser(ImageParser):
    def __init__(self, stream: IO[bytes]):
        self.stream = PreadStream(stream)

    def image_size_endian(self, order: ByteOrder) -> ImageSize:
        data = self.stream.pread(2, 6)
        if len(data) < 6:
            raise FormatError("EOF")

        magic = int.from_bytes(data[:2], order)
        if magic != 42:
            raise FormatError(f"Invalid TIFF magic {b2x(data[:2])}")

        idx = 0
        w = h = None
        data = data[2:6]
        offs = int.from_bytes(data, order)
        while offs:
            if offs & 3:
                raise FormatError(f"Invalid IFD#{idx} offset {b2x(data)} ({offs})")

            data = self.stream.pread(offs, 2)
            if len(data) < 2:
                raise FormatError("EOF")

            offs += 2
            nr = int.from_bytes(data, order)
            while nr > 0:
                data = self.stream.pread(offs, 12)
                if len(data) < 12:
                    raise FormatError("EOF")

                tag = int.from_bytes(data[:2], order)

                if tag == ImageLength:
                    h = getint(data, order)
                    if w is not None:
                        return ImageSize(w, h)

                if tag == ImageWidth:
                    w = getint(data, order)
                    if h is not None:
                        return ImageSize(w, h)

                nr -= 1
                offs += 12

            data = self.stream.pread(offs, 4)
            if len(data) < 4:
                raise FormatError("EOF")

            idx += 1
            offs = int.from_bytes(data, order)

        raise FormatError("Not found")

    def image_size(self) -> ImageSize:
        order = self.stream.pread(0, 2)
        if len(order) < 2:
            raise FormatError("EOF")

        if order == b"II":
            return self.image_size_endian("little")
        if order == b"MM":
            return self.image_size_endian("big")

        raise FormatError(f"Invalid byte order {b2x(order)}")


def tiff_image_size(stream: IO[bytes]) -> ImageSize:
    return TiffParser(stream).image_size()
