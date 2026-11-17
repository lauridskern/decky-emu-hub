"""Where the newest version of an emulator is, and what it is called.

GitHub and Forgejo (Ryubing) both answer `.../releases/latest` with the same
shape: a tag, a name, a date and a list of files. `latest()` turns either
into one small dict and picks the file for this emulator with its `asset`
pattern. Flathub apps are asked through Flathub's appstream API, only for the
version to show; flatpak itself decides whether an installed app has an update.

Answers are kept in memory for an hour (`TTL`), so opening the plugin again
and again does not use up GitHub's 60 requests an hour for anonymous clients.
A GitHub token in Settings raises that limit; it is only ever sent to
api.github.com.
"""

from __future__ import annotations

import json
import re
import threading
import time
import urllib.error
import urllib.request
from typing import Any, Callable, Dict, List, Optional, Tuple

USER_AGENT = "Emu Hub (Decky plugin)"
TTL = 3600.0
TIMEOUT = 20

_cache: Dict[str, Tuple[float, Any]] = {}
_lock = threading.Lock()


class SourceError(Exception):
    pass


def fetch_json(url: str, token: Optional[str] = None, timeout: float = TIMEOUT) -> Any:
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    if token and url.startswith("https://api.github.com/"):
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        if error.code == 403 and "api.github.com" in url:
            raise SourceError("GitHub's limit for anonymous requests is used up; try again in an hour or add a token in Settings")
        if error.code == 404:
            raise SourceError("no release found")
        raise SourceError(f"HTTP {error.code}")
    except (urllib.error.URLError, TimeoutError, OSError) as error:
        reason = getattr(error, "reason", error)
        raise SourceError(f"no connection ({reason})")
    except ValueError:
        raise SourceError("the answer was not JSON")


def _cached(key: str, load: Callable[[], Any], force: bool = False) -> Any:
    now = time.time()
    with _lock:
        hit = _cache.get(key)
        if hit and not force and now - hit[0] < TTL:
            return hit[1]
    value = load()
    with _lock:
        _cache[key] = (now, value)
    return value


def clear_cache() -> None:
    with _lock:
        _cache.clear()


def normalise(raw: Dict[str, Any]) -> Dict[str, Any]:
    """GitHub or Forgejo release JSON -> {tag, name, published, assets[]}."""
    assets = []
    for asset in raw.get("assets") or []:
        assets.append({
            "name": asset.get("name") or "",
            "size": asset.get("size") or 0,
            "updated_at": asset.get("updated_at") or asset.get("created_at") or "",
            "url": asset.get("browser_download_url") or "",
        })
    return {
        "tag": raw.get("tag_name") or "",
        "name": raw.get("name") or "",
        "published": raw.get("published_at") or raw.get("created_at") or "",
        "prerelease": bool(raw.get("prerelease")),
        "assets": assets,
    }


def pick_asset(release: Dict[str, Any], pattern: str) -> Optional[Dict[str, Any]]:
    regex = re.compile(pattern, re.I)
    matches = [a for a in release["assets"] if regex.search(a["name"])]
    return matches[0] if matches else None


def describe(emu: Dict[str, Any], release: Dict[str, Any]) -> Dict[str, Any]:
    """The version to show, the key to compare and the file to download."""
    source = emu["source"]
    asset = pick_asset(release, source["asset"])
    if not asset:
        raise SourceError("the release has no Linux file for this emulator")
    tag = release["tag"]
    if emu.get("rolling"):
        # One tag that is rebuilt: the file's date is the version.
        stamp = asset["updated_at"] or release["published"]
        version = f"build {stamp[:10]}" if stamp else tag
        key = f"{tag}@{stamp}"
    elif source.get("version_from") == "name" and release["name"]:
        version = release["name"]
        key = tag
    else:
        version = re.sub(r"^v\.?", "", tag)
        key = tag
    return {
        "version": version,
        "key": key,
        "asset": asset["name"],
        "url": asset["url"],
        "size": asset["size"],
        "published": release["published"],
    }


def release_url(emu: Dict[str, Any]) -> str:
    source = emu["source"]
    if source["type"] == "github":
        return f"https://api.github.com/repos/{source['repo']}/releases/latest"
    if source["type"] == "forgejo":
        return f"{source['api'].rstrip('/')}/releases/latest"
    raise SourceError(f"no release API for {source['type']}")


def latest(emu: Dict[str, Any], token: Optional[str] = None, force: bool = False,
           fetch: Optional[Callable[..., Any]] = None) -> Dict[str, Any]:
    """Newest release of an AppImage emulator (cached for an hour)."""
    fetch = fetch or fetch_json
    url = release_url(emu)
    raw = _cached(url, lambda: fetch(url, token), force)
    return describe(emu, normalise(raw))


def flathub_version(app_id: str, force: bool = False, fetch: Optional[Callable[..., Any]] = None) -> Optional[str]:
    """The version Flathub lists for an app, for display."""
    fetch = fetch or fetch_json
    url = f"https://flathub.org/api/v2/appstream/{app_id}"

    def load() -> Optional[str]:
        data = fetch(url)
        releases = (data or {}).get("releases") or []
        return releases[0].get("version") if releases else None

    return _cached(url, load, force)


_TOKEN = re.compile(r"\d+|[a-z]+")


def compare_versions(a: str, b: str) -> int:
    """-1, 0 or 1. Numbers compare as numbers ("2.10" > "2.9"); a leading v is ignored."""
    def parts(text: str) -> List[Any]:
        text = re.sub(r"^v\.?", "", (text or "").strip().lower())
        return [(0, int(t)) if t.isdigit() else (1, t) for t in _TOKEN.findall(text)]

    pa, pb = parts(a), parts(b)
    for x, y in zip(pa, pb):
        if x != y:
            # A number is newer than a word in the same place: 1.0 > 1.0-rc.
            if x[0] != y[0]:
                return -1 if x[0] == 1 else 1
            return -1 if x[1] < y[1] else 1
    if len(pa) == len(pb):
        return 0
    longer, sign = (pa, 1) if len(pa) > len(pb) else (pb, -1)
    extra = longer[min(len(pa), len(pb))]
    # 1.0.1 > 1.0, but 1.0-rc1 < 1.0
    return sign if extra[0] == 0 else -sign


def is_update(installed: Optional[Dict[str, Any]], newest: Dict[str, Any]) -> bool:
    """True when `newest` should replace what is installed.

    A file with an unknown version (found, not installed by Emu Hub) is not
    an update by itself; the UI offers to replace it. A different key is an
    update unless both versions read as numbers and the new one is older.
    """
    if not installed or not installed.get("key"):
        return False
    if installed["key"] == newest["key"]:
        return False
    old, new = installed.get("version") or "", newest.get("version") or ""
    if old and new and re.match(r"^\d", old) and re.match(r"^\d", new):
        return compare_versions(new, old) > 0
    return True
