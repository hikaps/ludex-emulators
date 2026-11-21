"""Download, verify, install and remove a pinned emulator. Standard library only; imports nothing from ludex."""
from __future__ import annotations

import fcntl
import hashlib
import os
import shutil
import urllib.request
from collections.abc import Callable
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from .manifest import Emulator, host_platform
from .paths import InstallError, ensure_dir

__all__ = ["InstallError", "binary", "install", "installed_version", "is_installing", "last_failure", "remove"]

_CHUNK = 1024 * 1024
_TIMEOUT = 30
Opener = Callable[[str], Any]


class _HttpsOnlyRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[no-untyped-def]
        if not newurl.startswith("https://"):
            raise InstallError("insecure_redirect", "the download redirected to a non-https address")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _default_opener(url: str) -> Any:
    return urllib.request.build_opener(_HttpsOnlyRedirect).open(url, timeout=_TIMEOUT)


def _dir(root: Path, emu: Emulator) -> Path:
    return root / "emulators" / emu.id


def _lock_path(root: Path, emu: Emulator) -> Path:
    return root / "emulators" / f"{emu.id}.lock"


def _failed_path(root: Path, emu: Emulator) -> Path:
    return root / "emulators" / f"{emu.id}.failed"


def _part_path(root: Path, emu: Emulator) -> Path:
    return root / "downloads" / f"{emu.id}-{emu.version}.part"


def _version_key(name: str) -> tuple[tuple[int, ...], str]:
    try:
        return tuple(int(p) for p in name.split(".")), name
    except ValueError:
        return (), name


def installed_version(root: Path, emu: Emulator) -> str | None:
    try:
        names = [
            p.name for p in _dir(root, emu).iterdir()
            if not p.name.endswith(".tmp") and (p / emu.file).is_file() and os.access(p / emu.file, os.X_OK)
        ]
    except OSError:
        return None
    return max(names, key=_version_key) if names else None


def binary(root: Path, emu: Emulator) -> Path | None:
    version = installed_version(root, emu)
    return _dir(root, emu) / version / emu.file if version else None


@contextmanager
def _lock(root: Path, emu: Emulator) -> Iterator[None]:
    ensure_dir(root / "emulators")
    fd = os.open(_lock_path(root, emu), os.O_RDWR | os.O_CREAT, 0o600)
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise InstallError("install_running", "an install of this emulator is already running") from None
        yield
    finally:
        os.close(fd)


def is_installing(root: Path, emu: Emulator) -> bool:
    try:
        with _lock(root, emu):
            return False
    except InstallError as exc:
        return exc.code == "install_running"


def last_failure(root: Path, emu: Emulator) -> str | None:
    try:
        text = _failed_path(root, emu).read_text(encoding="utf-8").strip()[:200]
    except OSError:
        return None
    return text or None


def _download(root: Path, emu: Emulator, opener: Opener, report: Callable[[str], None]) -> Path:
    part = _part_path(root, emu)
    ensure_dir(part.parent)
    part.unlink(missing_ok=True)
    digest = hashlib.sha256()
    try:
        fd = os.open(part, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "wb") as out, opener(emu.url) as response:
            if not str(response.geturl()).startswith("https://"):
                raise InstallError("insecure_redirect", "the download redirected to a non-https address")
            length = response.headers.get("Content-Length")
            if length is not None and length != str(emu.size):
                raise InstallError("size_mismatch", "the download size does not match the manifest")
            done, next_report = 0, 5
            while True:
                chunk = response.read(_CHUNK)
                if not chunk:
                    break
                done += len(chunk)
                if done > emu.size:
                    raise InstallError("size_mismatch", "the download size does not match the manifest")
                digest.update(chunk)
                out.write(chunk)
                percent = done * 100 // emu.size
                if percent >= next_report:
                    next_report = percent + 5
                    report(f"downloaded {done // _CHUNK} of {emu.size // _CHUNK} MiB")
            if done != emu.size:
                raise InstallError("size_mismatch", "the download size does not match the manifest")
    except InstallError:
        raise
    except OSError:
        raise InstallError("download_failed", "the download failed") from None
    if digest.hexdigest() != emu.sha256:
        raise InstallError("checksum_mismatch", "the download does not match the pinned checksum")
    return part


def install(
    root: Path, emu: Emulator, *, opener: Opener | None = None, platform: str | None = None,
    report: Callable[[str], None] = print,
) -> Path:
    if (platform if platform is not None else host_platform()) != emu.platform:
        raise InstallError("unsupported_platform", "this emulator build does not run on this system")
    with _lock(root, emu):
        _failed_path(root, emu).unlink(missing_ok=True)
        existing = binary(root, emu)
        if existing is not None and installed_version(root, emu) == emu.version:
            return existing
        target, tmp = _dir(root, emu) / emu.version, _dir(root, emu) / f"{emu.version}.tmp"
        try:
            part = _download(root, emu, opener or _default_opener, report)
            part.chmod(0o755)
            shutil.rmtree(tmp, ignore_errors=True)
            ensure_dir(tmp)
            os.replace(part, tmp / emu.file)
            shutil.rmtree(target, ignore_errors=True)
            os.replace(tmp, target)
            for entry in _dir(root, emu).iterdir():
                if entry != target:
                    shutil.rmtree(entry, ignore_errors=True)
        except (InstallError, OSError) as exc:
            _part_path(root, emu).unlink(missing_ok=True)
            shutil.rmtree(tmp, ignore_errors=True)
            code = exc.code if isinstance(exc, InstallError) else "install_failed"
            try:
                fd = os.open(_failed_path(root, emu), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
                with os.fdopen(fd, "w") as f:
                    f.write(code)
            except OSError:
                pass
            if isinstance(exc, InstallError):
                raise
            raise InstallError("install_failed", "the install failed") from None
        return target / emu.file


def remove(root: Path, emu: Emulator) -> bool:
    if is_installing(root, emu):
        raise InstallError("install_running", "an install of this emulator is already running")
    existed = _dir(root, emu).exists()
    shutil.rmtree(_dir(root, emu), ignore_errors=True)
    _failed_path(root, emu).unlink(missing_ok=True)
    return existed
