"""Deck presets: the few settings each emulator needs to be usable from Game Mode.

A preset names single keys in the emulator's own config file and sets only
those; everything else in the file stays as the user (or the emulator) left
it. Before the first change the original file is copied to the runtime
folder, and "Restore my config" puts it back (or removes the file if there
was none).

What a preset sets, where the emulator has such a setting:
  * start in fullscreen, no "are you sure?" on exit, no first-run wizard
  * the ROM folder of its console(s) and the library's BIOS folder
  * a resolution scale that is cheap at 1280x800 (2x or 3x native)
  * controller 1 = SDL pad 0 for PCSX2 and DuckStation (the Deck's pad under
    Steam Input), and the pause/quit button combos
  * RetroArch: menu on L3+R3, quit on Start+Select

Key names were checked against EmuDeck's shipped configs (Nov 2026); the
values are EmuDecky's own. UNTESTED ON A DECK: every preset below has only
been checked against those files and in the unit tests.

`create`: the file may be written when it does not exist yet (the emulator
fills in the rest on first start). Emulators that reset an unversioned or
partial file (Ryubing's JSON, RPCS3, Cemu) wait until they have been
started once; the preset is then applied on the next refresh ("waiting").
`create_extra`: keys written only when EmuDecky creates the file (version
stamps the emulator checks, default lists).

Paths are relative to the home folder: `appimage` for the AppImage,
`flatpak` for the Flathub copy. Values may use {roms}, {bios}, {saves},
{roms:<console>} and {home}.
"""

from __future__ import annotations

import json
import os
import shutil
import time
from typing import Any, Dict, List, Optional

from . import configfmt
from .library import bios_dir, roms_dir, saves_dir

# Folder names EmuDeck uses where ROM-Store's differ. In an EmuDeck library
# the existing folder wins, so presets point at the games already there.
FOLDER_ALIASES: Dict[str, List[str]] = {
    "gc": ["gamecube", "ngc"],
    "3ds": ["n3ds"],
    "arcades": ["arcade", "fbneo"],
    "dreamcast": ["dc"],
    "genesis": ["megadrive"],
    "psvita": ["vita"],
}

_PAD_PS = {
    "Up": "SDL-0/DPadUp", "Right": "SDL-0/DPadRight", "Down": "SDL-0/DPadDown", "Left": "SDL-0/DPadLeft",
    "Triangle": "SDL-0/Y", "Circle": "SDL-0/B", "Cross": "SDL-0/A", "Square": "SDL-0/X",
    "Select": "SDL-0/Back", "Start": "SDL-0/Start",
    "L1": "SDL-0/LeftShoulder", "R1": "SDL-0/RightShoulder", "L2": "SDL-0/+LeftTrigger", "R2": "SDL-0/+RightTrigger",
    "L3": "SDL-0/LeftStick", "R3": "SDL-0/RightStick",
    "LUp": "SDL-0/-LeftY", "LRight": "SDL-0/+LeftX", "LDown": "SDL-0/+LeftY", "LLeft": "SDL-0/-LeftX",
    "RUp": "SDL-0/-RightY", "RRight": "SDL-0/+RightX", "RDown": "SDL-0/+RightY", "RLeft": "SDL-0/-RightX",
    "LargeMotor": "SDL-0/LargeMotor", "SmallMotor": "SDL-0/SmallMotor",
}

_DOLPHIN_FILES = lambda app: [  # noqa: E731
    {
        "path": {"flatpak": f".var/app/{app}/config/dolphin-emu/Dolphin.ini"},
        "format": "ini",
        "create": True,
        "sep": " = ",
        "set": {
            "Analytics": {"PermissionAsked": "True", "Enabled": "False"},
            "Display": {"Fullscreen": "True"},
            "Interface": {"ConfirmStop": "False"},
            "General": {"ISOPaths": "2", "ISOPath0": "{roms:gc}", "ISOPath1": "{roms:wii}", "RecursiveISOPaths": "True"},
        },
    },
    {
        "path": {"flatpak": f".var/app/{app}/config/dolphin-emu/GFX.ini"},
        "format": "ini",
        "create": True,
        "sep": " = ",
        "set": {"Settings": {"InternalResolution": "2"}},
    },
]

