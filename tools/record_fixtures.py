#!/usr/bin/env python3
"""Record each emulator's latest release (trimmed) for the offline tests.

    python3 tools/record_fixtures.py            # every GitHub / Forgejo source
    python3 tools/record_fixtures.py pcsx2      # one

Writes tests/fixtures/releases/<id>.json. Set GITHUB_TOKEN to avoid the
anonymous rate limit.
"""

from __future__ import annotations

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from backend import catalogue, releases  # noqa: E402

KEEP = ("tag_name", "name", "published_at", "prerelease")
ASSET_KEEP = ("name", "size", "updated_at", "created_at", "browser_download_url")


def main() -> int:
    wanted = set(sys.argv[1:])
    out_dir = os.path.join(ROOT, "tests", "fixtures", "releases")
    os.makedirs(out_dir, exist_ok=True)
    token = os.environ.get("GITHUB_TOKEN")
    for emu in catalogue.EMULATORS:
        if emu["source"]["type"] == "flathub" or (wanted and emu["id"] not in wanted):
            continue
        raw = releases.fetch_json(releases.release_url(emu), token)
        trimmed = {k: raw.get(k) for k in KEEP}
        trimmed["assets"] = [{k: a.get(k) for k in ASSET_KEEP if k in a} for a in raw.get("assets", [])]
        with open(os.path.join(out_dir, f"{emu['id']}.json"), "w", encoding="utf-8") as handle:
            json.dump(trimmed, handle, indent=1)
        print(f"{emu['id']:12} {trimmed['tag_name']}  {len(trimmed['assets'])} files")
    return 0


if __name__ == "__main__":
    sys.exit(main())
