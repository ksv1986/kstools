from dataclasses import dataclass
from struct import Struct
from typing import IO

from .core import FormatError, ImageParser, ImageSize, PreadStream, StreamParser

iso_exts = ("avif", "heic", "heif")

BOX = Struct(">I4s")
ISPE = Struct(">IIII")


@dataclass
class Box:
    offs: int
    size: int
    text: bytes

    @property
    def start(self) -> int:
        return self.offs + 8

    @property
    def len(self) -> int:
        return self.size - 8

    @property
    def end(self) -> int:
        return self.offs + self.size

    @property
    def name(self) -> str:
        return self.text.decode("ascii", errors="replace")


class BoxParser(StreamParser):
    def __init__(self, stream: IO[bytes]):
        stream.seek(0, 2)
        self.end = stream.tell()
        self.stream = PreadStream(stream)

    def read_box(self, offs: int) -> Box | None:
        data = self.stream.pread(offs, BOX.size)
        if len(data) < BOX.size:
            return None
        b = Box(offs, *BOX.unpack(data))
        if b.size == 1:
            b.size = 8
        if not b.size:
            b.size = self.end - b.offs
        return b

    def find_box(self, text: bytes, offs: int, end: int) -> Box | None:
        b = self.read_box(offs)
        while True:
            if not b:
                return None
            if b.text == text:
                return b
            if b.end >= end:
                break
            b = self.read_box(b.end)
        return None


class IFFParser(ImageParser, BoxParser):
    def image_size(self) -> ImageSize:
        b = self.read_box(0)
        if not b:
            raise FormatError("Empty file")

        if b.text != b"ftyp":
            raise FormatError("No ftyp box")

        m = self.find_box(b"meta", b.end, self.end)
        if not m:
            raise FormatError("meta not found")

        b = self.find_box(b"iprp", m.start + 4, m.end)
        if not b:
            raise FormatError("iprp not found")

        b = self.find_box(b"ipco", b.start, b.end)
        if not b:
            raise FormatError("ipco not found")

        sz = None
        offs = b.start
        end = b.end
        rotate = False

        while True:
            b = self.read_box(offs)
            if not b:
                raise FormatError("failed to read box")

            if b.text == b"ispe":
                data = self.stream.pread(b.start, ISPE.size)
                _, width, height, _ = ISPE.unpack(data)
                if not sz or sz.width < width:
                    sz = ImageSize(width, height)

            if b.text == b"irot":
                data = self.stream.pread(b.start, 1)
                rotate = data[0] & 1 == 1

            if b.end >= end:
                break

            offs = b.end

        if not sz:
            raise FormatError("ispe not found")

        return ImageSize(sz.height, sz.width) if rotate else sz


def isobmff_image_size(stream: IO[bytes]) -> ImageSize:
    return IFFParser(stream).image_size()
