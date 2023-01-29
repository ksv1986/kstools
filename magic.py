from typing import IO, Tuple

from .bmp import OS2IDS, WINIDS, BmpParser
from .gif import GifParser
from .isobmff import IFFParser
from .jpeg import JpegParser
from .jpegxl import JXLBOX, JpegxlParser
from .png import PngParser
from .types import ImageParser, ImageSizeResult
from .webp import WebpParser


def parse_bytes(data: bytes) -> Tuple[ImageParser, str]:
    if len(data) < 12:
        return None, f"Data length {len(data)} is too short"

    if data[0] == 0:
        if data[:12] == JXLBOX[:12]:
            return JpegxlParser, None
        if data[4:8] == b"ftyp":
            return IFFParser, None

    elif data[0] == 0xFF:
        if data[1] == 0xD8:
            return JpegParser, None
        if data[1] == 0x0A:
            return JpegxlParser, None

    elif data[:4] == b"\x89PNG":
        return PngParser, None

    elif data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return WebpParser, None

    elif data[:3] == b"GIF":
        return GifParser, None

    elif data[:2] in WINIDS + OS2IDS:
        return BmpParser, None

    return None, "Unknown file"


def parse_stream(stream: IO[bytes]) -> Tuple[ImageParser, str]:
    stream.seek(0)
    data = stream.read(12)
    return parse_bytes(data)


def image_stream_size(stream: IO[bytes]) -> ImageSizeResult:
    cls, err = parse_stream(stream)
    if err:
        return None, err

    return cls(stream).image_size()
