"""Which emulator opens a console's games in Steam.

Steam shortcuts for games are made from Steam ROM Manager's parser
configuration (`userConfigurations.json`, the one EmuDeck sets up), by SRM
itself or by ROM-Store, which does SRM's job from inside Steam. For each ROM
folder (`roms/switch`, ...) the first enabled parser wins, and the parser
names the launcher: EmuDeck's `Emulation/tools/launchers/eden.sh`,
`ryujinx.sh`, RetroArch with a core, or `flatpak run <app id>`.

When several emulators have parsers for one folder (Switch: Eden and
Ryujinx in EmuDeck's default setup), this module says which one is in use
and switches it the way EmuDeck's own emulator choice does: the chosen
emulator's parsers are enabled, every other emulator's parsers for that
folder are disabled. Nothing else in the file changes, and a copy of the
file is kept before every change (`backups/srm/`).

The file is looked for in the same places, in the same order, as ROM-Store's
backend/steam.py (SRM_DIRS), so both plugins always read the same file.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import time
from typing import Any, Dict, List, Optional, Tuple

from . import catalogue

# Same list and order as ROM-Store's backend/steam.py. Keep the two in step.
SRM_DIRS = (
    ".config/steam-rom-manager/userData",
    ".var/app/com.steamgriddb.steam-rom-manager/config/steam-rom-manager/userData",
    "Emulation/tools/srm/userData",
    "EmuDecky/tools/srm/userData",
)
CONFIG = "userConfigurations.json"
KEEP_BACKUPS = 10

# EmuDeck launcher script (Emulation/tools/launchers/<name>.sh) -> Emu Hub id.
LAUNCHERS = {
    "eden": "eden",
    "ryujinx": "ryubing",
    "ryubing": "ryubing",
    "retroarch": "retroarch",
    "dolphin-emu": "dolphin",
    "dolphin": "dolphin",
    "primehack": "primehack",
    "pcsx2-qt": "pcsx2",
    "pcsx2": "pcsx2",
    "duckstation": "duckstation",
    "ppsspp": "ppsspp",
    "cemu": "cemu",
    "cemu-native": "cemu",
    "rpcs3": "rpcs3",
    "azahar": "azahar",
    "citra": "azahar",
    "lime3ds": "azahar",
    "melonds": "melonds",
    "xemu": "xemu",
    "xemu-emu": "xemu",
    "vita3k": "vita3k",
    "shadps4": "shadps4",
    "flycast": "flycast",
    "scummvm": "scummvm",
    "mame": "mame",
}

_ROMS_VAR = re.compile(r"\$\{romsdirglobal\}/+([^/]+)")
_FLATPAK_ID = re.compile(r"\brun\s+(?:--\S+\s+)*([A-Za-z0-9_.-]+\.[A-Za-z0-9_.-]+)")


def find_config(home: str) -> Optional[str]:
    for rel in SRM_DIRS:
        path = os.path.join(home, rel, CONFIG)
        if os.path.isfile(path):
            return path
    return None


def _flatpak_ids() -> Dict[str, str]:
    ids: Dict[str, str] = {}
    for emu in catalogue.EMULATORS:
        for key in ("flatpak", "flatpak_alt"):
            if emu.get(key):
                ids[emu[key].lower()] = emu["id"]
    return ids


def console_of(parser: Dict[str, Any]) -> Optional[str]:
    """The ROM folder a parser reads: `${romsdirglobal}/switch` -> "switch"."""
    rom_dir = str(parser.get("romDirectory") or "")
    match = _ROMS_VAR.search(rom_dir)
    if match:
        return match.group(1).lower()
    rom_dir = rom_dir.rstrip("/")
    if "/roms/" in rom_dir:
        return rom_dir.split("/roms/", 1)[1].split("/", 1)[0].lower() or None
    return None


def emulator_of(parser: Dict[str, Any]) -> Tuple[str, Optional[str], str]:
    """(key, Emu Hub id or None, label) for the program a parser starts."""
    exe = str((parser.get("executable") or {}).get("path") or "")
    args = str(parser.get("executableArgs") or "")
    title = str(parser.get("configTitle") or "")
    label = title.split(" - ", 1)[1].strip() if " - " in title else title
    if "retroarch" in exe.lower():
        return "retroarch", "retroarch", "RetroArch"
    stem = os.path.basename(exe.strip('"')).lower()
    stem = re.sub(r"\.(sh|appimage)$", "", stem)
    if stem == "flatpak":
        match = _FLATPAK_ID.search(args)
        if match:
            emu_id = _flatpak_ids().get(match.group(1).lower())
            if emu_id:
                return emu_id, emu_id, catalogue.get(emu_id)["name"]
            return f"flatpak:{match.group(1)}", None, label or match.group(1)
    emu_id = LAUNCHERS.get(stem)
    if emu_id is None:
        # pcsx2-v2.8.2-linux-appimage-x64-Qt, Eden-Linux-v0.2.1-..., Ryujinx.AppImage
        for name, known in LAUNCHERS.items():
            if stem.startswith(name):
                emu_id = known
                break
    if emu_id:
        return emu_id, emu_id, catalogue.get(emu_id)["name"]
    key = stem or label.lower() or "unknown"
    return f"other:{key}", None, label or stem or "Unknown"


def load(path: str) -> List[Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, list):
        raise ValueError("not a list of parsers")
    return data


def choices(home: str, installed: Dict[str, Any]) -> Dict[str, Any]:
    """Consoles whose games more than one emulator could open.

    `installed`: Emu Hub ids that are on the Deck. "current" is the emulator
    of the first enabled parser for the folder, the one Steam shortcuts use.
    """
    path = find_config(home)
    if not path:
        return {"srm": None, "consoles": []}
    try:
        parsers = load(path)
    except (OSError, ValueError) as error:
        return {"srm": path, "error": f"{os.path.basename(path)} could not be read ({error})", "consoles": []}
    groups: Dict[str, Dict[str, Any]] = {}
    for parser in parsers:
        if not isinstance(parser, dict):
            continue
        console = console_of(parser)
        if not console:
            continue
        key, emu_id, label = emulator_of(parser)
        group = groups.setdefault(console, {"console": console, "options": {}, "current": None})
        option = group["options"].setdefault(key, {
            "key": key, "emu_id": emu_id, "label": label, "parsers": [], "enabled": False,
            "installed": (emu_id in installed) if emu_id else None,
        })
        option["parsers"].append(str(parser.get("configTitle") or ""))
        if not parser.get("disabled"):
            option["enabled"] = True
            if group["current"] is None:
                group["current"] = key
    consoles = []
    for console, group in groups.items():
        if len(group["options"]) < 2:
            continue
        consoles.append({
            "console": console,
            "current": group["current"],
            "options": list(group["options"].values()),
        })
    consoles.sort(key=lambda c: c["console"])
    return {"srm": path, "consoles": consoles}


def _backup(path: str, folder: str) -> str:
    os.makedirs(folder, exist_ok=True)
    target = os.path.join(folder, f"userConfigurations.{time.strftime('%Y%m%d-%H%M%S')}.json")
    shutil.copy2(path, target)
    kept = sorted(n for n in os.listdir(folder) if n.startswith("userConfigurations."))
    for old in kept[:-KEEP_BACKUPS]:
        try:
            os.remove(os.path.join(folder, old))
        except OSError:
            pass
    return target


def choose(home: str, console: str, key: str, backup_dir: str) -> Dict[str, Any]:
    """Make `key` the emulator for `console`'s folder in SRM's parsers."""
    path = find_config(home)
    if not path:
        return {"ok": False, "error": "Steam ROM Manager's settings were not found."}
    try:
        with open(path, "r", encoding="utf-8") as handle:
            raw = handle.read()
        parsers = json.loads(raw)
        if not isinstance(parsers, list):
            raise ValueError("not a list of parsers")
    except (OSError, ValueError) as error:
        return {"ok": False, "error": f"{os.path.basename(path)} could not be read ({error})"}
    mine = [p for p in parsers if isinstance(p, dict) and console_of(p) == console]
    chosen = [p for p in mine if emulator_of(p)[0] == key]
    if not chosen:
        return {"ok": False, "error": f"No Steam ROM Manager parser for {console} starts that emulator."}
    # Keep the user's choice between the chosen emulator's own parsers (a
    # RetroArch core, Cemu's two file types) when one of them is on already.
    keep_states = any(not p.get("disabled") for p in chosen)
    changed = False
    for parser in mine:
        want = (bool(parser.get("disabled")) if keep_states else False) if parser in chosen else True
        if bool(parser.get("disabled")) != want:
            parser["disabled"] = want
            changed = True
    if not changed:
        return {"ok": True, "changed": False, "srm": path}
    try:
        saved = _backup(path, backup_dir)
        indent = 4 if raw.startswith("[\n    ") else 2
        tmp = f"{path}.emu-hub-tmp"
        with open(tmp, "w", encoding="utf-8") as handle:
            json.dump(parsers, handle, indent=indent, ensure_ascii=False)
            handle.write("\n")
        os.replace(tmp, path)
    except OSError as error:
        return {"ok": False, "error": f"Could not write {os.path.basename(path)} ({error})"}
    return {"ok": True, "changed": True, "srm": path, "backup": saved}


def auto_choose(home: str, installed: Dict[str, Any], backup_dir: str) -> List[Dict[str, Any]]:
    """Fix consoles whose games would start an emulator that is not installed.

    Only when the current pick is a known emulator that is missing and an
    installed one has parsers for the folder; a working choice, or one Emu
    Hub cannot judge (a launcher it does not know), is never touched.
    """
    done = []
    for group in choices(home, installed).get("consoles", []):
        current = next((o for o in group["options"] if o["key"] == group["current"]), None)
        if current is None or current["installed"] is not False:
            continue
        alternative = next((o for o in group["options"] if o["installed"]), None)
        if not alternative:
            continue
        result = choose(home, group["console"], alternative["key"], backup_dir)
        if result.get("ok") and result.get("changed"):
            done.append({"console": group["console"], "from": current["label"], "to": alternative["label"]})
    return done
