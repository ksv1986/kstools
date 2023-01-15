import os
import sys
from subprocess import CalledProcessError, check_output

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from kstools.isobmff import ImageParser, iso_exts  # noqa: E402
from kstools.jpeg import JpegParser, jpeg_exts  # noqa: E402


def perc(v: int, t: int) -> str:
    if not t or not v:
        return "0%"
    return f"{100. * v / t:.02f}%"


def fileextlow(name: str) -> str:
    e = os.path.splitext(name)[1].lower()
    return e[1:] if e else ""


def test():
    path = sys.argv[1] if len(sys.argv) > 1 else "."
    file_count = 0
    byte_count = 0
    failures = 0
    seek_count = 0
    bytes_read = 0
    errors = {}
    failed = []
    for root, _, files in os.walk(path):
        for f in files:
            ext = fileextlow(f)
            if ext not in jpeg_exts + iso_exts:
                continue

            fpath = os.path.join(root, f)
            with open(fpath, "rb") as s:
                if ext in jpeg_exts:
                    p = JpegParser(s)
                else:
                    p = ImageParser(s)
                sz, err = p.image_size()

                s.seek(0, 2)
                file_count += 1
                byte_count += s.tell()
                bytes_read += p.stream.bytes_read
                seek_count += p.stream.seek_count

            if sz:
                sz = f"{sz.width}x{sz.height}"
            try:
                real = check_output(["identify", fpath]).decode("utf-8")
                real = real[len(fpath) + 1 :]
                real = real.split(" ")[1]
            except CalledProcessError:
                real = "invalid file"

            print(f"{fpath}: {sz} (real {real})")

            if not sz or sz != real:
                failures += 1
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
    print(f"failures={failures} ({perc(failures, file_count)}) errors={errors}")

    MAX = 25
    for i, fpath in enumerate(failed):
        if i > MAX:
            print("...")
            break
        print(f"{fpath}")


if __name__ == "__main__":
    test()
