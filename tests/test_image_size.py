import os
import sys
from subprocess import CalledProcessError, check_output
from typing import Type

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from kstools.bmp import BmpParser, bmp_exts  # noqa: E402
from kstools.gif import GifParser, gif_exts  # noqa: E402
from kstools.isobmff import IFFParser, iso_exts  # noqa: E402
from kstools.jpeg import JpegParser, jpeg_exts  # noqa: E402
from kstools.jpegxl import JpegxlParser, jpegxl_exts  # noqa: E402
from kstools.magic import parse_stream  # noqa: E402
from kstools.png import PngParser, png_exts  # noqa: E402
from kstools.tiff import TiffParser, tiff_exts  # noqa: E402
from kstools.webp import WebpParser, webp_exts  # noqa: E402


def perc(v: int, t: int) -> str:
    if not t or not v:
        return "0%"
    return f"{100. * v / t:.02f}%"


def fileextlow(name: str) -> str:
    e = os.path.splitext(name)[1].lower()
    return e[1:] if e else ""


def identify(fpath: str) -> str:
    real = check_output(["identify", fpath]).decode("utf-8")
    real = real[len(fpath) + 1 :]
    split = real.split(" ")
    real = split[3].split("+")[0] if split[1] == "GIF" else split[1]
    return real


def jxlinfo(fpath: str) -> str:
    real = check_output(["jxlinfo", fpath]).decode("utf-8")
    split = real.split(",")
    real = split[1].strip()
    return real


def gen_lookup() -> dict:
    d = {}
    parsers = (
        (bmp_exts, BmpParser, identify),
        (gif_exts, GifParser, identify),
        (jpeg_exts, JpegParser, identify),
        (jpegxl_exts, JpegxlParser, jxlinfo),
        (iso_exts, IFFParser, identify),
        (png_exts, PngParser, identify),
        (tiff_exts, TiffParser, identify),
        (webp_exts, WebpParser, identify),
    )
    for exts, p, real in parsers:
        for e in exts:
            d[e] = (p, real)
    return d


def clsname(v: Type):
    return v.__name__ if v else "None"


def test():
    path = sys.argv[1] if len(sys.argv) > 1 else "."
    file_count = 0
    byte_count = 0
    failures = 0
    seek_count = 0
    bytes_read = 0
    wrong_guess = 0
    errors = {}
    failed = []
    lookup = gen_lookup()
    exts = lookup.keys()

    for root, _, files in os.walk(path):
        for f in files:
            ext = fileextlow(f)
            if ext not in exts:
                continue

            fpath = os.path.join(root, f)
            with open(fpath, "rb") as s:
                parser, real = lookup[ext]
                p = parser(s)
                sz, err = p.image_size()

                guess, _ = parse_stream(s)
                s.seek(0, 2)
                file_count += 1
                byte_count += s.tell()
                bytes_read += p.stream.bytes_read
                seek_count += p.stream.seek_count

            if sz:
                sz = f"{sz.width}x{sz.height}"
            try:
                real = real(fpath)
            except CalledProcessError:
                real = "invalid file"

            print(
                f"{fpath}: {sz} (real {real});"
                f" {clsname(parser)} guess={clsname(guess)}"
            )

            if not sz or sz != real or guess != parser:
                failures += 1
                if guess != parser:
                    wrong_guess += 1
                    err = err or "wrong guess"
                failed.append(fpath)
                err = err or "wrong size"
                count = errors.get(err, 0)
                errors[err] = count + 1

    print(f"file_count={file_count} byte_count={byte_count}")
    avg = f" (avg={seek_count/file_count:.02f}/file)" if file_count else ""
    print(
        f"bytes_read={bytes_read} ({perc(bytes_read, byte_count)})"
        f" seek_count={seek_count}{avg}"
    )
    print(
        f"failures={failures} ({perc(failures, file_count)})"
        f" wrong_guess={wrong_guess} errors={errors}"
    )

    MAX = 25
    for i, fpath in enumerate(failed):
        if i > MAX:
            print("...")
            break
        print(f"{fpath}")
    return failures > 0


if __name__ == "__main__":
    sys.exit(test())
