from __future__ import annotations

import fcntl
import os
import subprocess
import sys
from pathlib import Path
from importlib.metadata import EntryPoint

import pytest
from ludex.errors import LudexError
from ludex.plugins import SourceError
from ludex.loader import load_providers

from ludex_emulators import plugin
from ludex_emulators.plugin import PROVIDER

EMU = plugin._MANIFEST.emulators["pcsx2"]
COMMANDS = {c.name: c for c in PROVIDER.commands}


@pytest.fixture
def linux(monkeypatch):
    monkeypatch.setattr(plugin, "host_platform", lambda: "linux-x86_64")


def _row(root):
    return PROVIDER.views[0].fetch({}).rows[0]


def _put(root, version, executable=True):
    path = root / "emulators" / "pcsx2" / version / EMU.file
    path.parent.mkdir(parents=True)
    path.write_bytes(b"x")
    path.chmod(0o755 if executable else 0o644)


def test_loader_accepts_provider():
    loaded, problems = load_providers([EntryPoint("emulators", "ludex_emulators.plugin:PROVIDER", "ludex.providers")])
    assert problems == {} and loaded["emulators"].capabilities == ("owned", "installed", "launch", "commands", "views")


def test_row_unsupported(root, monkeypatch):
    monkeypatch.setattr(plugin, "host_platform", lambda: None)
    row = _row(root)
    assert row.cells[-1] == "unsupported platform" and row.actions == ()


def test_row_not_installed_and_failed(root, linux):
    row = _row(root)
    assert row.id == "pcsx2" and row.cells[-1] == "not installed" and row.cells[3] == "-"
    assert [(a.label, a.command, a.args) for a in row.actions] == [("Install", "install", ("pcsx2",))]
    (root / "emulators").mkdir(parents=True, exist_ok=True)
    (root / "emulators" / "pcsx2.failed").write_text("checksum_mismatch")
    row = _row(root)
    assert row.cells[-1] == "failed: checksum_mismatch" and row.actions[0].label == "Install"


def test_row_installed_and_update(root, linux):
    _put(root, EMU.version)
    row = _row(root)
    assert row.cells[-1] == "installed" and [a.label for a in row.actions] == ["Remove"]
    (root / "emulators" / "pcsx2" / EMU.version / EMU.file).unlink()
    other = root / "emulators" / "pcsx2" / "1.0.0"
    other.mkdir(parents=True)
    (other / EMU.file).write_bytes(b"x")
    (other / EMU.file).chmod(0o755)
    row = _row(root)
    assert row.cells[-1] == "update available" and [a.label for a in row.actions] == ["Update", "Remove"]


def test_row_installing(root, linux):
    (root / "emulators").mkdir(parents=True)
    fd = os.open(root / "emulators" / "pcsx2.lock", os.O_RDWR | os.O_CREAT)
    fcntl.flock(fd, fcntl.LOCK_EX)
    try:
        row = _row(root)
        assert row.cells[-1] == "installing" and row.actions == ()
    finally:
        os.close(fd)


def test_install_starts_service(root, linux, monkeypatch):
    calls = []
    monkeypatch.setattr(plugin, "start_service", lambda *a, **k: calls.append((a, k)))
    result = COMMANDS["install"].run(plugin.CommandContext(conn="conn", providers={}), ["pcsx2"])
    assert result.data["state"] == "installing"
    args, kwargs = calls[0]
    assert args[1:3] == ("emulators", "install-pcsx2")
    argv = args[3]
    assert argv[:2] == [sys.executable, "-c"] and argv[3:] == [str(Path(plugin.__file__).resolve().parent.parent), "pcsx2"]
    # the child must import the plugin from a bare interpreter, with only that folder added
    out = subprocess.run([argv[0], "-S", "-c", argv[2].replace("main(", "print(", 1).replace("sys.exit(", "(", 1), *argv[3:]], capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
    assert kwargs["cwd"] == root


def test_install_when_installed_starts_nothing(root, linux, monkeypatch):
    _put(root, EMU.version)
    monkeypatch.setattr(plugin, "start_service", lambda *a, **k: pytest.fail("started"))
    result = COMMANDS["install"].run(plugin.CommandContext(conn="conn", providers={}), ["pcsx2"])
    assert result.data["state"] == "installed"


def test_install_errors(root, linux, monkeypatch):
    ctx = plugin.CommandContext(conn="conn", providers={})
    with pytest.raises(LudexError) as exc:
        COMMANDS["install"].run(ctx, ["nope"])
    assert exc.value.code == "unknown_emulator"
    monkeypatch.setattr(plugin, "host_platform", lambda: None)
    with pytest.raises(LudexError) as exc:
        COMMANDS["install"].run(ctx, ["pcsx2"])
    assert exc.value.code == "unsupported_platform"


def test_remove_command(root, linux):
    ctx = plugin.CommandContext(conn="conn", providers={})
    assert COMMANDS["remove"].run(ctx, ["pcsx2"]).data["removed"] is False
    _put(root, EMU.version)
    assert COMMANDS["remove"].run(ctx, ["pcsx2"]).data["removed"] is True


def _account(tmp_path):
    folder = tmp_path / "roms"
    (folder / "sub").mkdir(parents=True)
    (folder / "sub" / "A_Game (USA).iso").write_bytes(b"x")
    return {"folder": str(folder), "system": "ps2"}


def test_fetch_and_installed(root, tmp_path):
    config = _account(tmp_path)
    result = PROVIDER.fetch(config)
    assert result.complete and [(g.store, g.store_id, g.title) for g in result.games] == [("emulators", "sub/A_Game (USA).iso", "A Game")]
    assert set(PROVIDER.installed(config)) == {"sub/A_Game (USA).iso"}
    assert PROVIDER.game_folder(config, "sub/A_Game (USA).iso") == (tmp_path / "roms" / "sub").resolve()


def test_empty_folder_is_an_error_not_an_empty_library(root, tmp_path):
    (tmp_path / "empty").mkdir()
    with pytest.raises(SourceError) as exc:
        PROVIDER.fetch({"folder": str(tmp_path / "empty"), "system": "ps2"})
    assert exc.value.code == "folder_empty"


@pytest.mark.parametrize("config", [{"folder": "relative", "system": "ps2"}, {"folder": "/tmp", "system": "nope"}, {}])
def test_bad_config(root, config):
    with pytest.raises(SourceError) as exc:
        PROVIDER.fetch(config)
    assert exc.value.code == "invalid_config"


def test_launch_command(root, tmp_path):
    config = _account(tmp_path)
    sid = "sub/A_Game (USA).iso"
    with pytest.raises(SourceError) as exc:
        PROVIDER.launch_command(config, sid)
    assert exc.value.code == "emulator_missing"
    _put(root, EMU.version)
    exe = root / "emulators" / "pcsx2" / EMU.version / EMU.file
    assert PROVIDER.launch_command(config, sid) == [str(exe), "-batch", "-fullscreen", str((tmp_path / "roms" / sid).resolve())]
    with pytest.raises(SourceError):
        PROVIDER.launch_command(config, "../x.iso")