PRESETS: Dict[str, Dict[str, Any]] = {
    # UNTESTED ON A DECK
    "pcsx2": {
        "summary": "Fullscreen, PS2 folder and BIOS, 2x resolution, pad 1 on the Deck's controls, Select+R3 pause menu, Select+Start quit.",
        "files": [{
            "path": {"appimage": ".config/PCSX2/inis/PCSX2.ini",
                     "flatpak": ".var/app/net.pcsx2.PCSX2/config/PCSX2/inis/PCSX2.ini"},
            "format": "ini",
            "create": True,
            "sep": " = ",
            # PCSX2 resets a file without its settings version to defaults.
            "create_extra": {"UI": {"SettingsVersion": "1"}},
            "set": {
                "UI": {"SetupWizardIncomplete": "false", "StartFullscreen": "true", "ConfirmShutdown": "false",
                       "HideMouseCursor": "true"},
                "Folders": {"Bios": "{bios}"},
                "GameList": {"RecursivePaths": "{roms:ps2}"},
                "EmuCore/GS": {"upscale_multiplier": "2"},
                "InputSources": {"SDL": "true"},
                "Pad1": dict({"Type": "DualShock2", "Analog": "SDL-0/Guide"}, **_PAD_PS),
                "Hotkeys": {"OpenPauseMenu": "SDL-0/Back & SDL-0/RightStick", "ShutdownVM": "SDL-0/Back & SDL-0/Start"},
            },
        }],
    },
    # UNTESTED ON A DECK
    "duckstation": {
        "summary": "Fullscreen, PlayStation folder and BIOS, 3x resolution, pad 1 on the Deck's controls, Select+R3 pause menu, Select+Start quit.",
        "files": [{
            "path": {"appimage": ".local/share/duckstation/settings.ini",
                     "flatpak": ".var/app/org.duckstation.DuckStation/data/duckstation/settings.ini"},
            "format": "ini",
            "create": True,
            "sep": " = ",
            "create_extra": {"Main": {"SettingsVersion": "3"}},
            "set": {
                "Main": {"SetupWizardIncomplete": "false", "StartFullscreen": "true", "ConfirmPowerOff": "false"},
                "BIOS": {"SearchDirectory": "{bios}"},
                "GameList": {"RecursivePaths": "{roms:psx}"},
                "GPU": {"ResolutionScale": "3"},
                "InputSources": {"SDL": "true"},
                "Pad1": dict({"Type": "AnalogController"},
                             **{k: v for k, v in _PAD_PS.items()}),
                "Hotkeys": {"OpenPauseMenu": "SDL-0/Back & SDL-0/RightStick", "PowerOff": "SDL-0/Back & SDL-0/Start"},
            },
        }],
    },
    # UNTESTED ON A DECK
    "dolphin": {
        "summary": "Fullscreen, GameCube and Wii folders, 2x resolution, no stop prompt, no analytics question.",
        "files": _DOLPHIN_FILES("org.DolphinEmu.dolphin-emu"),
    },
    # UNTESTED ON A DECK
    "primehack": {
        "summary": "Fullscreen, GameCube and Wii folders, 2x resolution, no stop prompt, no analytics question.",
        "files": _DOLPHIN_FILES("io.github.shiiion.primehack"),
    },
    # UNTESTED ON A DECK
    "ppsspp": {
        "summary": "Fullscreen, opens in the PSP folder, 2x resolution, no first-run screen.",
        "files": [{
            "path": {"appimage": ".config/ppsspp/PSP/SYSTEM/ppsspp.ini",
                     "flatpak": ".var/app/org.ppsspp.PPSSPP/config/ppsspp/PSP/SYSTEM/ppsspp.ini"},
            "format": "ini",
            "create": True,
            "sep": " = ",
            "set": {
                "General": {"FirstRun": "False", "CurrentDirectory": "{roms:psp}"},
                "Graphics": {"FullScreen": "True", "InternalResolution": "2"},
            },
        }],
    },
    # UNTESTED ON A DECK
    "retroarch": {
        "summary": "Fullscreen, library as the start folder, BIOS folder, menu on L3+R3, quit on Start+Select.",
        "files": [{
            "path": {"flatpak": ".var/app/org.libretro.RetroArch/config/retroarch/retroarch.cfg"},
            "format": "cfg",
            "create": True,
            "set": {
                "video_fullscreen": "true",
                "rgui_browser_directory": "{roms}",
                "system_directory": "{bios}",
                "input_menu_toggle_gamepad_combo": "2",
                "input_quit_gamepad_combo": "4",
            },
        }],
    },
    # UNTESTED ON A DECK
    "cemu": {
        "summary": "Fullscreen, Wii U folder in the game list, no update check on start.",
        "files": [{
            "path": {"appimage": ".config/Cemu/settings.xml",
                     "flatpak": ".var/app/info.cemu.Cemu/config/Cemu/settings.xml"},
            "format": "xml",
            "create": False,
            "set": {"fullscreen": "true", "check_update": "false", "GamePaths": ["{roms:wiiu}"]},
        }],
    },
    # UNTESTED ON A DECK
    "rpcs3": {
        "summary": "Games start in fullscreen, RPCS3 closes with the game.",
        "files": [{
            "path": {"appimage": ".config/rpcs3/config.yml",
                     "flatpak": ".var/app/net.rpcs3.RPCS3/config/rpcs3/config.yml"},
            "format": "yaml",
            "create": False,
            "set": {"Miscellaneous": {"Start games in fullscreen mode": True,
                                      "Exit RPCS3 when process finishes": True}},
        }],
    },
    # UNTESTED ON A DECK
    "azahar": {
        "summary": "Fullscreen, no close prompt, 3DS folder in the game list.",
        "files": [{
            "path": {"appimage": ".config/azahar-emu/qt-config.ini",
                     "flatpak": ".var/app/org.azahar_emu.Azahar/config/azahar-emu/qt-config.ini"},
            "format": "ini",
            "create": True,
            "sep": "=",
            "create_extra": {"UI": {
                "Paths\\gamedirs\\1\\path": "INSTALLED",
                "Paths\\gamedirs\\2\\path": "SYSTEM",
                "Paths\\gamedirs\\3\\path": "{roms:3ds}",
                "Paths\\gamedirs\\3\\deep_scan": "false",
                "Paths\\gamedirs\\3\\expanded": "true",
                "Paths\\gamedirs\\size": "3",
            }},
            "set": {"UI": {
                "fullscreen": "true", "fullscreen\\default": "false",
                "confirmClose": "false", "confirmClose\\default": "false",
            }},
        }],
    },
    # UNTESTED ON A DECK
    "ryubing": {
        "summary": "Fullscreen, Switch folder in the game list, no exit prompt, no update check, docked mode.",
        "files": [{
            "path": {"appimage": ".config/Ryujinx/Config.json",
                     "flatpak": ".var/app/io.github.ryubing.Ryujinx/config/Ryujinx/Config.json"},
            "format": "json",
            "create": False,
            "set": {"start_fullscreen": True, "show_confirm_exit": False, "check_updates_on_start": False,
                    "docked_mode": True, "game_dirs": ["{roms:switch}"]},
        }],
    },
    # UNTESTED ON A DECK
    "xemu": {
        "summary": "No welcome screen, no boot animation, MCPX boot ROM from the BIOS folder.",
        "files": [{
            "path": {"appimage": ".local/share/xemu/xemu/xemu.toml",
                     "flatpak": ".var/app/app.xemu.xemu/data/xemu/xemu/xemu.toml"},
            "format": "toml",
            "create": True,
            "set": {
                "general": {"show_welcome": False},
                "general.misc": {"skip_boot_anim": True},
                "sys.files": {"bootrom_path": "{bios}/mcpx_1.0.bin"},
            },
        }],
    },
    # UNTESTED ON A DECK
    "flycast": {
        "summary": "Dreamcast folder as the content folder.",
        "files": [{
            "path": {"appimage": ".config/flycast/emu.cfg",
                     "flatpak": ".var/app/org.flycast.Flycast/config/flycast/emu.cfg"},
            "format": "ini",
            "create": True,
            "sep": " = ",
            "set": {"config": {"Dreamcast.ContentPath": "{roms:dreamcast}"}},
        }],
    },
}


