"""Where the plugin keeps its files. Nothing is written outside the state root."""
from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path


class InstallError(Exception):
    """A failure with a stable ``code`` and a fixed, secret-free ``message``."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def state_root(environ: Mapping[str, str] | None = None) -> Path:
    env = os.environ if environ is None else environ
    if env.get("LUDEX_EMULATORS_HOME"):
        return Path(env["LUDEX_EMULATORS_HOME"]).expanduser().absolute()
    if env.get("XDG_DATA_HOME"):
        return Path(env["XDG_DATA_HOME"]).expanduser().absolute() / "ludex-emulators"
    return Path.home() / ".local" / "share" / "ludex-emulators"


def ensure_dir(path: Path) -> None:
    try:
        path.mkdir(mode=0o700, parents=True, exist_ok=True)
    except OSError:
        raise InstallError("state_unwritable", "the emulators state folder cannot be created") from None
