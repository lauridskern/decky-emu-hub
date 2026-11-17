"""Emu Hub's own launch scripts for games started from Steam.

Game shortcuts (Steam ROM Manager's, or ROM-Store's made from SRM's parsers)
usually start EmuDeck's `Emulation/tools/launchers/<name>.sh`. Those scripts
`git pull` and source EmuDeck's backend (~/.config/EmuDeck/backend) before
they look for the emulator, and some look in EmuDeck's old places only
(`ryujinx.sh` wants `~/Applications/publish/Ryujinx.sh`). Without EmuDeck's
backend, or with an emulator Emu Hub installed, they end at once and the game
"closes instantly".

Emu Hub's script for an emulator starts it from wherever it is: the AppImage
Emu Hub installs (`~/Applications/<file>`), EmuDeck's other places, any
`~/Applications/<name>*.AppImage`, else the Flathub app. It passes the game
and every argument through unchanged, so a parser's arguments keep working
(`vblank_mode=0 %command% -f -g "${filePath}"` becomes
`vblank_mode=0 <script> -f -g "<game>"`). A failed start is written to
`launch.log` next to the scripts.
"""

from __future__ import annotations

import os
import re
from typing import Any, Dict, List, Optional

from . import catalogue

REL_DIR = ".local/share/emu-hub/launchers"


def _quote(text: str) -> str:
    """Single-quote for sh (shlex is not in Decky's Python; tests/test_imports.py)."""
    return "'" + text.replace("'", "'\"'\"'") + "'"


def folder(home: str) -> str:
    return os.path.join(home, REL_DIR)


def path_for(home: str, emu_id: str) -> str:
    return os.path.join(folder(home), f"{emu_id}.sh")


def _stems(emu: Dict[str, Any]) -> List[str]:
    """`^eden.*\\.appimage$` -> "eden": file name starts to search for."""
    out = []
    for pattern in emu.get("detect") or []:
        match = re.match(r"\^([a-z0-9_-]+)", pattern)
        if match and match.group(1) not in out:
            out.append(match.group(1))
    return out


def script(emu: Dict[str, Any]) -> str:
    q = _quote
    files = []
    if emu.get("file"):
        files.append(f"$HOME/Applications/{emu['file']}")
    files += [f"$HOME/{rel}" for rel in emu.get("detect_paths") or []]
    flatpaks = [i for i in (emu.get("flatpak"), emu.get("flatpak_alt")) if i]
    lines = [
        "#!/bin/sh",
        f"# Emu Hub launcher for {emu['name']}: starts it from wherever it is installed and",
        "# passes the game and its arguments through. Written by Emu Hub (Library & BIOS →",
        "# Starting games from Steam); Steam ROM Manager's parsers point here.",
        f'log="$(dirname "$0")/launch.log"',
    ]
    for f in files:
        lines.append(f'if [ -x "{f}" ]; then exec "{f}" "$@"; fi')
        lines.append(f'if [ -f "{f}" ]; then chmod +x "{f}" 2>/dev/null; exec "{f}" "$@"; fi')
    for stem in _stems(emu):
        lines.append(
            f'app=$(find "$HOME/Applications" -maxdepth 1 -iname {q(stem + "*.appimage")} '
            "! -name '*.bak' ! -name '*.part' 2>/dev/null | sort | tail -n 1)"
        )
        lines.append('if [ -n "$app" ]; then chmod +x "$app" 2>/dev/null; exec "$app" "$@"; fi')
    for app_id in flatpaks:
        lines.append(f"if flatpak info {q(app_id)} >/dev/null 2>&1; then exec flatpak run {q(app_id)} \"$@\"; fi")
    lines.append(f'echo "$(date) {emu["name"]} is not installed (Emu Hub found no AppImage or Flathub app)" >> "$log"')
    lines.append("exit 1")
    return "\n".join(lines) + "\n"


def write(home: str, emu_id: str) -> Optional[str]:
    emu = catalogue.get(emu_id)
    if not emu or emu["id"] == "retroarch":
        return None  # RetroArch parsers use ${retroarchpath}, not a launcher
    target = path_for(home, emu_id)
    os.makedirs(folder(home), exist_ok=True)
    tmp = target + ".tmp"
    with open(tmp, "w", encoding="utf-8") as handle:
        handle.write(script(emu))
    os.chmod(tmp, 0o755)
    os.replace(tmp, target)
    return target


def last_failures(home: str, lines: int = 5) -> List[str]:
    try:
        with open(os.path.join(folder(home), "launch.log"), "r", encoding="utf-8", errors="replace") as handle:
            return handle.read().splitlines()[-lines:]
    except OSError:
        return []
