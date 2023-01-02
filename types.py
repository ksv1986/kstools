from binascii import hexlify
from dataclasses import dataclass
from typing import IO


def b2x(data: bytes):
    return hexlify(data[0:11]).decode("ascii")


@dataclass
class ImageSize:
    width: int
    height: int


ImageSizeResult = tuple[ImageSize, Exception]


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
