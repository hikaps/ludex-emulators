from __future__ import annotations

import fcntl
import os
import sys
from importlib.metadata import EntryPoint

import pytest
from ludex.errors import LudexError
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
    assert problems == {} and loaded["emulators"].capabilities == ("commands", "views")


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
    assert args[1:4] == ("emulators", "install-pcsx2", [sys.executable, "-m", "ludex_emulators", "install", "pcsx2"])
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
