from typing import IO

from .types import ImageSize, ImageSizeResult, PreadStream, b2x

jpegxl_exts = ("jxl",)

RATIO = (None, (1, 1), (12, 10), (4, 3), (3, 2), (16, 9), (5, 4), (2, 1))


def get_bits(bits: int, n: int) -> tuple[int, int]:
    v = bits & (2**n - 1)
    return bits >> n, v


def get_size(bits: int, div8: int, dist=(9, 13, 18, 30)) -> tuple[int, int]:
    if div8:
        bits, v = get_bits(bits, 5)
        return bits, 8 * (1 + v)
    else:
        bits, k = get_bits(bits, 2)
        bits, v = get_bits(bits, dist[k])
        return bits, 1 + v


class JpegxlParser:
    def __init__(self, stream: IO[bytes]):
        self.stream = PreadStream(stream)

    def image_size(self) -> ImageSizeResult:
        data = self.stream.pread(0, 11)
        if len(data) < 11:
            return None, "EOF"

        soi, data = data[:2], data[2:]
        if soi != b"\xFF\x0A":
            return None, f"Wrong SOI {b2x(soi)}"

        bits = int.from_bytes(data, "little")
        bits, div8 = get_bits(bits, 1)
        bits, h = get_size(bits, div8)
        bits, r = get_bits(bits, 3)
        ratio = RATIO[r]
        if ratio:
            w = h * ratio[0] // ratio[1]
        else:
            w = get_size(bits, div8)[1]

        return ImageSize(w, h), None


def jpegxl_image_size(stream: IO[bytes]) -> ImageSizeResult:
    return JpegxlParser(stream).image_size()
