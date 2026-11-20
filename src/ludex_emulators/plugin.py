"""The ludex provider. Needs ludex; the installer, manifest and paths modules do not."""
from __future__ import annotations

import argparse
import sys
from collections.abc import Mapping, Sequence

from ludex.errors import LudexError
from ludex.plugins import Command, CommandContext, CommandResult, Provider, View, ViewAction, ViewRow, ViewTable
from ludex.services import start_service

from . import installer
from .manifest import Emulator, host_platform, load_manifest
from .paths import InstallError, ensure_dir, state_root

_MANIFEST = load_manifest()


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> None:  # type: ignore[override]
        raise LudexError("invalid_arguments", message)


def _emulator(args: Sequence[str], prog: str) -> Emulator:
    parser = _Parser(prog=f"ludex emulators {prog}", add_help=False)
    parser.add_argument("emulator")
    emu = _MANIFEST.emulators.get(parser.parse_args(list(args)).emulator)
    if emu is None:
        raise LudexError("unknown_emulator", "unknown emulator")
    return emu


def _install(ctx: CommandContext, args: Sequence[str]) -> CommandResult:
    emu = _emulator(args, "install")
    if host_platform() != emu.platform:
        raise LudexError("unsupported_platform", "this emulator build does not run on this system")
    root = state_root()
    if installer.installed_version(root, emu) == emu.version:
        return CommandResult({"emulator": emu.id, "version": emu.version, "state": "installed"}, f"{emu.name} {emu.version} is already installed")
    try:
        ensure_dir(root)
    except InstallError as exc:
        raise LudexError(exc.code, exc.message) from None
    start_service(ctx.conn, "emulators", f"install-{emu.id}", [sys.executable, "-m", "ludex_emulators", "install", emu.id], cwd=root, settle=0.5)
    return CommandResult(
        {"emulator": emu.id, "version": emu.version, "state": "installing"},
        f"installing {emu.name} {emu.version} in the background (see Jobs); it asks for your own BIOS on first start",
    )


def _remove(ctx: CommandContext, args: Sequence[str]) -> CommandResult:
    emu = _emulator(args, "remove")
    try:
        removed = installer.remove(state_root(), emu)
    except InstallError as exc:
        raise LudexError(exc.code, exc.message) from None
    return CommandResult({"emulator": emu.id, "removed": removed}, f"removed {emu.name}" if removed else f"{emu.name} is not installed")


def _row(emu: Emulator) -> ViewRow:
    root = state_root()
    version = installer.installed_version(root, emu)
    failure = installer.last_failure(root, emu)
    names = ", ".join(s.name for s in _MANIFEST.systems.values() if s.emulator == emu.id)
    actions: tuple[ViewAction, ...] = ()
    if host_platform() != emu.platform:
        status = "unsupported platform"
    elif installer.is_installing(root, emu):
        status = "installing"
    else:
        if version == emu.version:
            status = "installed"
        elif version:
            status = "update available"
        else:
            status = f"failed: {failure}" if failure else "not installed"
        if version is None:
            actions = (ViewAction("Install", "install", (emu.id,)),)
        else:
            if version != emu.version:
                actions = (ViewAction("Update", "install", (emu.id,)),)
            actions += (ViewAction("Remove", "remove", (emu.id,)),)
    return ViewRow(emu.id, (emu.name, names, emu.version, version or "-", status), actions)


def _emulators_view(settings: Mapping[str, str]) -> ViewTable:
    return ViewTable(
        ("Emulator", "Systems", "Pinned", "Installed", "Status"),
        tuple(_row(e) for _, e in sorted(_MANIFEST.emulators.items())),
    )


PROVIDER = Provider(
    name="emulators",
    help="Installs pinned emulators and launches your ROMs with them",
    config_fields=(),
    commands=(
        Command("install", "install a pinned emulator in the background: install EMULATOR", _install),
        Command("remove", "remove an installed emulator: remove EMULATOR", _remove),
    ),
    views=(View("emulators", "Emulators", _emulators_view),),
)
