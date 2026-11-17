"""The game library: where it is, and its console folders.

A library root holds `roms/<console>/`, `bios/` and `saves/`, the layout
EmuDeck uses (`~/Emulation`) and ROM-Store downloads into. EmuDecky's own
default is `~/EmuDecky`; an existing EmuDeck library (in the home folder or
on an SD card) is preferred, so both tools keep using one set of folders.

Console folder names are the ones ROM-Store uses (its backend/systems.py,
`SYSTEMS[key][1]`), so a game ROM-Store downloads lands where the emulator
EmuDecky set up looks for it. Keep the two lists in step.
"""

from __future__ import annotations

import glob
import os
from typing import Dict, List, Optional, Tuple

# key -> (label, folder in roms/). Same folder names as ROM-Store.
CONSOLES: Dict[str, Tuple[str, str]] = {
    "nes": ("NES", "nes"),
    "snes": ("Super Nintendo", "snes"),
    "n64": ("Nintendo 64", "n64"),
    "gb": ("Game Boy", "gb"),
    "gbc": ("Game Boy Color", "gbc"),
    "gba": ("Game Boy Advance", "gba"),
    "nds": ("Nintendo DS", "nds"),
    "3ds": ("Nintendo 3DS", "3ds"),
    "gc": ("GameCube", "gc"),
    "wii": ("Wii", "wii"),
    "wiiu": ("Wii U", "wiiu"),
    "switch": ("Switch", "switch"),
    "genesis": ("Genesis / Mega Drive", "genesis"),
    "mastersystem": ("Master System", "mastersystem"),
    "gamegear": ("Game Gear", "gamegear"),
    "segacd": ("Sega CD", "segacd"),
    "saturn": ("Saturn", "saturn"),
    "dreamcast": ("Dreamcast", "dreamcast"),
    "psx": ("PlayStation", "psx"),
    "ps2": ("PlayStation 2", "ps2"),
    "ps3": ("PlayStation 3", "ps3"),
    "ps4": ("PlayStation 4", "ps4"),
    "psp": ("PSP", "psp"),
    "psvita": ("PS Vita", "psvita"),
    "xbox": ("Xbox", "xbox"),
    "pcengine": ("PC Engine", "pcengine"),
    "neogeo": ("Neo Geo", "neogeo"),
    "atari2600": ("Atari 2600", "atari2600"),
    "arcades": ("Arcade (FinalBurn Neo)", "arcades"),
    "mame": ("Arcade (MAME)", "mame"),
    "scummvm": ("ScummVM", "scummvm"),
}


def label(key: str) -> str:
    return CONSOLES.get(key, (key, key))[0]


def folder(key: str) -> str:
    return CONSOLES.get(key, (key, key))[1]


def candidates(home: str, media_glob: str = "/run/media/*/*") -> List[Dict[str, str]]:
    """Possible library roots, in order of preference.

    An EmuDeck library that already has a roms folder comes first (internal,
    then SD cards), then EmuDecky folders, then the default ~/EmuDecky.
    """
    mounts = sorted(glob.glob(media_glob))
    found: List[Dict[str, str]] = []

    def add(path: str, kind: str, where: str) -> None:
        if path not in [c["path"] for c in found]:
            found.append({"path": path, "kind": kind, "where": where})

    for base, where in [(home, "internal")] + [(m, "sd") for m in mounts]:
        path = os.path.join(base, "Emulation")
        if os.path.isdir(os.path.join(path, "roms")):
            add(path, "emudeck", where)
    for base, where in [(home, "internal")] + [(m, "sd") for m in mounts]:
        path = os.path.join(base, "EmuDecky")
        if os.path.isdir(path):
            add(path, "emudecky", where)
    add(os.path.join(home, "EmuDecky"), "emudecky", "internal")
    return found


def default_root(home: str, media_glob: str = "/run/media/*/*") -> str:
    return candidates(home, media_glob)[0]["path"]


def resolve_root(setting: Optional[str], home: str, media_glob: str = "/run/media/*/*") -> str:
    return setting or default_root(home, media_glob)


def roms_dir(root: str, console: Optional[str] = None) -> str:
    base = os.path.join(root, "roms")
    return os.path.join(base, folder(console)) if console else base


def bios_dir(root: str) -> str:
    return os.path.join(root, "bios")


def saves_dir(root: str) -> str:
    return os.path.join(root, "saves")


def create_folders(root: str) -> Dict[str, object]:
    """Make roms/<console> for every console, bios/ and saves/. Never deletes."""
    made: List[str] = []
    errors: List[str] = []
    paths = [roms_dir(root), bios_dir(root), saves_dir(root)] + [roms_dir(root, key) for key in CONSOLES]
    for path in paths:
        if os.path.isdir(path):
            continue
        try:
            os.makedirs(path, exist_ok=True)
            made.append(path)
        except OSError as error:
            errors.append(f"{path}: {error.strerror or error}")
    return {"ok": not errors, "made": len(made), "errors": errors}


def describe(root: str) -> Dict[str, object]:
    """The root, whether its folders exist, and how many files each console has."""
    consoles = []
    for key, (name, sub) in CONSOLES.items():
        path = roms_dir(root, key)
        count = 0
        exists = os.path.isdir(path)
        if exists:
            try:
                count = sum(1 for entry in os.scandir(path) if not entry.name.startswith(".") and entry.name != "systeminfo.txt")
            except OSError:
                count = 0
        consoles.append({"key": key, "label": name, "folder": sub, "exists": exists, "files": count})
    return {
        "root": root,
        "exists": os.path.isdir(root),
        "roms": roms_dir(root),
        "bios": bios_dir(root),
        "ready": os.path.isdir(roms_dir(root)) and os.path.isdir(bios_dir(root)),
        "consoles": consoles,
    }
