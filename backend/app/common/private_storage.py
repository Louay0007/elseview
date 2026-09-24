import csv
import hashlib
import io
import os
import re
import shutil
import struct
import wave
import zlib
from contextlib import contextmanager

from app.common.errors import DomainError

LIMITS = {
    "image/png": 8 * 1024 * 1024,
    "text/csv": 2 * 1024 * 1024,
    "text/plain": 1024 * 1024,
    "audio/wav": 16 * 1024 * 1024,
}
EXTENSIONS = {"image/png": "png", "text/csv": "csv", "text/plain": "txt", "audio/wav": "wav"}


class PrivateStorage:
    def __init__(self, root, minimum_free=32 * 1024 * 1024):
        self.root = root
        self.minimum_free = minimum_free

    @contextmanager
    def directory(self):
        descriptor = os.open(self.root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            try:
                os.mkdir("assets", mode=0o700, dir_fd=descriptor)
            except FileExistsError:
                pass
            child = os.open(
                "assets", os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=descriptor
            )
            try:
                yield child
            finally:
                os.close(child)
        finally:
            os.close(descriptor)

    def name(self, key):
        if not re.fullmatch(r"[0-9a-f]{32}", key):
            raise DomainError("INVALID_STORAGE_KEY", "Invalid storage reference.", 400)
        return key

    def create(self, key, size):
        with self.directory() as directory:
            if shutil.disk_usage(self.root).free < size + self.minimum_free:
                raise DomainError("STORAGE_FULL", "Storage is temporarily unavailable.", 507)
            return os.open(
                self.name(key),
                os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                0o600,
                dir_fd=directory,
            )

    def read(self, key, limit):
        with self.directory() as directory:
            descriptor = os.open(
                self.name(key), os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory
            )
            with os.fdopen(descriptor, "rb") as source:
                import stat

                if not stat.S_ISREG(os.fstat(source.fileno()).st_mode):
                    raise ValueError("Unsupported object")
                content = source.read(limit + 1)
                if len(content) > limit:
                    raise ValueError("Object exceeds limit")
                return content

    def delete(self, key):
        with self.directory() as directory:
            try:
                os.unlink(self.name(key), dir_fd=directory)
            except FileNotFoundError:
                pass


def validate_png(content):
    if not content.startswith(b"\x89PNG\r\n\x1a\n"):
        raise ValueError("Invalid PNG")
    offset, chunks, compressed = 8, [], bytearray()
    width = height = channels = None
    while offset < len(content):
        if len(content) - offset < 12:
            raise ValueError("Truncated PNG")
        size = struct.unpack_from(">I", content, offset)[0]
        kind = content[offset + 4 : offset + 8]
        end = offset + 12 + size
        if end > len(content) or kind not in {b"IHDR", b"IDAT", b"IEND"}:
            raise ValueError("Unsupported PNG chunk")
        data = content[offset + 8 : offset + 8 + size]
        if zlib.crc32(kind + data) != struct.unpack_from(">I", content, end - 4)[0]:
            raise ValueError("Invalid PNG checksum")
        if kind == b"IHDR":
            if chunks or len(data) != 13:
                raise ValueError("Invalid PNG header")
            width, height, depth, color, compression, filtering, interlace = struct.unpack(
                ">IIBBBBB", data
            )
            if (
                not 1 <= width <= 4096
                or not 1 <= height <= 4096
                or width * height > 4_000_000
                or depth != 8
                or color not in {2, 6}
                or compression
                or filtering
                or interlace
            ):
                raise ValueError("Unsupported PNG encoding")
            channels = 3 if color == 2 else 4
        elif kind == b"IDAT":
            if not chunks or chunks[-1] not in {b"IHDR", b"IDAT"}:
                raise ValueError("Invalid PNG ordering")
            compressed.extend(data)
        elif size != 0 or end != len(content):
            raise ValueError("Invalid PNG end")
        chunks.append(kind)
        offset = end
    if len(chunks) < 3 or chunks[-1] != b"IEND" or not width:
        raise ValueError("Incomplete PNG")
    stride = width * channels + 1
    expected = stride * height
    decoder = zlib.decompressobj()
    pixels = decoder.decompress(bytes(compressed), expected + 1)
    if (
        len(pixels) != expected
        or not decoder.eof
        or decoder.unused_data
        or any(pixels[pos] > 4 for pos in range(0, expected, stride))
    ):
        raise ValueError("Invalid PNG pixels")
    return {"width": width, "height": height, "duration_ms": None}


def validate_content(content, media_type, checksum):
    if hashlib.sha256(content).hexdigest() != checksum:
        raise ValueError("Checksum mismatch")
    if not content or len(content) > LIMITS[media_type]:
        raise ValueError("Invalid content length")
    result = {"width": None, "height": None, "duration_ms": None}
    if media_type == "image/png":
        return validate_png(content)
    if media_type in {"text/plain", "text/csv"}:
        text = content.decode("utf-8-sig")
        if not text.strip() or any(ord(char) < 32 and char not in "\r\n\t" for char in text):
            raise ValueError("Invalid text")
        if media_type == "text/csv":
            rows = csv.reader(io.StringIO(text), strict=True)
            width = None
            for number, row in enumerate(rows):
                if (
                    number >= 10000
                    or not row
                    or len(row) > 100
                    or any(len(cell) > 10000 for cell in row)
                ):
                    raise ValueError("CSV limits exceeded")
                if width is not None and len(row) != width:
                    raise ValueError("Inconsistent CSV columns")
                width = len(row)
    elif media_type == "audio/wav":
        if (
            content[:4] != b"RIFF"
            or len(content) < 12
            or struct.unpack_from("<I", content, 4)[0] + 8 != len(content)
        ):
            raise ValueError("Invalid WAV")
        with wave.open(io.BytesIO(content)) as audio:
            count = audio.getnframes()
            if (
                audio.getcomptype() != "NONE"
                or audio.getnchannels() not in {1, 2}
                or audio.getsampwidth() not in {1, 2, 3, 4}
                or not 8000 <= audio.getframerate() <= 96000
                or count < 1
            ):
                raise ValueError("Unsupported WAV")
            if len(audio.readframes(count)) != count * audio.getnchannels() * audio.getsampwidth():
                raise ValueError("Truncated WAV")
            result["duration_ms"] = count * 1000 // audio.getframerate()
            if result["duration_ms"] > 600000:
                raise ValueError("Recording too long")
    return result
