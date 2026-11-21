from __future__ import annotations

import pytest

from ludex_emulators.manifest import load_manifest
from ludex_emulators.roms import RomError, clean_title, resolve, scan

PS2 = load_manifest().systems["ps2"]


def _touch(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"x")


def test_clean_title():
    assert clean_title("Shadow_of_the_Colossus (USA) [SCUS-97472].iso") == "Shadow of the Colossus"
    assert clean_title("Game.ISO.gz") == "Game"
    assert clean_title("(USA).iso") == "(USA)"


def test_scan_filters_and_ids(tmp_path):
    for name in ("A.iso", "sub/B.CHD", "C.iso.gz", "notes.gz", "readme.txt", ".hidden.iso", ".dir/D.iso", "bin.bin"):
        _touch(tmp_path / name)
    assert scan(tmp_path, PS2) == [("A.iso", "A"), ("C.iso.gz", "C"), ("sub/B.CHD", "B")]


def test_scan_errors(tmp_path):
    with pytest.raises(RomError) as exc:
        scan(tmp_path / "missing", PS2)
    assert exc.value.code == "folder_unreadable"
    with pytest.raises(RomError) as exc:
        scan(tmp_path, PS2)
    assert exc.value.code == "folder_empty"
    for n in range(3):
        _touch(tmp_path / f"{n}.iso")
    with pytest.raises(RomError) as exc:
        scan(tmp_path, PS2, limit=2)
    assert exc.value.code == "too_many_roms"


def test_resolve(tmp_path):
    folder = tmp_path / "roms"
    _touch(folder / "ok.iso")
    _touch(folder / "game.txt")
    _touch(tmp_path / "outside.iso")
    (folder / "link.iso").symlink_to(tmp_path / "outside.iso")
    assert resolve(folder, "ok.iso", PS2) == (folder / "ok.iso").resolve()
    for bad in ("../outside.iso", "/etc/passwd", "link.iso", "game.txt", "missing.iso", "", "a\0.iso"):
        with pytest.raises(RomError) as exc:
            resolve(folder, bad, PS2)
        assert exc.value.code == "rom_not_found"
