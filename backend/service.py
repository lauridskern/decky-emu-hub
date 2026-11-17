"""Emu Hub's backend: catalogue + what is installed + updates + jobs.

main.py wraps every public coroutine here as a call the UI can make. Blocking
work (flatpak, HTTP, file copies) runs on threads; the event loop only waits.

Runtime files (DECKY_PLUGIN_RUNTIME_DIR):
  installed.json   what Emu Hub installed or adopted, with versions
  shortcuts.json   Steam shortcuts Emu Hub made or adopted, per emulator
  updates.json     the last update check and what was already announced
  backups/<emu>/   original config files from before a Deck preset
"""

from __future__ import annotations

import asyncio
import concurrent.futures
import os
import threading
import time
from typing import Any, Awaitable, Callable, Dict, List, Optional

from . import bios, catalogue, detect, flatpak, library, presets, releases, srm
from .installer import Installer, Job
from .settings import Settings, load_json, save_json

Emit = Callable[..., Awaitable[Any]]

FLATPAK_TTL = 30.0


class Service:
    def __init__(self, settings: Settings, runtime_dir: str, home: str, emit: Optional[Emit] = None) -> None:
        self.settings = settings
        self.runtime = runtime_dir
        self.home = home
        self.emit = emit
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        self.manifest_path = os.path.join(runtime_dir, "installed.json")
        self.shortcuts_path = os.path.join(runtime_dir, "shortcuts.json")
        self.updates_path = os.path.join(runtime_dir, "updates.json")
        self.backups = presets.Backups(os.path.join(runtime_dir, "backups"))
        self.manifest: Dict[str, Any] = load_json(self.manifest_path, {})
        self.shortcuts: Dict[str, Any] = load_json(self.shortcuts_path, {})
        stored = load_json(self.updates_path, {})
        self.checked_at: float = float(stored.get("checked_at") or 0)
        self.latest: Dict[str, Any] = stored.get("latest") or {}
        self.flatpak_updates: Dict[str, str] = stored.get("flatpak_updates") or {}
        self.announced: Dict[str, str] = stored.get("announced") or {}
        self.check_error: Optional[str] = stored.get("error")
        self._flatpaks: Dict[str, Dict[str, str]] = {}
        self._flatpaks_at = 0.0
        self.lock = threading.RLock()
        self.checking = False
        self.installer = Installer(home, self._job_finished)
        self.ticker: Optional[asyncio.Task] = None

    # ------------------------------------------------------------ lifecycle

    async def start(self) -> None:
        self.loop = asyncio.get_running_loop()
        os.makedirs(self.runtime, exist_ok=True)
        self.ticker = self.loop.create_task(self._tick())
        self.loop.create_task(self._auto_choose_later())

    async def stop(self) -> None:
        if self.ticker:
            self.ticker.cancel()
        self.installer.stop()

    async def _tick(self) -> None:
        """Background update check: shortly after start, then every hour look
        whether `check_hours` have passed. Never while a job runs."""
        await asyncio.sleep(90)
        while True:
            try:
                due = time.time() - self.checked_at >= float(self.settings.get("check_hours")) * 3600
                if self.settings.get("check_updates") and due and not self.installer.busy():
                    await self.check_updates(force=True, announce=True)
            except asyncio.CancelledError:
                raise
            except Exception:
                pass
            await asyncio.sleep(3600)

    def _emit_threadsafe(self, event: str, *args: Any) -> None:
        if not self.emit or not self.loop:
            return
        try:
            asyncio.run_coroutine_threadsafe(self.emit(event, *args), self.loop)
        except Exception:
            pass

    # ------------------------------------------------------------- helpers

    def root(self) -> str:
        return library.resolve_root(self.settings.get("library_root"), self.home)

    def _flatpak_list(self, fresh: bool = False) -> Dict[str, Dict[str, str]]:
        if fresh or time.time() - self._flatpaks_at > FLATPAK_TTL:
            self._flatpaks = flatpak.installed(self.home)
            self._flatpaks_at = time.time()
        return self._flatpaks

    def _save_manifest(self) -> None:
        save_json(self.manifest_path, self.manifest)

    def _save_updates(self) -> None:
        save_json(self.updates_path, {
            "checked_at": self.checked_at,
            "latest": self.latest,
            "flatpak_updates": self.flatpak_updates,
            "announced": self.announced,
            "error": self.check_error,
        })

    def _has_update(self, emu: Dict[str, Any], copy: Optional[Dict[str, Any]]) -> bool:
        if not copy:
            return False
        if copy["method"] == "flatpak":
            return copy.get("app_id") in self.flatpak_updates
        newest = self.latest.get(emu["id"])
        if not newest or newest.get("error") or emu["source"]["type"] == "flathub":
            return False
        return releases.is_update(copy, newest)

    def _view(self, emu: Dict[str, Any], copy: Optional[Dict[str, Any]], jobs: Dict[str, Dict[str, Any]], root: str) -> Dict[str, Any]:
        newest = self.latest.get(emu["id"]) or {}
        method = copy["method"] if copy else emu["method"]
        preset_state = presets.status(emu.get("preset"), method, self.home, root) if copy else (
            "none" if not emu.get("preset") else "ready")
        installed = None
        if copy:
            installed = {
                "method": copy["method"],
                "version": copy.get("version"),
                "path": copy.get("path"),
                "app_id": copy.get("app_id"),
                "installation": copy.get("installation"),
                "managed": bool(copy.get("managed")),
            }
        latest_version = newest.get("version")
        if copy and copy["method"] == "flatpak" and copy.get("app_id") in self.flatpak_updates:
            latest_version = self.flatpak_updates[copy["app_id"]] or latest_version
        shortcut = self.shortcuts.get(emu["id"]) or {}
        return {
            "id": emu["id"],
            "name": emu["name"],
            "blurb": emu["blurb"],
            "consoles": [library.label(c) for c in emu["consoles"]],
            "method": emu["method"],
            "source": emu["source"]["type"],
            "installed": installed,
            "latest": latest_version,
            "latest_error": newest.get("error"),
            "update": self._has_update(emu, copy),
            # Found (EmuDeck, by hand), so Emu Hub cannot tell its version.
            "unknown_version": bool(copy and copy["method"] == "appimage" and not copy.get("key")
                                    and emu["source"]["type"] != "flathub"),
            "preset": {
                "state": preset_state,
                "summary": (presets.PRESETS.get(emu.get("preset") or "") or {}).get("summary"),
                "backup": self.backups.has(emu["id"]),
            },
            "shortcut": shortcut.get("appid"),
            "job": jobs.get(emu["id"]),
        }

    def _snapshot(self) -> Dict[str, Any]:
        root = self.root()
        flatpaks = self._flatpak_list()
        found = detect.detect_all(self.home, self.manifest, flatpaks)
        self._apply_pending(found, root)
        jobs = {j["emu_id"]: j for j in self.installer.views()}
        views = [self._view(emu, found.get(emu["id"]), jobs, root) for emu in catalogue.EMULATORS]
        return {
            "emulators": views,
            "updates": sum(1 for v in views if v["update"]),
            "checked_at": self.checked_at,
            "checking": self.checking,
            "check_error": self.check_error,
            "busy": self.installer.busy(),
            "flatpak": flatpak.available(),
            "library": {"root": root, "ready": os.path.isdir(library.roms_dir(root))},
        }

    def _apply_pending(self, found: Dict[str, Any], root: str) -> None:
        """Presets that waited for the emulator's first start."""
        changed = False
        for emu_id, record in list(self.manifest.items()):
            if not record.get("preset_pending") or emu_id not in found:
                continue
            emu = catalogue.get(emu_id)
            if not emu:
                continue
            method = found[emu_id]["method"]
            if presets.status(emu.get("preset"), method, self.home, root) == "waiting":
                continue
            result = presets.apply(emu.get("preset"), emu_id, method, self.home, root, self.backups)
            record["preset_pending"] = False
            record["preset_result"] = "applied" if result.get("ok") else result.get("error")
            changed = True
            if result.get("ok"):
                self._emit_threadsafe("emuhub_notice", f"{emu['name']} is set up for the Deck",
                                      "Deck settings applied after its first start.")
        if changed:
            self._save_manifest()

    # --------------------------------------------------------------- public

    async def state(self) -> Dict[str, Any]:
        return await asyncio.to_thread(self._snapshot)

    async def check_updates(self, force: bool = False, announce: bool = False) -> Dict[str, Any]:
        if self.checking:
            return await self.state()
        self.checking = True
        try:
            await asyncio.to_thread(self._check, force)
        finally:
            self.checking = False
        snapshot = await self.state()
        if announce:
            await self._announce(snapshot)
        return snapshot

    def _check(self, force: bool) -> None:
        token = self.settings.get("github_token") or None
        errors: List[str] = []

        def one(emu: Dict[str, Any]) -> None:
            try:
                if emu["source"]["type"] == "flathub":
                    version = releases.flathub_version(emu["flatpak"], force=force)
                    self.latest[emu["id"]] = {"version": version, "key": version}
                else:
                    self.latest[emu["id"]] = releases.latest(emu, token=token, force=force)
            except releases.SourceError as error:
                previous = self.latest.get(emu["id"]) or {}
                self.latest[emu["id"]] = dict(previous, error=str(error))
                errors.append(f"{emu['name']}: {error}")
            except Exception as error:  # a broken source never stops the others
                self.latest[emu["id"]] = {"error": str(error)}
                errors.append(f"{emu['name']}: {error}")

        with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
            list(pool.map(one, catalogue.EMULATORS))
        self.flatpak_updates = flatpak.updates(self.home)
        self._flatpak_list(fresh=True)
        self.checked_at = time.time()
        rate_limited = [e for e in errors if "limit" in e]
        self.check_error = (rate_limited[0] if rate_limited else
                            (f"{len(errors)} source(s) could not be checked" if errors else None))
        self._save_updates()

    async def _announce(self, snapshot: Dict[str, Any]) -> None:
        """Toast new updates once per version."""
        fresh = []
        for view in snapshot["emulators"]:
            if view["update"] and self.announced.get(view["id"]) != (view["latest"] or "?"):
                fresh.append(view["name"])
                self.announced[view["id"]] = view["latest"] or "?"
        if fresh:
            self._save_updates()
            if self.emit:
                await self.emit("emuhub_updates", {"count": snapshot["updates"], "names": fresh})

    def _plan(self, emu: Dict[str, Any], action: str, copy: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        if action == "uninstall":
            if not copy:
                raise ValueError("not installed")
            if copy["method"] == "flatpak":
                return {"method": "flatpak", "app_id": copy["app_id"], "installation": copy.get("installation")}
            return {"method": "appimage", "path": copy["path"]}
        if copy and copy["method"] == "flatpak":
            return {"method": "flatpak", "app_id": copy["app_id"], "installation": copy.get("installation"),
                    "version": self.flatpak_updates.get(copy["app_id"])}
        if emu["method"] == "flatpak" and not copy:
            return {"method": "flatpak", "app_id": emu["flatpak"], "installation": "user",
                    "version": (self.latest.get(emu["id"]) or {}).get("version")}
        if emu["source"]["type"] == "flathub":
            raise ValueError(f"{emu['name']} is installed as a file Emu Hub cannot update")
        newest = releases.latest(emu, token=self.settings.get("github_token") or None)
        self.latest[emu["id"]] = newest
        apps = detect.apps_dir(self.home)
        target = os.path.join(apps, emu["file"])
        # Update a found AppImage where it is, so launchers pointing at it keep working.
        if copy and (copy.get("path") or "").lower().endswith(".appimage") and os.path.dirname(copy["path"]) == apps:
            target = copy["path"]
        return {"method": "appimage", "url": newest["url"], "size": newest["size"], "version": newest["version"],
                "key": newest["key"], "target": target, "zip_member": emu.get("zip_member")}

    async def run(self, emu_id: str, action: str) -> Dict[str, Any]:
        emu = catalogue.get(emu_id)
        if not emu or action not in ("install", "update", "uninstall"):
            return {"ok": False, "error": "Unknown emulator or action"}
        flatpaks = await asyncio.to_thread(self._flatpak_list)
        copy = detect.detect(emu, self.home, self.manifest, flatpaks)
        if action == "install" and copy:
            action = "update"
        try:
            plan = await asyncio.to_thread(self._plan, emu, action, copy)
        except (ValueError, releases.SourceError) as error:
            return {"ok": False, "error": str(error)}
        plan["first_install"] = copy is None
        self.installer.add(emu_id, action, plan)
        return {"ok": True, "state": await self.state()}

    async def update_all(self) -> Dict[str, Any]:
        snapshot = await self.state()
        queued = []
        for view in snapshot["emulators"]:
            if view["update"]:
                result = await self.run(view["id"], "update")
                if result.get("ok"):
                    queued.append(view["id"])
        return {"ok": True, "queued": queued, "state": await self.state()}

    async def cancel(self, emu_id: str) -> Dict[str, Any]:
        return {"ok": self.installer.cancel(emu_id), "state": await self.state()}

    def _job_finished(self, job: Job) -> None:
        """Worker thread: record the result, apply the preset, tell the UI."""
        emu = catalogue.get(job.emu_id)
        if not emu:
            return
        self._flatpaks_at = 0.0
        if job.state == "done":
            with self.lock:
                if job.action == "uninstall":
                    self.manifest.pop(job.emu_id, None)
                else:
                    record = dict(self.manifest.get(job.emu_id) or {})
                    record.update(job.result)
                    record.update({
                        "version": job.plan.get("version") or record.get("version"),
                        "key": job.plan.get("key") or job.plan.get("version") or record.get("key"),
                        "managed": True,
                        "updated_at": time.time(),
                    })
                    record.setdefault("installed_at", time.time())
                    self.manifest[job.emu_id] = record
                    if job.plan.get("method") == "flatpak":
                        self.flatpak_updates.pop(job.plan.get("app_id"), None)
                        self._save_updates()
                self._save_manifest()
            if job.action != "uninstall" and job.plan.get("first_install") and self.settings.get("auto_presets") and emu.get("preset"):
                method = job.result.get("method", emu["method"])
                result = presets.apply(emu["preset"], emu["id"], method, self.home, self.root(), self.backups)
                if not result.get("ok") and result.get("state") == "waiting":
                    self.manifest[job.emu_id]["preset_pending"] = True
                    self._save_manifest()
        if job.state == "done":
            self._auto_choose()
        self._emit_threadsafe("emuhub_job", {
            "emu_id": job.emu_id,
            "name": emu["name"],
            "action": job.action,
            "state": job.state,
            "error": job.error,
            "shortcut": self._shortcut_plan(emu) if job.state == "done" and job.action != "uninstall" else None,
        })

    # -------------------------------------------------------------- presets

    async def apply_preset(self, emu_id: str) -> Dict[str, Any]:
        emu = catalogue.get(emu_id)
        if not emu:
            return {"ok": False, "error": "Unknown emulator"}
        copy = await asyncio.to_thread(detect.detect, emu, self.home, self.manifest, self._flatpak_list())
        if not copy:
            return {"ok": False, "error": "Install it first."}
        result = await asyncio.to_thread(presets.apply, emu.get("preset"), emu_id, copy["method"], self.home, self.root(), self.backups)
        if not result.get("ok") and result.get("state") == "waiting" and emu_id in self.manifest:
            self.manifest[emu_id]["preset_pending"] = True
            self._save_manifest()
        result["state_all"] = await self.state()
        return result

    async def restore_config(self, emu_id: str) -> Dict[str, Any]:
        result = await asyncio.to_thread(self.backups.restore, emu_id)
        if emu_id in self.manifest:
            self.manifest[emu_id]["preset_pending"] = False
            self._save_manifest()
        result["state_all"] = await self.state()
        return result

    # --------------------------------------------------------------- steam

    def _shortcut_plan(self, emu: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        copy = detect.detect(emu, self.home, self.manifest, self._flatpak_list())
        if not copy:
            return None
        if copy["method"] == "flatpak":
            return {"emu_id": emu["id"], "name": emu["name"], "exe": '"/usr/bin/flatpak"',
                    "startDir": '"/usr/bin"', "launchOptions": f"run {copy['app_id']}", "key": copy["app_id"]}
        path = copy["path"]
        return {"emu_id": emu["id"], "name": emu["name"], "exe": f'"{path}"',
                "startDir": f'"{os.path.dirname(path)}"', "launchOptions": "", "key": path}

    async def shortcut_plan(self, emu_id: str) -> Dict[str, Any]:
        emu = catalogue.get(emu_id)
        plan = await asyncio.to_thread(self._shortcut_plan, emu) if emu else None
        tracked = self.shortcuts.get(emu_id) or {}
        return {"plan": plan, "appid": tracked.get("appid"), "made": bool(tracked.get("made")),
                "enabled": bool(self.settings.get("add_to_steam"))}

    async def report_shortcut(self, emu_id: str, appid: Optional[int], made: bool = True) -> Dict[str, Any]:
        if appid:
            self.shortcuts[emu_id] = {"appid": int(appid), "made": bool(made), "at": time.time()}
        else:
            self.shortcuts.pop(emu_id, None)
        await asyncio.to_thread(save_json, self.shortcuts_path, self.shortcuts)
        return {"ok": True}

    # ------------------------------------------------- which emulator opens …

    def _installed_ids(self) -> Dict[str, Any]:
        return detect.detect_all(self.home, self.manifest, self._flatpak_list())

    def _choices(self) -> Dict[str, Any]:
        result = srm.choices(self.home, self._installed_ids())
        labels = {folder: label for label, folder in library.CONSOLES.values()}
        for group in result.get("consoles", []):
            group["label"] = labels.get(group["console"], group["console"])
        return result

    async def emulator_choices(self) -> Dict[str, Any]:
        """Consoles with games more than one emulator could open (SRM parsers)."""
        return await asyncio.to_thread(self._choices)

    async def choose_emulator(self, console: str, key: str) -> Dict[str, Any]:
        result = await asyncio.to_thread(srm.choose, self.home, console, key,
                                         os.path.join(self.runtime, "backups", "srm"))
        result["choices"] = await self.emulator_choices()
        return result

    async def launch_check(self) -> Dict[str, Any]:
        """Which launcher each emulator's Steam games start, and whether it can work."""
        return await asyncio.to_thread(lambda: srm.launch_check(self.home, self._installed_ids()))

    async def use_launchers(self, emuhub: bool) -> Dict[str, Any]:
        """Point SRM's parsers at Emu Hub's launchers, or back at the old ones."""
        backups = os.path.join(self.runtime, "backups", "srm")
        state = os.path.join(self.runtime, "launchers.json")
        if emuhub:
            result = await asyncio.to_thread(srm.use_emuhub_launchers, self.home, backups, state)
        else:
            result = await asyncio.to_thread(srm.use_original_launchers, self.home, backups, state)
        result["check"] = await self.launch_check()
        return result

    def _auto_choose(self) -> None:
        """A console whose games would start an emulator that is gone gets an
        installed one (srm.auto_choose); the frontend tells ROM-Store."""
        try:
            done = srm.auto_choose(self.home, self._installed_ids(), os.path.join(self.runtime, "backups", "srm"))
        except Exception:
            return
        if done:
            self._emit_threadsafe("emuhub_choice", {"auto": True, "changes": done})

    async def _auto_choose_later(self) -> None:
        await asyncio.sleep(20)
        await asyncio.to_thread(self._auto_choose)

    # ------------------------------------------------------------- library

    async def library_info(self) -> Dict[str, Any]:
        def build() -> Dict[str, Any]:
            root = self.root()
            info = library.describe(root)
            info["candidates"] = library.candidates(self.home)
            info["automatic"] = not self.settings.get("library_root")
            consoles = []
            for emu in catalogue.EMULATORS:
                consoles.extend(emu["consoles"])
            info["bios_status"] = bios.report(consoles, library.bios_dir(root), self.home)
            return info

        return await asyncio.to_thread(build)

    async def set_library_root(self, path: str) -> Dict[str, Any]:
        self.settings.update({"library_root": path or ""})
        return await self.library_info()

    async def create_folders(self) -> Dict[str, Any]:
        result = await asyncio.to_thread(library.create_folders, self.root())
        result["library"] = await self.library_info()
        return result

    async def get_settings(self) -> Dict[str, Any]:
        return self.settings.view()

    async def set_settings(self, changes: Dict[str, Any]) -> Dict[str, Any]:
        if "github_token" in (changes or {}):
            releases.clear_cache()
        return self.settings.update(changes)
