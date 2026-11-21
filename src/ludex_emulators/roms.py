"""ROM scanning, title cleanup and safe path resolution. Imports nothing from ludex."""
from __future__ import annotations

import os
import re
from pathlib import Path, PurePosixPath

from .manifest import System

_GROUPS = re.compile(r"\([^)]*\)|\[[^\]]*\]")


class RomError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def _allowed(name: str, system: System) -> bool:
    lower = name.lower()
    suffix = PurePosixPath(lower).suffix
    if suffix not in system.extensions:
        return False
    return suffix != ".gz" or PurePosixPath(lower).stem.endswith(".iso")


def _stem(filename: str) -> str:
    stem = PurePosixPath(filename).stem
    if filename.lower().endswith(".gz") and stem.lower().endswith(".iso"):
        stem = stem[:-4]
    return stem


def clean_title(filename: str) -> str:
    stem = _stem(filename)
    title = " ".join(_GROUPS.sub("", stem.replace("_", " ")).split())
    return title or stem


def scan(folder: Path, system: System, limit: int = 20000) -> list[tuple[str, str]]:
    if not folder.is_dir():
        raise RomError("folder_unreadable", "ROM folder is missing or unreadable")
    found: list[tuple[str, str]] = []
    for current, dirs, files in os.walk(folder, followlinks=False):
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        for name in files:
            if name.startswith(".") or not _allowed(name, system):
                continue
            found.append((Path(current, name).relative_to(folder).as_posix(), clean_title(name)))
            if len(found) > limit:
                raise RomError("too_many_roms", f"the ROM folder has more than {limit} ROMs; pick a narrower folder")
    if not found:
        raise RomError("folder_empty", "ROM folder has no ROMs (is the drive mounted?)")
    return sorted(found)


def resolve(folder: Path, store_id: str, system: System) -> Path:
    bad = RomError("rom_not_found", "the ROM file was not found")
    if not store_id or "\0" in store_id or store_id.startswith("/") or ".." in PurePosixPath(store_id).parts:
        raise bad
    try:
        base = folder.resolve()
        path = (folder / store_id).resolve()
    except (OSError, RuntimeError):
        raise bad from None
    if not path.is_relative_to(base) or not path.is_file() or not _allowed(path.name, system):
        raise bad
    return path
