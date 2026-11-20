from __future__ import annotations

import importlib.metadata

import ludex_emulators


def test_version_matches_installed_metadata() -> None:
    assert ludex_emulators.__version__ == importlib.metadata.version("ludex-emulators")
