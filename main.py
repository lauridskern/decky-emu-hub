"""Emu Hub - Decky plugin backend.

Installs, updates and sets up emulators from Game Mode: AppImages from the
projects' own releases into ~/Applications, Flathub apps with
`flatpak --user`, a Deck preset for each emulator's config, and the state the
UI shows (installed, version, update available, BIOS in place).

Runs as the deck user (no "root" flag): everything it touches is in the
user's home folder or the user's flatpak installation.
"""

from __future__ import annotations

import os
import sys
from typing import Any, Dict, Optional

PLUGIN_DIR = os.path.dirname(os.path.abspath(__file__))
if PLUGIN_DIR not in sys.path:
    sys.path.insert(0, PLUGIN_DIR)

try:
    import decky  # type: ignore  # Decky Loader >= 3.1
except ImportError:
    try:
        import decky_plugin as decky  # type: ignore  # Decky Loader 3.0
    except ImportError:
        decky = None  # type: ignore  # tests, packaging checks

from backend.service import Service  # noqa: E402
from backend.settings import Settings  # noqa: E402


def _log(message: str) -> None:
    logger = getattr(decky, "logger", None)
    if logger is not None:
        try:
            logger.info(message)
        except Exception:
            pass


def _env(name: str, fallback: str) -> str:
    value = getattr(decky, name, None) if decky is not None else None
    return str(value) if value else fallback


HOME = _env("DECKY_USER_HOME", os.path.expanduser("~"))
SETTINGS_DIR = _env("DECKY_PLUGIN_SETTINGS_DIR", os.path.join(HOME, "homebrew", "settings", "emu-hub"))
RUNTIME_DIR = _env("DECKY_PLUGIN_RUNTIME_DIR", os.path.join(HOME, "homebrew", "data", "emu-hub"))


class Plugin:
    """Decky Loader >= 3.1 instantiates this class; older loaders call the
    methods on the class itself, so every entry point resolves an instance."""

    _instance: Optional["Plugin"] = None

    def __init__(self) -> None:
        emit = getattr(decky, "emit", None) if decky is not None else None
        self.service = Service(Settings(os.path.join(SETTINGS_DIR, "emu-hub.json")), RUNTIME_DIR, HOME, emit)
        Plugin._instance = self

    @classmethod
    def instance(cls) -> "Plugin":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def _svc(cls) -> Service:
        return cls.instance().service

    async def _main(self) -> None:
        service = self._svc()
        await service.start()
        _log(f"Emu Hub started; home {HOME}, library {service.root()}")

    async def _unload(self) -> None:
        await self._svc().stop()
        _log("Emu Hub stopped")

    async def _uninstall(self) -> None:
        pass

    # ----------------------------------------------------------------- state
    async def get_state(self) -> Dict[str, Any]:
        return await self._svc().state()

    async def check_updates(self, force: bool = True) -> Dict[str, Any]:
        return await self._svc().check_updates(force=bool(force))

    # ------------------------------------------------------------------ jobs
    async def install(self, emu_id: str) -> Dict[str, Any]:
        return await self._svc().run(emu_id, "install")

    async def update(self, emu_id: str) -> Dict[str, Any]:
        return await self._svc().run(emu_id, "update")

    async def update_all(self) -> Dict[str, Any]:
        return await self._svc().update_all()

    async def uninstall(self, emu_id: str) -> Dict[str, Any]:
        return await self._svc().run(emu_id, "uninstall")

    async def cancel(self, emu_id: str) -> Dict[str, Any]:
        return await self._svc().cancel(emu_id)

    # --------------------------------------------------------------- configs
    async def apply_preset(self, emu_id: str) -> Dict[str, Any]:
        return await self._svc().apply_preset(emu_id)

    async def restore_config(self, emu_id: str) -> Dict[str, Any]:
        return await self._svc().restore_config(emu_id)

    # ----------------------------------------------------------------- steam
    async def shortcut_plan(self, emu_id: str) -> Dict[str, Any]:
        return await self._svc().shortcut_plan(emu_id)

    async def report_shortcut(self, emu_id: str, appid: Optional[int] = None, made: bool = True) -> Dict[str, Any]:
        return await self._svc().report_shortcut(emu_id, appid, made)

    # ------------------------------------------------- which emulator opens …
    async def emulator_choices(self) -> Dict[str, Any]:
        return await self._svc().emulator_choices()

    async def choose_emulator(self, console: str, key: str) -> Dict[str, Any]:
        return await self._svc().choose_emulator(console, key)

    # --------------------------------------------------------------- library
    async def get_library(self) -> Dict[str, Any]:
        return await self._svc().library_info()

    async def set_library_root(self, path: str = "") -> Dict[str, Any]:
        return await self._svc().set_library_root(path)

    async def create_folders(self) -> Dict[str, Any]:
        return await self._svc().create_folders()

    # -------------------------------------------------------------- settings
    async def get_settings(self) -> Dict[str, Any]:
        return await self._svc().get_settings()

    async def set_settings(self, changes: Dict[str, Any]) -> Dict[str, Any]:
        return await self._svc().set_settings(changes)
