from typing import IO

from .bmp import OS2IDS, WINIDS, BmpParser
from .core import FormatError, ImageParser, ImageSize, b2x
from .gif import GifParser
from .isobmff import IFFParser
from .jpeg import JpegParser
from .jpegxl import JXLBOX, JpegxlParser
from .png import PngParser
from .tiff import TiffParser
from .webp import WebpParser


def parse_bytes(data: bytes) -> type[ImageParser]:
    if len(data) < 12:
        raise FormatError(f"Data length {len(data)} is too short")

    if data[0] == 0:
        if data[:12] == JXLBOX[:12]:
            return JpegxlParser
        if data[4:8] == b"ftyp":
            return IFFParser

    elif data[0] == 0xFF:
        if data[1] == 0xD8:
            return JpegParser
        if data[1] == 0x0A:
            return JpegxlParser

    elif data[:4] == b"\x89PNG":
        return PngParser

    elif data[:4] == b"II*\x00" or data[:4] == b"MM\x00*":
        return TiffParser

    elif data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return WebpParser

    elif data[:3] == b"GIF":
        return GifParser

    elif data[:2] in WINIDS + OS2IDS:
        return BmpParser

    raise FormatError(f"Unknown file signarure {b2x(data)}")


def parse_stream(stream: IO[bytes]) -> type[ImageParser]:
    stream.seek(0)
    data = stream.read(12)
    return parse_bytes(data)


def image_stream_size(stream: IO[bytes]) -> ImageSize:
    cls = parse_stream(stream)
    return cls(stream).image_size()
