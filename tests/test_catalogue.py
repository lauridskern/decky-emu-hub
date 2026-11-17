"""Every catalogue entry is complete, and every release source picks the
right file from its recorded release (tests/fixtures/releases)."""

import os
import re
import unittest

from helpers import FIXTURES, release
from backend import catalogue, releases, library


class CatalogueTest(unittest.TestCase):
    def test_entries_are_complete(self):
        ids = set()
        for emu in catalogue.EMULATORS:
            self.assertNotIn(emu["id"], ids)
            ids.add(emu["id"])
            self.assertIn(emu["method"], ("appimage", "flatpak"))
            self.assertTrue(emu["consoles"])
            for console in emu["consoles"]:
                self.assertIn(console, library.CONSOLES, f"{emu['id']}: {console}")
            if emu["method"] == "flatpak":
                self.assertEqual(emu["source"]["type"], "flathub")
                self.assertRegex(emu["flatpak"], r"^[A-Za-z0-9_]+(\.[A-Za-z0-9_-]+)+$")
            else:
                self.assertTrue(emu["file"].endswith(".AppImage"))
                self.assertIn(emu["source"]["type"], ("github", "forgejo"))
                re.compile(emu["source"]["asset"])

    def test_required_emulators_present(self):
        for wanted in ("retroarch", "dolphin", "pcsx2", "duckstation", "ppsspp", "cemu", "rpcs3", "azahar",
                       "melonds", "ryubing", "xemu", "vita3k", "shadps4", "flycast", "scummvm", "mame", "primehack"):
            self.assertIn(wanted, catalogue.BY_ID)

    def test_every_source_has_a_fixture_and_picks_one_linux_file(self):
        expected = {
            "pcsx2": ("pcsx2-v2.8.2-linux-appimage-x64-Qt.AppImage", "2.8.2"),
            "duckstation": ("DuckStation-x64.AppImage", None),
            "ppsspp": ("PPSSPP-v1.20.4-anylinux-x86_64.AppImage", "1.20.4"),
            "cemu": ("Cemu-2.6-x86_64.AppImage", "2.6"),
            "rpcs3": (None, "0.0.43-20623"),
            "azahar": ("azahar.AppImage", "2126.2"),
            "melonds": ("melonDS-1.1-appimage-x86_64.zip", "1.1"),
            "ryubing": ("ryujinx-1.3.3-x64.AppImage", "1.3.3"),
            "xemu": ("xemu-0.8.139-x86_64.AppImage", "0.8.139"),
            "vita3k": ("Vita3K-x86_64.AppImage", None),
            "flycast": ("flycast-x86_64-2.7.AppImage", "2.7"),
        }
        for emu in catalogue.EMULATORS:
            if emu["source"]["type"] == "flathub":
                continue
            self.assertTrue(os.path.isfile(os.path.join(FIXTURES, "releases", f"{emu['id']}.json")), emu["id"])
            info = releases.describe(emu, releases.normalise(release(emu["id"])))
            self.assertNotRegex(info["asset"], r"(?i)aarch64|arm64|armhf|windows|macos|dbg|zsync|SSE2", emu["id"])
            self.assertTrue(info["url"].startswith("https://"), emu["id"])
            name, version = expected[emu["id"]]
            if name:
                self.assertEqual(info["asset"], name)
            if version:
                self.assertEqual(info["version"], version)

    def test_rolling_release_versions_are_build_dates(self):
        info = releases.describe(catalogue.get("duckstation"), releases.normalise(release("duckstation")))
        self.assertTrue(info["version"].startswith("build 20"))
        self.assertIn("latest@", info["key"])

    def test_latest_uses_the_fetcher_and_caches(self):
        calls = []

        def fake(url, token=None):
            calls.append(url)
            return release("pcsx2")

        releases.clear_cache()
        emu = catalogue.get("pcsx2")
        releases.latest(emu, fetch=fake)
        releases.latest(emu, fetch=fake)
        self.assertEqual(calls, ["https://api.github.com/repos/PCSX2/pcsx2/releases/latest"])
        releases.latest(emu, fetch=fake, force=True)
        self.assertEqual(len(calls), 2)
        releases.clear_cache()

    def test_forgejo_url(self):
        self.assertEqual(releases.release_url(catalogue.get("ryubing")),
                         "https://git.ryujinx.app/api/v1/repos/projects/Ryubing/releases/latest")

    def test_flathub_version(self):
        releases.clear_cache()
        version = releases.flathub_version("org.example.App", fetch=lambda url: {"releases": [{"version": "1.2"}]})
        self.assertEqual(version, "1.2")
        releases.clear_cache()


class VersionTest(unittest.TestCase):
    def test_compare(self):
        c = releases.compare_versions
        self.assertEqual(c("2.10", "2.9"), 1)
        self.assertEqual(c("v2.8.2", "2.8.2"), 0)
        self.assertEqual(c("1.0", "1.0.1"), -1)
        self.assertEqual(c("1.0-rc1", "1.0"), -1)
        self.assertEqual(c("0.0.43-20623", "0.0.43-20601"), 1)
        self.assertEqual(c("2126.2", "2125.0"), 1)

    def test_is_update(self):
        newest = {"version": "2.8.2", "key": "v2.8.2"}
        self.assertTrue(releases.is_update({"version": "2.8.1", "key": "v2.8.1"}, newest))
        self.assertFalse(releases.is_update({"version": "2.8.2", "key": "v2.8.2"}, newest))
        # never a downgrade
        self.assertFalse(releases.is_update({"version": "2.9.0", "key": "v2.9.0"}, newest))
        # unknown version (found, not installed by EmuDecky): not an update by itself
        self.assertFalse(releases.is_update({"version": None, "key": None}, newest))
        # rolling: a new build date is an update
        self.assertTrue(releases.is_update({"version": "build 2026-10-01", "key": "latest@2026-10-01T00:00:00Z"},
                                           {"version": "build 2026-11-07", "key": "latest@2026-11-07T03:09:45Z"}))


if __name__ == "__main__":
    unittest.main()
