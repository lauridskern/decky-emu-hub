#!/usr/bin/env python3
"""Live check: does every emulator still resolve to a downloadable file?

For each GitHub / Forgejo source: ask for the latest release, pick the file
with the catalogue's pattern, and make a 1-byte ranged request for it (no
real download). For each Flathub app: ask Flathub for its current version.

    python3 tools/check_sources.py      # exit 1 if anything failed

Set GITHUB_TOKEN to avoid the anonymous rate limit.
"""

from __future__ import annotations

import os
import sys
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from backend import catalogue, releases  # noqa: E402


def probe(url: str) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": releases.USER_AGENT, "Range": "bytes=0-0"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return f"HTTP {response.status}"


def main() -> int:
    token = os.environ.get("GITHUB_TOKEN")
    failed = 0
    for emu in catalogue.EMULATORS:
        source = emu["source"]["type"]
        try:
            if source == "flathub":
                version = releases.flathub_version(emu["flatpak"], force=True)
                print(f"ok    {emu['id']:12} flathub {emu['flatpak']:30} {version}")
            else:
                info = releases.latest(emu, token=token, force=True)
                status = probe(info["url"])
                print(f"ok    {emu['id']:12} {source:7} {info['version']:22} {info['asset']}  ({info['size'] // 1048576} MB, {status})")
        except Exception as error:
            failed += 1
            print(f"FAIL  {emu['id']:12} {source:7} {error}")
    print(f"\n{len(catalogue.EMULATORS) - failed}/{len(catalogue.EMULATORS)} sources resolve")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