def console_dir(root: str, console: str) -> str:
    """roms/<console>, or the EmuDeck name of it when that folder exists instead."""
    path = roms_dir(root, console)
    if os.path.isdir(path):
        return path
    for alias in FOLDER_ALIASES.get(console, []):
        candidate = os.path.join(roms_dir(root), alias)
        if os.path.isdir(candidate):
            return candidate
    return path


def fill(value: Any, root: str, home: str) -> Any:
    if isinstance(value, bool) or value is None or isinstance(value, (int, float)):
        return value
    if isinstance(value, list):
        return [fill(v, root, home) for v in value]
    if isinstance(value, dict):
        return {k: fill(v, root, home) for k, v in value.items()}
    text = str(value)
    if "{roms:" in text:
        start = text.index("{roms:")
        end = text.index("}", start)
        console = text[start + 6:end]
        text = text[:start] + console_dir(root, console) + text[end + 1:]
    return (text.replace("{roms}", roms_dir(root)).replace("{bios}", bios_dir(root))
            .replace("{saves}", saves_dir(root)).replace("{home}", home))


def _apply_format(fmt: str, text: str, updates: Any, sep: Optional[str]) -> str:
    if fmt == "ini":
        return configfmt.ini_set(text, updates, sep=None if text.strip() else sep)
    if fmt == "toml":
        return configfmt.toml_set(text, updates)
    if fmt == "cfg":
        return configfmt.cfg_set(text, updates)
    if fmt == "json":
        return configfmt.json_set(text, updates)
    if fmt == "xml":
        return configfmt.xml_set(text, updates)
    if fmt == "yaml":
        return configfmt.yaml_set(text, updates)
    raise ValueError(fmt)


