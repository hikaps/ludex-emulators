# ludex-emulators

A [ludex](https://github.com/hikaps/ludex) plugin that installs pinned emulators and launches your ROMs with them. Targets: PlayStation 2 with PCSX2 and, experimentally, Nintendo Switch with Lichii, both on Linux x86_64.

Status: v1 feature-complete (install, ROM account, launch); not yet released.

## v1 scope

- A bundled, pinned manifest: per emulator a version, an `https` download URL, a SHA-256 and a size. Downloads that do not match are refused.
- `ludex emulators install ID` / `remove ID` (also as confirmed row actions in an Emulators view), installed under the plugin's state folder, one folder per emulator and version. The install runs as a background job. PCSX2 asks for your own BIOS on its first start; the plugin never handles BIOS files.
  Only Linux x86_64 is supported (AppImages); other systems show `unsupported platform`.
  Lichii is an experimental Switch/Switch 2 emulator (a fork of Eden/yuzu); it is pinned to one build, needs your own keys and firmware, may not run every game, and may disappear upstream. It has no stop-on-exit option, so close its window when you are done.
- A ROM account (`folder`, `system`): `ps2` scans `.iso`, `.chd`, `.cso` and `.iso.gz`; `switch` scans `.nsp`, `.xci`, `.nsz` and `.xcz`. One game per file.
- Launch through the installed emulator in fullscreen; per-game arguments and environment come from ludex's launch options.

## What it does not do

It never downloads BIOS, firmware, keys or games. You supply those. It only downloads the emulator itself, from the URL and checksum pinned in the manifest.

## Use

```sh
ludex account add emulators ps2 --set folder=~/Roms/ps2 --set system=ps2
ludex import --all
ludex emulators install pcsx2        # or the Emulators view
ludex launch "Game Title"
```

## Install

```sh
ludex plugin add git+https://github.com/hikaps/ludex-emulators   # runs with your permissions
```

Needs `ludex-core>=0.62.0`.

If the AppImage cannot mount (no FUSE), set `APPIMAGE_EXTRACT_AND_RUN=1` in the game's launch options.

## Development

See [AGENTS.md](AGENTS.md) and [CONTRIBUTING.md](CONTRIBUTING.md). License: GPL-3.0-or-later.
