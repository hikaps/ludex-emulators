# Repository Guidelines

## Project Overview

`ludex-emulators` is a provider plugin for [ludex](https://github.com/hikaps/ludex). It installs emulators from a bundled, pinned manifest (version, `https` URL, SHA-256, size), scans a user-supplied ROM folder as an owned-games account, and launches ROMs through the installed emulator. First target: PlayStation 2 with PCSX2 (Linux x64 AppImage). Python 3.11+, standard library only at runtime (ludex is not a declared dependency; it is installed beside the plugin).

The plugin contract is specified in the docstrings of `ludex.plugins` (in the ludex repository); it is the source of truth. Requirements and plans are not tracked here.

## Constraints

- Never provide or fetch content: no games, BIOS, firmware, keys or anything copyrighted. The only download is an emulator binary from the URL pinned in the manifest.
- Every download is verified: `https` only (also after redirects), bounded to the pinned size, SHA-256 compared before the file is made executable or moved into place. Never track "latest"; a version bump is a reviewed manifest change, and its checksum is taken from the upstream project's own release page.
- Network only for that download. No telemetry, no hosted component, no credentials.
- Errors reaching ludex carry fixed, secret-free messages; never include URLs with query strings.
- Never write outside the plugin's state folder (`LUDEX_EMULATORS_HOME`, else `$XDG_DATA_HOME/ludex-emulators`, else `~/.local/share/ludex-emulators`), except the ROM folder is only read.

## Planned Layout (`src/ludex_emulators/`)

- `manifest.json` + `manifest.py`: pinned emulator entries and their validation.
- `installer.py`: download, verify, install, remove (stdlib only, injectable opener; also runs as `python -m ludex_emulators install ID`, started by ludex as a service job).
- `roms.py`: ROM scanning and title cleanup. `plugin.py`: exports `PROVIDER` (entry point group `ludex.providers`, name `emulators`): `fetch`, `installed`, `launch_command`, `commands` (`install`, `remove`), `views` (Emulators table with confirmed row actions).
- `scripts/pin.py` (dev only): prints a manifest entry from an upstream release for review.

## Development Commands

Run from the repository root:

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e ".[test]"
python -m pytest --basetemp=/tmp/ludex-emulators-pytest -q
```

For work against a local ludex checkout, install it editable first (`pip install -e ../ludex/packages/core -e ../ludex/packages/cli`). `--basetemp` deletes that directory; do not share it across concurrent runs. No lint, formatter or type-check tool is configured; do not invent one.

## Code Conventions

- Four-space indentation, type hints, `from __future__ import annotations`, `snake_case` functions/modules, `PascalCase` classes, `_private_helpers`. Value records use frozen/slotted dataclasses.
- Pass paths, openers and clocks explicitly; avoid global state. Boundary errors expose stable `.code`/`.message`.
- The installer module imports nothing from ludex, so it runs wherever Python does.

## Testing

- Pytest with `tmp_path`, `monkeypatch`, `capsys`. Tests are offline: inject a fake opener instead of touching the network; never download a real emulator in tests.
- Cover the uncertain edges: checksum or size mismatch, oversize stream, `http` URL or redirect to `http`, interrupted download leaving no partial file, reinstall of an installed version, path traversal in ROM ids, a plugin that fails to import without ludex.

## Workflow

Branching, commits, PRs and releases are in [CONTRIBUTING.md](CONTRIBUTING.md). A change to a command, setting or convention updates README.md or this file in the same PR.

**Never merge a pull request (feature or release) without the maintainer's explicit approval for that PR**, even when CI is green and an earlier PR was approved. Open the PR, wait for CI, report the result and stop; merge only after the maintainer says so. This applies to agents and automation alike.
