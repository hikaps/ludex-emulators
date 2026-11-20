# ludex-emulators

A [ludex](https://github.com/hikaps/ludex) plugin that installs pinned emulators and launches your ROMs with them. First target: PlayStation 2 with PCSX2 on Linux.

Status: emulator install and the Emulators view work; the ROM account and launch are not in yet.

## v1 scope

- A bundled, pinned manifest: per emulator a version, an `https` download URL, a SHA-256 and a size. Downloads that do not match are refused.
- `ludex emulators install ID` / `remove ID` (also as confirmed row actions in an Emulators view), installed under the plugin's state folder, one folder per emulator and version. The install runs as a background job. PCSX2 asks for your own BIOS on its first start; the plugin never handles BIOS files.
  Only Linux x86_64 is supported (PCSX2 AppImage); other systems show `unsupported platform`.
- A ROM account (`folder`): scans `.iso`, `.chd`, `.cso` and `.gz`, one game per file.
- Launch through the installed emulator in fullscreen; per-game arguments and environment come from ludex's launch options.

## What it does not do

It never downloads BIOS, firmware, keys or games. You supply those. It only downloads the emulator itself, from the URL and checksum pinned in the manifest.

## Install (once it has features)

```sh
ludex plugin add git+https://github.com/hikaps/ludex-emulators   # runs with your permissions
```

Needs `ludex-core>=0.62.0`.

If the AppImage cannot mount (no FUSE), set `APPIMAGE_EXTRACT_AND_RUN=1` in the game's launch options.

## Development

See [AGENTS.md](AGENTS.md) and [CONTRIBUTING.md](CONTRIBUTING.md). License: GPL-3.0-or-later.
