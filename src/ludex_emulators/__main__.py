"""``python -m ludex_emulators install ID``: what ludex runs as a background install job."""
from __future__ import annotations

import argparse
import sys

from .installer import InstallError, install
from .manifest import ManifestError, load_manifest
from .paths import state_root


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m ludex_emulators")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("install", help="download and install a pinned emulator").add_argument("emulator")
    args = parser.parse_args(argv)
    try:
        manifest = load_manifest()
        emu = manifest.emulators.get(args.emulator)
        if emu is None:
            parser.error("unknown emulator")
        install(state_root(), emu)
    except (InstallError, ManifestError) as exc:
        print(f"error: {exc.message}", file=sys.stderr)
        return 1
    print(f"installed {emu.name} {emu.version}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
