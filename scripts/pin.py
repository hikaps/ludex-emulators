#!/usr/bin/env python3
"""Dev only: print a manifest entry from an upstream GitHub release, for review.

Usage: python scripts/pin.py OWNER/REPO TAG ASSET_REGEX
Cross-check the printed checksum against the project's own release page before pasting it into manifest.json.
"""
from __future__ import annotations

import json
import re
import sys
import urllib.request

_MAX = 1024 * 1024


def main(argv: list[str]) -> int:
    if len(argv) != 3 or not re.fullmatch(r"[\w.-]+/[\w.-]+", argv[0]) or not re.fullmatch(r"[\w.+-]+", argv[1]):
        print("usage: pin.py OWNER/REPO TAG ASSET_REGEX", file=sys.stderr)
        return 2
    repo, tag, pattern = argv
    with urllib.request.urlopen(f"https://api.github.com/repos/{repo}/releases/tags/{tag}", timeout=30) as response:
        release = json.loads(response.read(_MAX))
    assets = [a for a in release.get("assets", []) if re.search(pattern, a.get("name", ""))]
    if len(assets) != 1:
        print("no single matching asset", file=sys.stderr)
        return 1
    asset = assets[0]
    digest = asset.get("digest") or ""
    if not digest.startswith("sha256:"):
        print("release has no digest; take the checksum from the release page", file=sys.stderr)
        return 1
    print(json.dumps({
        "version": tag.removeprefix("v"), "url": asset["browser_download_url"], "size": asset["size"],
        "sha256": digest.removeprefix("sha256:"), "source": release["html_url"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
