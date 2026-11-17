"""Install, update and remove emulators, one job at a time, off the event loop.

A job is queued by the service with everything it needs already resolved
(the file to download and where it goes, or the flatpak app id), and runs on
a single worker thread. Progress, cancel and the result are read by the
service; the frontend polls them only while a job is running.

AppImages: downloaded next to their target as `<name>.part` (a zip is
unpacked into it), checked to be a Linux program (an error page is never
installed), then the old file is moved to `<name>.bak`, the new one takes its
place, and only then is the `.bak` removed. A failure in between puts the old
file back.
"""

from __future__ import annotations

import os
import shutil
import stat
import threading
import time
import urllib.error
import urllib.request
import zipfile
from collections import deque
from typing import Any, Callable, Deque, Dict, List, Optional

from . import flatpak
from .releases import USER_AGENT

CHUNK = 256 * 1024
ELF = b"\x7fELF"


class Cancelled(Exception):
    pass


class Job:
    def __init__(self, emu_id: str, action: str, plan: Dict[str, Any]) -> None:
        self.emu_id = emu_id
        self.action = action
        self.plan = plan
        self.state = "queued"
        self.progress = 0.0
        self.received = 0
        self.total = int(plan.get("size") or 0)
        self.message = "Waiting"
        self.error: Optional[str] = None
        self.result: Dict[str, Any] = {}
        self.cancel = threading.Event()
        self.created = time.time()
        self.finished: Optional[float] = None

    def view(self) -> Dict[str, Any]:
        return {
            "emu_id": self.emu_id,
            "action": self.action,
            "state": self.state,
            "progress": round(self.progress, 4),
            "received": self.received,
            "total": self.total,
            "message": self.message,
            "error": self.error,
            "version": self.plan.get("version"),
        }


def download(url: str, dest: str, job: Job, timeout: float = 30) -> None:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        response = urllib.request.urlopen(request, timeout=timeout)
    except urllib.error.HTTPError as error:
        raise RuntimeError(f"the download answered HTTP {error.code}")
    except (urllib.error.URLError, OSError) as error:
        raise RuntimeError(f"no connection ({getattr(error, 'reason', error)})")
    with response:
        length = response.headers.get("Content-Length")
        if length and length.isdigit():
            job.total = int(length)
        job.received = 0
        with open(dest, "wb") as handle:
            while True:
                if job.cancel.is_set():
                    raise Cancelled()
                chunk = response.read(CHUNK)
                if not chunk:
                    break
                handle.write(chunk)
                job.received += len(chunk)
                if job.total:
                    job.progress = min(0.97, job.received / job.total)
    if job.total and job.received < job.total:
        raise RuntimeError("the download stopped early")


def unzip_member(archive: str, pattern: str, dest: str) -> str:
    import re
    regex = re.compile(pattern, re.I)
    with zipfile.ZipFile(archive) as zf:
        members = [m for m in zf.infolist() if not m.is_dir() and regex.search(m.filename)]
        if not members:
            raise RuntimeError("the zip has no AppImage in it")
        member = members[0]
        with zf.open(member) as src, open(dest, "wb") as out:
            shutil.copyfileobj(src, out, CHUNK)
        return member.filename


def looks_like_program(path: str) -> bool:
    try:
        with open(path, "rb") as handle:
            return handle.read(4) == ELF
    except OSError:
        return False


def replace_file(new: str, target: str) -> None:
    """Swap `new` in for `target`, keeping the old file as .bak until done."""
    backup = f"{target}.bak"
    had_old = os.path.isfile(target)
    if had_old:
        os.replace(target, backup)
    try:
        os.replace(new, target)
        mode = os.stat(target).st_mode
        os.chmod(target, mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH | stat.S_IRUSR)
    except OSError:
        if had_old and os.path.isfile(backup):
            os.replace(backup, target)
        raise
    if had_old and os.path.isfile(backup):
        os.remove(backup)


def install_appimage(job: Job) -> Dict[str, Any]:
    plan = job.plan
    target = plan["target"]
    folder = os.path.dirname(target)
    os.makedirs(folder, exist_ok=True)
    need = int(plan.get("size") or 0) * (2 if plan.get("zip_member") else 1)
    free = shutil.disk_usage(folder).free
    if need and free < need + 64 * 1024 * 1024:
        raise RuntimeError(f"not enough free space ({free // (1024 * 1024)} MB free)")
    part = f"{target}.part"
    archive = f"{target}.zip.part"
    try:
        job.message = "Downloading"
        if plan.get("zip_member"):
            download(plan["url"], archive, job)
            job.message = "Unpacking"
            unzip_member(archive, plan["zip_member"], part)
        else:
            download(plan["url"], part, job)
        if not looks_like_program(part):
            raise RuntimeError("the file is not a Linux program (a web page or a broken download)")
        job.message = "Installing"
        replace_file(part, target)
    finally:
        for leftover in (part, archive):
            if os.path.exists(leftover):
                try:
                    os.remove(leftover)
                except OSError:
                    pass
    return {"method": "appimage", "path": target}


