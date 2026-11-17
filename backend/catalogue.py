"""The emulators Emu Hub knows, one entry each.

Every entry says where the emulator comes from and how it is installed:

  method "appimage"  an AppImage from the project's own releases, saved to
                     ~/Applications/<file> (EmuDeck's place and file names, so
                     an EmuDeck install is found and updated in place)
  method "flatpak"   a Flathub app, installed with `flatpak install --user`

`source` is where new versions come from:

  {"type": "github", "repo": "owner/name", "asset": regex}
  {"type": "forgejo", "api": "https://host/api/v1/repos/owner/name", "asset": regex}
  {"type": "flathub"}  (the app id is `flatpak`)

`zip_member` is set when the AppImage ships inside a zip. `rolling` marks a
release that keeps one tag ("latest", "continuous") and replaces its files:
the version shown is the build date, and a change of the file is an update.

`flatpak_alt` is the Flathub id of the same emulator, so a copy installed from
Flathub (by EmuDeck, Discover or by hand) is found and updated through
flatpak instead of being installed a second time.

`detect` are file name patterns (case-insensitive) in ~/Applications that
mean "already installed", e.g. by EmuDeck. `detect_paths` are exact paths
below the home folder for installs that are not a single AppImage.

Sources were checked live on 2026-11-17 (see tools/check_sources.py and the
recorded releases in tests/fixtures/releases/).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

FLATHUB_REPO = "https://dl.flathub.org/repo/flathub.flatpakrepo"

EMULATORS: List[Dict[str, Any]] = [
    {
        "id": "retroarch",
        "name": "RetroArch",
        "blurb": "One front end for most retro systems, through its cores.",
        "consoles": ["nes", "snes", "n64", "gb", "gbc", "gba", "genesis", "mastersystem", "gamegear",
                     "segacd", "saturn", "psx", "pcengine", "neogeo", "atari2600", "arcades"],
        "method": "flatpak",
        "flatpak": "org.libretro.RetroArch",
        "source": {"type": "flathub"},
        "detect": [r"^retroarch.*\.appimage$"],
        "preset": "retroarch",
    },
    {
        "id": "dolphin",
        "name": "Dolphin",
        "blurb": "GameCube and Wii.",
        "consoles": ["gc", "wii"],
        "method": "flatpak",
        "flatpak": "org.DolphinEmu.dolphin-emu",
        "source": {"type": "flathub"},
        "detect": [],
        "preset": "dolphin",
    },
    {
        "id": "pcsx2",
        "name": "PCSX2",
        "blurb": "PlayStation 2.",
        "consoles": ["ps2"],
        "method": "appimage",
        "file": "pcsx2-Qt.AppImage",
        "source": {"type": "github", "repo": "PCSX2/pcsx2", "asset": r"-linux-appimage-x64-Qt\.AppImage$"},
        "flatpak_alt": "net.pcsx2.PCSX2",
        "detect": [r"^pcsx2.*\.appimage$"],
        "preset": "pcsx2",
    },
    {
        "id": "duckstation",
        "name": "DuckStation",
        "blurb": "PlayStation.",
        "consoles": ["psx"],
        "method": "appimage",
        "file": "DuckStation.AppImage",
        "source": {"type": "github", "repo": "stenzek/duckstation", "asset": r"^DuckStation-x64\.AppImage$"},
        "rolling": True,
        # Flathub's DuckStation is end-of-life; an old copy is still found.
        "flatpak_alt": "org.duckstation.DuckStation",
        "detect": [r"^duckstation.*\.appimage$"],
        "preset": "duckstation",
    },
    {
        "id": "ppsspp",
        "name": "PPSSPP",
        "blurb": "PlayStation Portable.",
        "consoles": ["psp"],
        "method": "appimage",
        "file": "PPSSPP.AppImage",
        "source": {"type": "github", "repo": "hrydgard/ppsspp", "asset": r"-anylinux-x86_64\.AppImage$"},
        "flatpak_alt": "org.ppsspp.PPSSPP",
        "detect": [r"^ppsspp.*\.appimage$"],
        "preset": "ppsspp",
    },
    {
        "id": "cemu",
        "name": "Cemu",
        "blurb": "Wii U.",
        "consoles": ["wiiu"],
        "method": "appimage",
        "file": "Cemu.AppImage",
        "source": {"type": "github", "repo": "cemu-project/Cemu", "asset": r"^Cemu-.*-x86_64\.AppImage$"},
        "flatpak_alt": "info.cemu.Cemu",
        "detect": [r"^cemu.*\.appimage$"],
        "preset": "cemu",
    },
    {
        "id": "rpcs3",
        "name": "RPCS3",
        "blurb": "PlayStation 3. Needs the PS3 system software, installed from inside RPCS3.",
        "consoles": ["ps3"],
        "method": "appimage",
        "file": "rpcs3.AppImage",
        # Linux builds are published in a separate repository, one release per build.
        "source": {"type": "github", "repo": "RPCS3/rpcs3-binaries-linux", "asset": r"_linux64\.AppImage$",
                   "version_from": "name"},
        "flatpak_alt": "net.rpcs3.RPCS3",
        "detect": [r"^rpcs3.*\.appimage$"],
        "preset": "rpcs3",
    },
    {
        "id": "azahar",
        "name": "Azahar",
        "blurb": "Nintendo 3DS (the successor of Citra and Lime3DS).",
        "consoles": ["3ds"],
        "method": "appimage",
        "file": "azahar.AppImage",
        "source": {"type": "github", "repo": "azahar-emu/azahar", "asset": r"^azahar\.AppImage$"},
        "flatpak_alt": "org.azahar_emu.Azahar",
        "detect": [r"^azahar.*\.appimage$"],
        "preset": "azahar",
    },
    {
        "id": "melonds",
        "name": "melonDS",
        "blurb": "Nintendo DS.",
        "consoles": ["nds"],
        "method": "appimage",
        "file": "melonDS.AppImage",
        "source": {"type": "github", "repo": "melonDS-emu/melonDS", "asset": r"-appimage-x86_64\.zip$"},
        "zip_member": r"\.AppImage$",
        "flatpak_alt": "net.kuribo64.melonDS",
        "detect": [r"^melonds.*\.appimage$"],
        "preset": None,
    },
    {
        "id": "ryubing",
        "name": "Ryubing",
        "blurb": "Nintendo Switch (the maintained Ryujinx). Needs your own keys and firmware.",
        "consoles": ["switch"],
        "method": "appimage",
        "file": "Ryujinx.AppImage",
        # Ryubing left GitHub; its Forgejo instance has a Gitea-style API.
        "source": {"type": "forgejo", "api": "https://git.ryujinx.app/api/v1/repos/projects/Ryubing",
                   "asset": r"-x64\.AppImage$"},
        "flatpak_alt": "io.github.ryubing.Ryujinx",
        "detect": [r"^ryujinx.*\.appimage$", r"^ryubing.*\.appimage$"],
        "detect_paths": ["Applications/publish/Ryujinx"],
        "preset": "ryubing",
    },
    {
        "id": "eden",
        "name": "Eden",
        "blurb": "Nintendo Switch (from the yuzu family). Needs your own keys and firmware.",
        "consoles": ["switch"],
        "method": "appimage",
        "file": "Eden.AppImage",
        # Eden's GitHub releases repository was taken down (DMCA, March 2026);
        # it publishes from its own Forgejo, files served by stable.eden-emu.dev.
        # amd64 builds need x86-64-v3, which the Deck's Zen 2 has; "legacy" is
        # for older CPUs. clang-pgo is the build Eden recommends.
        "source": {"type": "forgejo", "api": "https://git.eden-emu.dev/api/v1/repos/eden-emu/eden",
                   "asset": r"^Eden-Linux-v[0-9.]+-amd64-clang-pgo\.AppImage$"},
        "flatpak_alt": "dev.eden_emu.eden",
        "detect": [r"^eden.*\.appimage$"],
        "preset": "eden",
    },
    {
        "id": "xemu",
        "name": "xemu",
        "blurb": "Original Xbox. Needs your own BIOS, MCPX boot ROM and hard disk image.",
        "consoles": ["xbox"],
        "method": "appimage",
        "file": "xemu.AppImage",
        "source": {"type": "github", "repo": "xemu-project/xemu", "asset": r"^xemu-[0-9.]+-x86_64\.AppImage$"},
        "flatpak_alt": "app.xemu.xemu",
        "detect": [r"^xemu.*\.appimage$"],
        "preset": "xemu",
    },
    {
        "id": "vita3k",
        "name": "Vita3K",
        "blurb": "PlayStation Vita. Needs the Vita firmware, installed from inside Vita3K.",
        "consoles": ["psvita"],
        "method": "appimage",
        "file": "Vita3K.AppImage",
        "source": {"type": "github", "repo": "Vita3K/Vita3K", "asset": r"^Vita3K-x86_64\.AppImage$"},
        "rolling": True,
        "detect": [r"^vita3k.*\.appimage$"],
        "detect_paths": ["Applications/Vita3K/Vita3K"],
        "preset": None,
    },
    {
        "id": "shadps4",
        "name": "shadPS4",
        "blurb": "PlayStation 4 (early; few games run well).",
        "consoles": ["ps4"],
        # The upstream Linux zip is the command-line build; the one with a game
        # list (the Qt launcher) is only published as pre-releases. Flathub
        # ships the launcher.
        "method": "flatpak",
        "flatpak": "net.shadps4.shadPS4",
        "source": {"type": "flathub"},
        "detect": [r"^shadps4.*\.appimage$"],
        "preset": None,
    },
    {
        "id": "flycast",
        "name": "Flycast",
        "blurb": "Dreamcast, NAOMI and Atomiswave.",
        "consoles": ["dreamcast"],
        "method": "appimage",
        "file": "flycast.AppImage",
        "source": {"type": "github", "repo": "flyinghead/flycast", "asset": r"^flycast-x86_64-.*\.AppImage$"},
        "flatpak_alt": "org.flycast.Flycast",
        "detect": [r"^flycast.*\.appimage$"],
        "preset": "flycast",
    },
    {
        "id": "primehack",
        "name": "PrimeHack",
        "blurb": "Dolphin fork for the Metroid Prime Trilogy with aiming controls.",
        "consoles": ["gc", "wii"],
        "method": "flatpak",
        "flatpak": "io.github.shiiion.primehack",
        "source": {"type": "flathub"},
        "detect": [],
        "preset": "primehack",
    },
    {
        "id": "scummvm",
        "name": "ScummVM",
        "blurb": "Classic point-and-click adventures.",
        "consoles": ["scummvm"],
        "method": "flatpak",
        "flatpak": "org.scummvm.ScummVM",
        "source": {"type": "flathub"},
        "detect": [],
        "preset": None,
    },
    {
        "id": "mame",
        "name": "MAME",
        "blurb": "Arcade machines (standalone MAME).",
        "consoles": ["mame"],
        "method": "flatpak",
        "flatpak": "org.mamedev.MAME",
        "source": {"type": "flathub"},
        "detect": [],
        "preset": None,
    },
]

BY_ID: Dict[str, Dict[str, Any]] = {emu["id"]: emu for emu in EMULATORS}


def get(emu_id: str) -> Optional[Dict[str, Any]]:
    return BY_ID.get(emu_id)


def flatpak_ids(emu: Dict[str, Any]) -> List[str]:
    """Every Flathub id this emulator can be installed under."""
    ids = []
    if emu.get("flatpak"):
        ids.append(emu["flatpak"])
    if emu.get("flatpak_alt"):
        ids.append(emu["flatpak_alt"])
    return ids
