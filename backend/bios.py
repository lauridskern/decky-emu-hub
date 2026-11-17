"""Which consoles need system files, and whether this Deck has them.

Emu Hub never downloads BIOS files, firmware or keys. It says which console
needs one, which file names the emulators look for and where they go, and
checks whether a matching file is in place. File names follow ROM-Store's
backend/bios.py (RetroArch, DuckStation, PCSX2, Flycast in `bios/`).

Some emulators keep their system files in their own data folder instead
(RPCS3's installed firmware, Ryubing's keys): `home_paths` are checked there,
relative to the home folder, for the AppImage and the Flathub copy.
"""

from __future__ import annotations

import os
import re
from typing import Any, Dict, List

BIOS: Dict[str, Dict[str, Any]] = {
    "psx": {
        "label": "PlayStation BIOS",
        "any_of": ["scph5501.bin", "scph5500.bin", "scph5502.bin", "scph1001.bin", "scph7001.bin", "scph101.bin"],
    },
    "ps2": {
        "label": "PlayStation 2 BIOS",
        # PS2 models have five digits (SCPH-70012, scph39001); PS1 dumps
        # (scph5501.bin) must not count.
        "pattern": r"(scph-?\d{5}|ps2).*\.bin$",
        "hint": "any PS2 BIOS dump (.bin) for PCSX2",
    },
    "ps3": {
        "label": "PS3 system software",
        "home_paths": [".config/rpcs3/dev_flash/vsh/module/vsh.self",
                       ".var/app/net.rpcs3.RPCS3/config/rpcs3/dev_flash/vsh/module/vsh.self"],
        "hint": "install PS3UPDAT.PUP from inside RPCS3 (File → Install Firmware)",
    },
    "switch": {
        "label": "Switch keys",
        "home_paths": [".config/Ryujinx/system/prod.keys",
                       ".var/app/io.github.ryubing.Ryujinx/config/Ryujinx/system/prod.keys"],
        "hint": "prod.keys from your own Switch, then firmware from inside Ryubing",
    },
    "xbox": {
        "label": "Xbox MCPX boot ROM",
        "any_of": ["mcpx_1.0.bin"],
        "hint": "also a BIOS image and a hard disk image, chosen in xemu's settings",
    },
    "saturn": {"label": "Saturn BIOS", "any_of": ["sega_101.bin", "mpr-17933.bin", "saturn_bios.bin"]},
    "segacd": {"label": "Sega CD BIOS", "any_of": ["bios_CD_U.bin", "bios_CD_E.bin", "bios_CD_J.bin"]},
    "pcengine": {
        "label": "PC Engine CD system card",
        "any_of": ["syscard3.pce"],
        "optional": True,
        "hint": "only for CD games",
    },
    "neogeo": {"label": "Neo Geo BIOS", "any_of": ["neogeo.zip"]},
    "dreamcast": {
        "label": "Dreamcast BIOS",
        "any_of": ["dc/dc_boot.bin", "dc_boot.bin"],
        "optional": True,
        "hint": "Flycast runs most games without it",
    },
    "nds": {
        "label": "DS BIOS and firmware",
        "any_of": ["bios7.bin", "bios9.bin", "firmware.bin"],
        "optional": True,
        "hint": "melonDS runs most games without them",
    },
    "gba": {
        "label": "Game Boy Advance BIOS",
        "any_of": ["gba_bios.bin"],
        "optional": True,
        "hint": "RetroArch's mGBA runs games without it",
    },
}


def _present(folder: str, name: str) -> bool:
    """Case-insensitive, since emulators on Linux disagree on case."""
    path = os.path.join(folder, name)
    if os.path.isfile(path):
        return True
    parent, base = os.path.split(path)
    try:
        return any(entry.lower() == base.lower() for entry in os.listdir(parent))
    except OSError:
        return False


def check(console: str, bios_folder: str, home: str) -> Dict[str, Any]:
    spec = BIOS[console]
    found = None
    if spec.get("pattern"):
        pattern = re.compile(spec["pattern"], re.I)
        try:
            found = next((os.path.join(bios_folder, n) for n in sorted(os.listdir(bios_folder)) if pattern.search(n)), None)
        except OSError:
            found = None
    for name in spec.get("any_of", []):
        if found:
            break
        if _present(bios_folder, name):
            found = os.path.join(bios_folder, name)
    for rel in spec.get("home_paths", []):
        if found:
            break
        path = os.path.join(home, rel)
        if os.path.isfile(path):
            found = path
    return {
        "console": console,
        "label": spec["label"],
        "files": spec.get("any_of", []),
        "hint": spec.get("hint"),
        "optional": bool(spec.get("optional")),
        "found": found,
        "folder": bios_folder if not spec.get("home_paths") else None,
    }


def report(consoles: List[str], bios_folder: str, home: str) -> List[Dict[str, Any]]:
    """Status for each console in `consoles` that needs something."""
    seen = []
    out = []
    for console in consoles:
        if console in BIOS and console not in seen:
            seen.append(console)
            out.append(check(console, bios_folder, home))
    return out