def run_flatpak(job: Job, home: str) -> Dict[str, Any]:
    plan = job.plan
    if not flatpak.available():
        raise RuntimeError("flatpak is not available on this system")
    if job.action == "install":
        job.message = "Adding Flathub"
        error = flatpak.ensure_remote(home)
        if error:
            raise RuntimeError(error)
    job.message = {"install": "Installing from Flathub", "update": "Updating", "uninstall": "Removing"}[job.action]

    def on_progress(value: float) -> None:
        job.progress = min(0.97, value)

    error = flatpak.run_with_progress(
        flatpak.command(job.action, plan["app_id"], plan.get("installation")),
        home, on_progress, job.cancel.is_set,
    )
    if error == "Cancelled":
        raise Cancelled()
    if error:
        raise RuntimeError(error)
    return {"method": "flatpak", "app_id": plan["app_id"],
            "installation": "user" if job.action == "install" else plan.get("installation")}


def remove_appimage(job: Job, home: str) -> Dict[str, Any]:
    path = job.plan["path"]
    apps = os.path.realpath(os.path.join(home, "Applications"))
    real = os.path.realpath(path)
    # Only files EmuDecky manages or found in ~/Applications, never elsewhere.
    if not real.startswith(apps + os.sep):
        raise RuntimeError("that file is not in ~/Applications, so it is left alone")
    if os.path.islink(path) or os.path.isfile(path):
        os.remove(path)
    return {"method": "appimage", "path": path}


class Installer:
    def __init__(self, home: str, on_finished: Callable[[Job], None]) -> None:
        self.home = home
        self.on_finished = on_finished
        self.queue: Deque[Job] = deque()
        self.jobs: Dict[str, Job] = {}
        self.current: Optional[Job] = None
        self.lock = threading.Lock()
        self.wake = threading.Event()
        self.thread: Optional[threading.Thread] = None
        self.stopping = False

    def start(self) -> None:
        if self.thread and self.thread.is_alive():
            return
        self.stopping = False
        self.thread = threading.Thread(target=self._loop, name="emudecky-installer", daemon=True)
        self.thread.start()

    def stop(self) -> None:
        self.stopping = True
        with self.lock:
            for job in list(self.queue):
                job.cancel.set()
            if self.current:
                self.current.cancel.set()
        self.wake.set()

    def add(self, emu_id: str, action: str, plan: Dict[str, Any]) -> Job:
        with self.lock:
            old = self.jobs.get(emu_id)
            if old and old.state in ("queued", "running"):
                return old
            job = Job(emu_id, action, plan)
            self.jobs[emu_id] = job
            self.queue.append(job)
        self.start()
        self.wake.set()
        return job

    def cancel(self, emu_id: str) -> bool:
        with self.lock:
            job = self.jobs.get(emu_id)
            if not job or job.state not in ("queued", "running"):
                return False
            job.cancel.set()
            if job.state == "queued":
                try:
                    self.queue.remove(job)
                except ValueError:
                    pass
                job.state = "cancelled"
                job.error = "Cancelled"
                job.finished = time.time()
        return True

    def busy(self) -> bool:
        with self.lock:
            return any(job.state in ("queued", "running") for job in self.jobs.values())

    def views(self) -> List[Dict[str, Any]]:
        with self.lock:
            jobs = sorted(self.jobs.values(), key=lambda j: j.created)
        # Finished jobs are shown for a minute, then only their effect remains.
        now = time.time()
        return [j.view() for j in jobs if not j.finished or now - j.finished < 60]

    def _loop(self) -> None:
        while not self.stopping:
            with self.lock:
                job = self.queue.popleft() if self.queue else None
                self.current = job
            if job is None:
                self.wake.wait(5)
                self.wake.clear()
                continue
            self._run(job)
            with self.lock:
                self.current = None

    def _run(self, job: Job) -> None:
        job.state = "running"
        try:
            if job.plan.get("method") == "flatpak":
                job.result = run_flatpak(job, self.home)
            elif job.action == "uninstall":
                job.result = remove_appimage(job, self.home)
            else:
                job.result = install_appimage(job)
            job.state = "done"
            job.progress = 1.0
            job.message = {"install": "Installed", "update": "Updated", "uninstall": "Removed"}[job.action]
        except Cancelled:
            job.state = "cancelled"
            job.error = "Cancelled"
            job.message = "Cancelled"
        except Exception as error:  # every failure ends up on screen, none kills the worker
            job.state = "error"
            job.error = str(error) or error.__class__.__name__
            job.message = "Failed"
        job.finished = time.time()
        try:
            self.on_finished(job)
        except Exception:
            pass
