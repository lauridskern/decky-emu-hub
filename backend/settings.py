"""User settings, one small JSON file."""

from __future__ import annotations

import json
import os
import threading
from typing import Any, Dict

DEFAULTS: Dict[str, Any] = {
    # "" = pick automatically (an EmuDeck library if there is one, else ~/EmuDecky)
    "library_root": "",
    # Apply the Deck preset right after an emulator is installed.
    "auto_presets": True,
    # Add each installed emulator to the Steam library as a shortcut.
    "add_to_steam": True,
    # Look for updates in the background, every `check_hours` hours.
    "check_updates": True,
    "check_hours": 6,
    # Optional: raises GitHub's limit of 60 anonymous requests an hour.
    "github_token": "",
}

EDITABLE = set(DEFAULTS)


class Settings:
    def __init__(self, path: str) -> None:
        self.path = path
        self.lock = threading.Lock()
        self.data: Dict[str, Any] = dict(DEFAULTS)
        try:
            with open(path, "r", encoding="utf-8") as handle:
                stored = json.load(handle)
            if isinstance(stored, dict):
                self.data.update({k: v for k, v in stored.items() if k in DEFAULTS})
        except (OSError, ValueError):
            pass

    def get(self, key: str) -> Any:
        with self.lock:
            return self.data.get(key, DEFAULTS.get(key))

    def view(self) -> Dict[str, Any]:
        with self.lock:
            data = dict(self.data)
        # The token never goes back to the UI, only whether one is set.
        data["github_token_set"] = bool(data.pop("github_token", ""))
        return data

    def update(self, changes: Dict[str, Any]) -> Dict[str, Any]:
        with self.lock:
            for key, value in (changes or {}).items():
                if key not in EDITABLE:
                    continue
                default = DEFAULTS[key]
                if isinstance(default, bool):
                    value = bool(value)
                elif isinstance(default, int):
                    try:
                        value = max(1, min(168, int(value)))
                    except (TypeError, ValueError):
                        continue
                else:
                    value = str(value or "").strip()
                self.data[key] = value
            self._save()
        return self.view()

    def _save(self) -> None:
        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
        tmp = f"{self.path}.tmp"
        with open(tmp, "w", encoding="utf-8") as handle:
            json.dump(self.data, handle, indent=2)
        os.replace(tmp, self.path)


def load_json(path: str, default: Any) -> Any:
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
        return data if isinstance(data, type(default)) else default
    except (OSError, ValueError):
        return default


def save_json(path: str, data: Any) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    tmp = f"{path}.tmp"
    with open(tmp, "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2)
    os.replace(tmp, path)
