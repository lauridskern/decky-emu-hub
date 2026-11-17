"""Flathub apps through the `flatpak` command.

New installs go into the user installation (`--user`), which needs no
password and no polkit prompt, so it works in Game Mode. Apps that are
already in the system installation (EmuDeck and Discover put them there)
are updated and removed where they are.

All commands run with procenv's clean environment (see procenv.py).
"""

from __future__ import annotations

import re
import shutil
import subprocess
from typing import Callable, Dict, List, Optional

from . import procenv
from .catalogue import FLATHUB_REPO

FLATPAK = "flatpak"


def available() -> bool:
    return bool(shutil.which(FLATPAK) or shutil.which("/usr/bin/flatpak"))


def parse_list(output: str) -> Dict[str, Dict[str, str]]:
    """`flatpak list --app --columns=application,version,installation`."""
    apps: Dict[str, Dict[str, str]] = {}
    for line in output.splitlines():
        cols = line.split("\t")
        if not cols or not cols[0].strip() or cols[0].startswith("Application"):
            continue
        app_id = cols[0].strip()
        version = cols[1].strip() if len(cols) > 1 else ""
        installation = cols[2].strip() if len(cols) > 2 else "system"
        # A user and a system copy: the user one is what `flatpak run` starts.
        if app_id in apps and apps[app_id]["installation"] == "user":
            continue
        apps[app_id] = {"version": version, "installation": installation or "system"}
    return apps


def parse_updates(output: str) -> Dict[str, str]:
    """`flatpak remote-ls --updates --app --columns=application,version`."""
    updates: Dict[str, str] = {}
    for line in output.splitlines():
        cols = line.split("\t")
        if cols and cols[0].strip() and "." in cols[0] and not cols[0].startswith("Application"):
            updates[cols[0].strip()] = cols[1].strip() if len(cols) > 1 else ""
    return updates


_PERCENT = re.compile(r"(\d{1,3})%")


def parse_progress(chunk: str) -> Optional[float]:
    """Last percentage in a piece of flatpak's progress output, 0..1."""
    found = _PERCENT.findall(chunk)
    if not found:
        return None
    value = min(100, int(found[-1]))
    return value / 100.0


def installed(home: str) -> Dict[str, Dict[str, str]]:
    if not available():
        return {}
    try:
        result = procenv.run([FLATPAK, "list", "--app", "--columns=application,version,installation"], home, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return {}
    return parse_list(result.stdout) if result.returncode == 0 else {}


def updates(home: str) -> Dict[str, str]:
    """Apps with an update, from both installations."""
    found: Dict[str, str] = {}
    if not available():
        return found
    for scope in ("--user", "--system"):
        try:
            result = procenv.run([FLATPAK, "remote-ls", scope, "--updates", "--app", "--columns=application,version"], home, timeout=90)
        except (OSError, subprocess.SubprocessError):
            continue
        if result.returncode == 0:
            found.update(parse_updates(result.stdout))
    return found


def scope_flag(installation: Optional[str]) -> str:
    return "--system" if installation == "system" else "--user"


def ensure_remote(home: str) -> Optional[str]:
    """Add Flathub to the user installation if it is not there. Error text or None."""
    try:
        result = procenv.run([FLATPAK, "remote-add", "--user", "--if-not-exists", "flathub", FLATHUB_REPO], home, timeout=60)
    except (OSError, subprocess.SubprocessError) as error:
        return str(error)
    return None if result.returncode == 0 else (result.stderr.strip() or "could not add Flathub")


def command(action: str, app_id: str, installation: Optional[str] = None) -> List[str]:
    if action == "install":
        return [FLATPAK, "install", "--user", "-y", "--noninteractive", "flathub", app_id]
    if action == "update":
        return [FLATPAK, "update", scope_flag(installation), "-y", "--noninteractive", app_id]
    if action == "uninstall":
        return [FLATPAK, "uninstall", scope_flag(installation), "-y", "--noninteractive", app_id]
    raise ValueError(action)


def run_with_progress(args: List[str], home: str, on_progress: Callable[[float], None],
                      cancelled: Callable[[], bool]) -> Optional[str]:
    """Run a flatpak command, reporting its percentages. Error text or None."""
    try:
        proc = subprocess.Popen(
            args,
            env=procenv.clean_env(home),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
        )
    except OSError as error:
        return f"could not start flatpak ({error})"
    tail = ""
    assert proc.stdout is not None
    while True:
        if cancelled():
            proc.terminate()
            try:
                proc.wait(10)
            except subprocess.TimeoutExpired:
                proc.kill()
            return "Cancelled"
        chunk = proc.stdout.read1(4096) if hasattr(proc.stdout, "read1") else proc.stdout.read(256)
        if not chunk:
            break
        text = chunk.decode("utf-8", "replace")
        tail = (tail + text)[-2000:]
        value = parse_progress(text)
        if value is not None:
            on_progress(value)
    code = proc.wait()
    if code != 0:
        lines = [l.strip() for l in re.split(r"[\r\n]+", tail) if l.strip()]
        errors = [l for l in lines if l.lower().startswith("error")]
        return (errors or lines or [f"flatpak exited with {code}"])[-1]
    return None
