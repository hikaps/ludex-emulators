"""The bundled, pinned emulator manifest and its validation."""
from __future__ import annotations

import json
import platform
import re
from collections.abc import Mapping
from dataclasses import dataclass
from importlib import resources

_ID = re.compile(r"[a-z][a-z0-9-]{0,31}")
_SHA = re.compile(r"[0-9a-f]{64}")
_MAX_SIZE = 2 * 1024**3


class ManifestError(Exception):
    def __init__(self) -> None:
        super().__init__("the bundled emulator manifest is invalid")
        self.code = "invalid_manifest"
        self.message = "the bundled emulator manifest is invalid"


@dataclass(frozen=True, slots=True)
class Emulator:
    id: str
    name: str
    version: str
    platform: str
    kind: str
    file: str
    url: str
    size: int
    sha256: str
    launch: tuple[str, ...]
    source: str


@dataclass(frozen=True, slots=True)
class System:
    id: str
    name: str
    emulator: str
    extensions: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Manifest:
    systems: Mapping[str, System]
    emulators: Mapping[str, Emulator]


def host_platform() -> str | None:
    if platform.system() == "Linux" and platform.machine() in ("x86_64", "AMD64"):
        return "linux-x86_64"
    return None


def _str(value: object) -> str:
    if not isinstance(value, str) or not value:
        raise ManifestError
    return value


def _emulator(emu_id: str, raw: object) -> Emulator:
    if not _ID.fullmatch(emu_id) or not isinstance(raw, dict):
        raise ManifestError
    url = _str(raw.get("url"))
    size = raw.get("size")
    file = _str(raw.get("file"))
    launch = raw.get("launch")
    sha = _str(raw.get("sha256"))
    if (
        not url.startswith("https://") or "?" in url or "#" in url
        or isinstance(size, bool) or not isinstance(size, int) or not 0 < size <= _MAX_SIZE
        or not _SHA.fullmatch(sha)
        or "/" in file or file.startswith(".")
        or _str(raw.get("kind")) != "appimage"
        or not isinstance(launch, list) or not all(isinstance(a, str) for a in launch)
        or launch.count("{rom}") != 1
    ):
        raise ManifestError
    return Emulator(
        emu_id, _str(raw.get("name")), _str(raw.get("version")), _str(raw.get("platform")), "appimage",
        file, url, size, sha, tuple(launch), _str(raw.get("source")),
    )


def _system(sys_id: str, raw: object, emulators: Mapping[str, Emulator]) -> System:
    if not _ID.fullmatch(sys_id) or not isinstance(raw, dict):
        raise ManifestError
    exts = raw.get("extensions")
    if (
        _str(raw.get("emulator")) not in emulators
        or not isinstance(exts, list) or not exts
        or not all(isinstance(e, str) and len(e) > 1 and e.startswith(".") and e == e.lower() for e in exts)
    ):
        raise ManifestError
    return System(sys_id, _str(raw.get("name")), raw["emulator"], tuple(exts))


def load_manifest(text: str | None = None) -> Manifest:
    if text is None:
        text = resources.files("ludex_emulators").joinpath("manifest.json").read_text(encoding="utf-8")
    try:
        data = json.loads(text)
        if not isinstance(data, dict) or data.get("schema") != 1:
            raise ManifestError
        raw_emus, raw_systems = data.get("emulators"), data.get("systems")
        if not isinstance(raw_emus, dict) or not isinstance(raw_systems, dict):
            raise ManifestError
        emulators = {k: _emulator(k, v) for k, v in raw_emus.items()}
        systems = {k: _system(k, v, emulators) for k, v in raw_systems.items()}
    except (ValueError, KeyError, TypeError):
        raise ManifestError from None
    return Manifest(systems, emulators)
