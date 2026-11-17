"""Environment for the programs Emu Hub starts (flatpak, AppImages).

Decky runs plugin backends with its own PyInstaller-built Python, which sets
LD_LIBRARY_PATH to its bundled libraries. Passed on, that breaks system
programs like `flatpak` (they load the wrong libssl, libstdc++, ...). Every
subprocess gets this cleaned environment instead.
"""

from __future__ import annotations

import os
import subprocess
from typing import Dict, List, Optional

DROP = ("LD_LIBRARY_PATH", "LD_PRELOAD", "PYTHONHOME", "PYTHONPATH", "PYINSTALLER_RESET_ENVIRONMENT")


def clean_env(home: str, base: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    env = dict(os.environ if base is None else base)
    original = env.get("LD_LIBRARY_PATH_ORIG")
    for name in DROP:
        env.pop(name, None)
    env.pop("LD_LIBRARY_PATH_ORIG", None)
    if original:
        # PyInstaller keeps what was there before it started; restore that.
        env["LD_LIBRARY_PATH"] = original
    env["HOME"] = home
    env["XDG_DATA_HOME"] = os.path.join(home, ".local", "share")
    env["XDG_CONFIG_HOME"] = os.path.join(home, ".config")
    env["XDG_CACHE_HOME"] = os.path.join(home, ".cache")
    paths = [p for p in env.get("PATH", "").split(":") if p]
    for extra in ("/usr/local/bin", "/usr/bin", "/bin"):
        if extra not in paths:
            paths.append(extra)
    env["PATH"] = ":".join(paths)
    try:
        uid = os.getuid()
    except AttributeError:  # not POSIX (tests on another OS)
        uid = None
    if uid is not None:
        runtime = f"/run/user/{uid}"
        if os.path.isdir(runtime):
            env.setdefault("XDG_RUNTIME_DIR", runtime)
            env.setdefault("DBUS_SESSION_BUS_ADDRESS", f"unix:path={runtime}/bus")
    return env


def run(args: List[str], home: str, timeout: float = 120) -> subprocess.CompletedProcess:
    """Run a command to completion with the clean environment."""
    return subprocess.run(
        args,
        env=clean_env(home),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=timeout,
        stdin=subprocess.DEVNULL,
    )
