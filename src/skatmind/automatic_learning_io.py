"""Bounded, non-link owned storage I/O. No discovery of recording categories."""

from __future__ import annotations

import os
import re
import stat
import uuid
from pathlib import Path

from .automatic_learning_contracts import OBJECT_AREAS, ObjectRefV1

_OBJECT_NAME = re.compile(r"[0-9a-f]{64}\.json\Z")
_TEMP_NAME = re.compile(r"\.auto-[0-9a-f]{32}\.tmp\Z")


def checked_path(path: Path, *, directory: bool = False):
    info = path.stat(follow_symlinks=False)
    if (path.is_symlink() or path.is_junction()
            or getattr(info, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT):
        raise ValueError("Automatic Learning paths must not be links or reparse points.")
    if not (stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode)):
        raise ValueError("Automatic Learning paths must have their regular owned type.")
    return info


def stamp(info):
    return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns


def directory_identity(path: Path):
    info = checked_path(path, directory=True)
    return info.st_dev, info.st_ino


def checked_root(root: Path):
    # Check ancestors too: a non-link child of a substituted linked home is unsafe.
    for parent in reversed(root.parents):
        checked_path(parent, directory=True)
    return directory_identity(root)


def object_path(root: Path, reference: ObjectRefV1):
    if type(reference) is not ObjectRefV1:
        raise ValueError("Expected an exact object reference.")
    reference.__post_init__()
    checked_root(root)
    checked_path(root / reference.area, directory=True)
    return root / reference.area / f"{reference.fingerprint}.json"


def read_bounded(path: Path, limit: int) -> bytes:
    before = checked_path(path)
    if before.st_size > limit:
        raise ValueError("Automatic Learning file exceeds its byte limit.")
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags)
    with os.fdopen(descriptor, "rb") as file:
        opened = os.fstat(file.fileno())
        if stamp(opened) != stamp(before) or not stat.S_ISREG(opened.st_mode):
            raise ValueError("Automatic Learning file changed while opening.")
        raw = file.read(limit + 1)
        after = os.fstat(file.fileno())
    if (len(raw) > limit or stamp(after) != stamp(before)
            or stamp(checked_path(path)) != stamp(before)):
        raise ValueError("Automatic Learning file changed or exceeded its read bound.")
    return raw


def scan_files(root: Path):
    """All retained object bytes count; only canonical owned names can be deleted."""
    checked_root(root)
    result = {}
    for area in ("", *OBJECT_AREAS):
        directory = root / area
        checked_path(directory, directory=True)
        with os.scandir(directory) as entries:
            for entry in entries:
                if not area and not _TEMP_NAME.fullmatch(entry.name):
                    continue
                path = directory / entry.name
                info = path.stat(follow_symlinks=False)
                regular = stat.S_ISREG(info.st_mode) and not (
                    path.is_symlink() or path.is_junction()
                    or getattr(info, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT
                )
                result[path] = (stamp(info), bool(
                    regular and (_TEMP_NAME.fullmatch(entry.name)
                                 or (area and _OBJECT_NAME.fullmatch(entry.name)))
                ))
    return result


def total_bytes(root: Path, files):
    # A publication hard-link and its temporary alias occupy the same inode.
    sizes = {}
    directories = {root / area for area in OBJECT_AREAS}
    for path, (value, _owned) in files.items():
        if path.parent in directories:
            sizes[value[:2]] = value[2]
    return sum(sizes.values())


def acquire_local_lease(root: Path):
    """Nonblocking OS advisory lease shared by cooperating local processes."""
    path = root / ".coordination.lock"
    before = checked_path(path)
    file = path.open("r+b")
    try:
        if stamp(os.fstat(file.fileno())) != stamp(before):
            raise ValueError("Automatic Learning coordination file changed.")
        if os.name == "nt":
            import msvcrt

            msvcrt.locking(file.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl

            fcntl.flock(file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BaseException:
        file.close()
        raise
    return file


def release_local_lease(file):
    try:
        if os.name == "nt":
            import msvcrt

            file.seek(0)
            msvcrt.locking(file.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl

            fcntl.flock(file.fileno(), fcntl.LOCK_UN)
    finally:
        file.close()


def write_temporary(directory: Path, raw: bytes) -> Path:
    checked_path(directory, directory=True)
    path = directory / f".auto-{uuid.uuid4().hex}.tmp"
    # An interrupted write may leave an owned temporary; never a candidate object.
    with path.open("xb") as file:
        view = memoryview(raw)
        while view:
            written = file.write(view)
            if type(written) is not int or written <= 0:
                raise OSError("Incomplete Automatic Learning temporary write.")
            view = view[written:]
        file.flush()
        os.fsync(file.fileno())
    return path


def discard_temporary(root: Path, path: Path):
    checked_root(root)
    if path.parent not in (root, *(root / area for area in OBJECT_AREAS)):
        raise ValueError("Temporary file escaped its owned root.")
    if not _TEMP_NAME.fullmatch(path.name):
        raise ValueError("Expected an owned temporary filename.")
    checked_path(path.parent, directory=True)
    try:
        checked_path(path)
    except FileNotFoundError:
        return
    path.unlink()


def sync_directory(directory: Path):
    descriptor = None
    try:
        descriptor = os.open(directory, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        os.fsync(descriptor)
    except OSError:
        pass  # Windows does not support opening directories for fsync.
    finally:
        if descriptor is not None:
            os.close(descriptor)
