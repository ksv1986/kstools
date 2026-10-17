from abc import ABC, abstractmethod
from binascii import hexlify
from typing import IO, NamedTuple


def b2x(data: bytes):
    return hexlify(data[0:12]).decode("ascii")


def be16(data: bytes):
    return int.from_bytes(data[:2], "big")


def le16(data: bytes):
    return int.from_bytes(data[:2], "little")


class FormatError(ValueError):
    pass


class ImageSize(NamedTuple):
    width: int
    height: int


class StreamParser(ABC):
    @abstractmethod
    def __init__(self, stream: IO[bytes]): ...


class ImageParser(StreamParser):
    @abstractmethod
    def image_size(self) -> ImageSize: ...


class PreadStream:
    def __init__(self, stream: IO[bytes]):
        stream.seek(0)
        self.stream = stream
        self.offs = 0
        self.bytes_read = 0
        self.seek_count = 0

    def seek(self, offs: int) -> int:
        if self.offs != offs:
            self.offs = offs
            self.seek_count += 1
            self.stream.seek(offs)
        return self.offs

    def skip(self, length: int) -> int:
        return self.seek(self.offs + length)

    def read(self, size: int = -1) -> bytes:
        data = self.stream.read(size)
        self.bytes_read += len(data)
        self.offs += len(data)
        return data

    def pread(self, offs: int, size: int = -1) -> bytes:
        self.seek(offs)
        return self.read(size)