def _read_back(fmt: str, text: str, updates: Any) -> bool:
    """True when every key of the preset has its value in the file."""
    if fmt in ("ini", "toml", "yaml"):
        get = {"ini": configfmt.ini_get, "toml": configfmt.toml_get, "yaml": configfmt.yaml_get}[fmt]
        return all(configfmt.same(get(text, section, key), wanted)
                   for section, values in updates.items() for key, wanted in values.items())
    if fmt == "cfg":
        return all(configfmt.same(configfmt.cfg_get(text, key), wanted) for key, wanted in updates.items())
    if fmt == "json":
        return all(configfmt.same(configfmt.json_get(text, key), wanted) for key, wanted in updates.items())
    if fmt == "xml":
        return all(configfmt.same(configfmt.xml_get(text, key), wanted) for key, wanted in updates.items())
    return False


def files_for(preset_id: str, method: str, home: str) -> List[Dict[str, Any]]:
    preset = PRESETS.get(preset_id)
    if not preset:
        return []
    out = []
    for spec in preset["files"]:
        rel = spec["path"].get(method)
        if rel:
            out.append(dict(spec, abs=os.path.join(home, rel)))
    return out


def _read(path: str) -> str:
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as handle:
            return handle.read()
    except OSError:
        return ""


def _write(path: str, text: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = f"{path}.emudecky-tmp"
    with open(tmp, "w", encoding="utf-8") as handle:
        handle.write(text)
    os.replace(tmp, path)


def status(preset_id: Optional[str], method: str, home: str, root: str) -> str:
    """"none" (no preset), "applied", "partial" (some keys differ: never applied,
    changed by the user or reset by the emulator), "waiting" (the emulator has
    to be started once first) or "ready" (can be applied now)."""
    files = files_for(preset_id or "", method, home)
    if not files:
        return "none"
    states = []
    for spec in files:
        if not os.path.isfile(spec["abs"]):
            states.append("ready" if spec.get("create") else "waiting")
            continue
        text = _read(spec["abs"])
        try:
            ok = _read_back(spec["format"], text, fill(spec["set"], root, home))
        except Exception:  # an unreadable file is "not applied", never a crash
            ok = False
        states.append("applied" if ok else "partial")
    if all(s == "applied" for s in states):
        return "applied"
    if "waiting" in states:
        return "waiting"
    if all(s == "ready" for s in states):
        return "ready"
    return "partial"


class Backups:
    """Originals of files a preset changed, one folder per emulator."""

    def __init__(self, folder: str) -> None:
        self.folder = folder

    def _meta_path(self, emu_id: str) -> str:
        return os.path.join(self.folder, emu_id, "meta.json")

    def meta(self, emu_id: str) -> Dict[str, Any]:
        try:
            with open(self._meta_path(emu_id), "r", encoding="utf-8") as handle:
                data = json.load(handle)
            return data if isinstance(data, dict) else {}
        except (OSError, ValueError):
            return {}

    def has(self, emu_id: str) -> bool:
        return bool(self.meta(emu_id))

    def keep(self, emu_id: str, path: str) -> None:
        """Copy `path` away once; later changes never replace the original."""
        meta = self.meta(emu_id)
        if path in meta:
            return
        os.makedirs(os.path.join(self.folder, emu_id), exist_ok=True)
        entry: Dict[str, Any] = {"existed": os.path.isfile(path), "at": time.time()}
        if entry["existed"]:
            name = f"{len(meta)}-{os.path.basename(path)}"
            shutil.copy2(path, os.path.join(self.folder, emu_id, name))
            entry["copy"] = name
        meta[path] = entry
        with open(self._meta_path(emu_id), "w", encoding="utf-8") as handle:
            json.dump(meta, handle, indent=2)

    def restore(self, emu_id: str) -> Dict[str, Any]:
        meta = self.meta(emu_id)
        if not meta:
            return {"ok": False, "error": "There is no saved config to go back to."}
        restored = []
        for path, entry in meta.items():
            try:
                if entry.get("existed") and entry.get("copy"):
                    os.makedirs(os.path.dirname(path), exist_ok=True)
                    shutil.copy2(os.path.join(self.folder, emu_id, entry["copy"]), path)
                elif os.path.isfile(path):
                    os.remove(path)
                restored.append(path)
            except OSError as error:
                return {"ok": False, "error": f"{path}: {error.strerror or error}"}
        shutil.rmtree(os.path.join(self.folder, emu_id), ignore_errors=True)
        return {"ok": True, "files": restored}


def apply(preset_id: Optional[str], emu_id: str, method: str, home: str, root: str, backups: Backups) -> Dict[str, Any]:
    files = files_for(preset_id or "", method, home)
    if not files:
        return {"ok": False, "state": "none", "error": "There is no Deck preset for this emulator yet."}
    waiting = [spec for spec in files if not os.path.isfile(spec["abs"]) and not spec.get("create")]
    if waiting:
        return {"ok": False, "state": "waiting",
                "error": "Start the emulator once, then apply the Deck settings (it writes its config on first start)."}
    written = []
    for spec in files:
        path = spec["abs"]
        existed = os.path.isfile(path)
        text = _read(path)
        updates = fill(spec["set"], root, home)
        if not existed and spec.get("create_extra"):
            extra = fill(spec["create_extra"], root, home)
            text = _apply_format(spec["format"], text, extra, spec.get("sep"))
        try:
            new = _apply_format(spec["format"], text, updates, spec.get("sep"))
        except Exception as error:  # a file we cannot parse is left alone
            return {"ok": False, "state": "partial", "error": f"{os.path.basename(path)} could not be read ({error})"}
        try:
            backups.keep(emu_id, path)
            _write(path, new)
        except OSError as error:
            return {"ok": False, "state": "partial", "error": f"{path}: {error.strerror or error}"}
        written.append(path)
    return {"ok": True, "state": "applied", "files": written}
