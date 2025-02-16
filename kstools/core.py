from binascii import hexlify
from dataclasses import dataclass
from typing import IO, Tuple


def b2x(data: bytes):
    return hexlify(data[0:11]).decode("ascii")


def be16(data: bytes):
    return int.from_bytes(data[:2], "big")


def le16(data: bytes):
    return int.from_bytes(data[:2], "little")


@dataclass
class ImageSize:
    width: int
    height: int


ImageSizeResult = Tuple[ImageSize, str]


class ImageParser:
    def image_size(self) -> ImageSizeResult:
        pass


class PreadStream:
    def __init__(self, stream: IO[bytes]):
        stream.seek(0)
        self.stream = stream
        self.offs = 0
        self.bytes_read = 0
        self.seek_count = 0

    def seek(self, offs: int):
        if self.offs != offs:
            self.offs = offs
            self.stream.seek(offs)
            self.seek_count += 1

    def skip(self, length: int):
        self.seek(self.offs + length)

    def read(self, size: int = -1) -> bytes:
        data = self.stream.read(size)
        self.bytes_read += len(data)
        self.offs += len(data)
        return data

    def pread(self, offs: int, size: int = -1) -> bytes:
        self.seek(offs)
        return self.read(size)
