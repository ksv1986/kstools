from typing import IO

from .core import FormatError, ImageParser, ImageSize, PreadStream, b2x, be16

jpeg_exts = ("jpeg", "jpg")


class JpegParser(ImageParser):
    def __init__(self, stream: IO[bytes]):
        self.stream = PreadStream(stream)

    def image_size(self) -> ImageSize:
        soi = self.stream.read(2)
        if len(soi) < 2:
            raise FormatError("EOF")

        if soi[0] != 0xFF or soi[1] != 0xD8:
            raise FormatError(f"Wrong SOI {b2x(soi)}")

        while True:
            offs = self.stream.offs

            seg = self.stream.read(2)
            if len(seg) < 2:
                raise FormatError("EOF")

            if seg[0] != 0xFF:
                raise FormatError(f"Wrong segment header {b2x(seg)} at {offs}")

            if seg[1] >= 0xD0 and seg[1] < 0xD8:  # RSTn; skip
                continue

            if seg[1] == 0xD9:
                raise FormatError("EOI")

            seg_len = self.stream.read(2)
            if len(seg_len) < 2:
                raise FormatError("EOF")

            skip = be16(seg_len) - 2
            # print(f"seg: offs={offs:x}/{offs} {b2x(seg)}{b2x(seg_len)} len={skip}")
            if seg[1] == 0xC0 or seg[1] == 0xC2:  # SOFn
                data = self.stream.read(5)
                if len(data) < 5:
                    raise FormatError("EOF")

                h = be16(data[1:3])
                w = be16(data[3:5])
                return ImageSize(w, h)

            self.stream.skip(skip)


def jpeg_image_size(stream: IO[bytes]) -> ImageSize:
    return JpegParser(stream).image_size()
