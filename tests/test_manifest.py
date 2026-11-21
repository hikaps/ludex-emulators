from __future__ import annotations

import json
from importlib import resources

import pytest

from ludex_emulators.manifest import ManifestError, load_manifest


def _data():
    return json.loads(resources.files("ludex_emulators").joinpath("manifest.json").read_text())


def test_bundled_manifest_loads():
    manifest = load_manifest()
    assert manifest.emulators["pcsx2"].size == 60119544
    assert manifest.systems["ps2"].emulator == "pcsx2"


@pytest.mark.parametrize("mutate", [
    lambda d: d["emulators"]["pcsx2"].update(url="http://example.com/x"),
    lambda d: d["emulators"]["pcsx2"].update(url="https://example.com/x?token=1"),
    lambda d: d["emulators"]["pcsx2"].update(sha256="ABC"),
    lambda d: d["emulators"]["pcsx2"].update(launch=["-batch"]),
    lambda d: d["emulators"]["pcsx2"].update(launch=["{rom}", "{rom}"]),
    lambda d: d["emulators"]["pcsx2"].update(size=0),
    lambda d: d["emulators"]["pcsx2"].update(file="../evil"),
    lambda d: d["emulators"]["pcsx2"].update(kind="exe"),
    lambda d: d["systems"]["ps2"].update(emulator="missing"),
    lambda d: d["systems"]["ps2"].update(extensions=["ISO"]),
    lambda d: d.update(schema=2),
])
def test_invalid_manifest_is_rejected(mutate):
    data = _data()
    mutate(data)
    with pytest.raises(ManifestError) as exc:
        load_manifest(json.dumps(data))
    assert exc.value.code == "invalid_manifest"


def test_garbage_is_rejected():
    with pytest.raises(ManifestError):
        load_manifest("not json")
