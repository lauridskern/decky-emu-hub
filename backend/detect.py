"""What is installed: Emu Hub's own record, files in ~/Applications, flatpak.

Order of trust for each emulator:
  1. the manifest (installed.json): Emu Hub installed or adopted it, and
     knows the version and release key
  2. a Flathub copy under any of its ids (`flatpak list`)
  3. an AppImage in ~/Applications whose name matches `detect`, or one of
     `detect_paths` (EmuDeck's installs): installed, version unknown

A manifest entry whose file has gone (deleted by hand) no longer counts.
"""

from __future__ import annotations

import os
import re
from typing import Any, Dict, Optional

from .catalogue import EMULATORS, flatpak_ids


def apps_dir(home: str) -> str:
    return os.path.join(home, "Applications")


def find_appimage(emu: Dict[str, Any], home: str) -> Optional[str]:
    folder = apps_dir(home)
    own = os.path.join(folder, emu["file"]) if emu.get("file") else None
    if own and os.path.isfile(own):
        return own
    try:
        names = sorted(os.listdir(folder))
    except OSError:
        names = []
    for pattern in emu.get("detect", []):
        regex = re.compile(pattern, re.I)
        for name in names:
            path = os.path.join(folder, name)
            if regex.search(name) and os.path.isfile(path) and not name.endswith((".bak", ".part")):
                return path
    for rel in emu.get("detect_paths", []):
        path = os.path.join(home, rel)
        if os.path.isfile(path):
            return path
    return None


def detect(emu: Dict[str, Any], home: str, manifest: Dict[str, Any], flatpaks: Dict[str, Dict[str, str]]) -> Optional[Dict[str, Any]]:
    """The installed copy of one emulator, or None."""
    record = manifest.get(emu["id"])
    if record:
        if record.get("method") == "flatpak":
            app = flatpaks.get(record.get("app_id") or "")
            if app:
                return dict(record, version=app.get("version") or record.get("version"),
                            installation=app.get("installation"))
        elif record.get("path") and os.path.isfile(record["path"]):
            return dict(record)
    for app_id in flatpak_ids(emu):
        app = flatpaks.get(app_id)
        if app:
            return {"method": "flatpak", "app_id": app_id, "version": app.get("version") or None,
                    "installation": app.get("installation"), "managed": False, "key": None}
    if emu["method"] == "appimage" or emu.get("detect") or emu.get("detect_paths"):
        path = find_appimage(emu, home)
        if path:
            return {"method": "appimage", "path": path, "version": None, "key": None, "managed": False}
    return None


def detect_all(home: str, manifest: Dict[str, Any], flatpaks: Dict[str, Dict[str, str]]) -> Dict[str, Dict[str, Any]]:
    found = {}
    for emu in EMULATORS:
        copy = detect(emu, home, manifest, flatpaks)
        if copy:
            found[emu["id"]] = copy
    return found
