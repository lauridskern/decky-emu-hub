"""The service end to end with a fake home, no network and no flatpak."""

import asyncio
import os
import tempfile
import unittest
from unittest import mock

from helpers import release
from backend import flatpak, releases
from backend.service import Service
from backend.settings import Settings


def fake_fetch(url, token=None):
    if "flathub.org" in url:
        return {"releases": [{"version": "9.9"}]}
    for emu_id, repo in (("pcsx2", "PCSX2/pcsx2"), ("duckstation", "stenzek/duckstation"), ("cemu", "cemu-project/Cemu")):
        if repo in url:
            return release(emu_id)
    raise releases.SourceError("no release found")


class ServiceTest(unittest.TestCase):
    def setUp(self):
        self.home = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.home, "Applications"))
        with open(os.path.join(self.home, "Applications", "pcsx2-Qt.AppImage"), "wb") as handle:
            handle.write(b"\x7fELF" + b"\0" * 100)
        self.svc = Service(Settings(os.path.join(self.home, "s.json")), os.path.join(self.home, "rt"), self.home)
        releases.clear_cache()
        self.patches = [
            mock.patch.object(flatpak, "installed", return_value={"org.libretro.RetroArch": {"version": "1.22.1", "installation": "system"}}),
            mock.patch.object(flatpak, "updates", return_value={"org.libretro.RetroArch": "1.22.2"}),
            mock.patch.object(flatpak, "available", return_value=True),
            mock.patch.object(releases, "fetch_json", side_effect=fake_fetch),
        ]
        for patch in self.patches:
            patch.start()

    def tearDown(self):
        for patch in self.patches:
            patch.stop()
        releases.clear_cache()

    def test_state_and_update_check(self):
        state = asyncio.run(self.svc.check_updates(force=True))
        views = {v["id"]: v for v in state["emulators"]}
        self.assertEqual(len(views), 17)
        self.assertEqual(views["pcsx2"]["installed"]["method"], "appimage")
        self.assertTrue(views["pcsx2"]["unknown_version"])
        self.assertFalse(views["pcsx2"]["update"])
        self.assertEqual(views["pcsx2"]["latest"], "2.8.2")
        self.assertTrue(views["retroarch"]["update"])
        self.assertEqual(views["retroarch"]["latest"], "1.22.2")
        self.assertEqual(state["updates"], 1)
        self.assertIsNone(views["dolphin"]["installed"])
        self.assertEqual(views["dolphin"]["latest"], "9.9")
        self.assertIn("source(s) could not be checked", state["check_error"])
        self.assertEqual(views["pcsx2"]["preset"]["state"], "ready")

    def test_known_old_version_is_an_update_and_plans_in_place(self):
        path = os.path.join(self.home, "Applications", "pcsx2-Qt.AppImage")
        self.svc.manifest["pcsx2"] = {"method": "appimage", "path": path, "version": "2.8.1", "key": "v2.8.1", "managed": True}
        state = asyncio.run(self.svc.check_updates(force=True))
        self.assertTrue(next(v for v in state["emulators"] if v["id"] == "pcsx2")["update"])
        from backend import catalogue, detect
        copy = detect.detect(catalogue.get("pcsx2"), self.home, self.svc.manifest, {})
        plan = self.svc._plan(catalogue.get("pcsx2"), "update", copy)
        self.assertEqual(plan["target"], path)
        self.assertTrue(plan["url"].endswith("linux-appimage-x64-Qt.AppImage"))

    def test_shortcut_plans(self):
        plan = asyncio.run(self.svc.shortcut_plan("pcsx2"))["plan"]
        self.assertTrue(plan["exe"].endswith('pcsx2-Qt.AppImage"'))
        self.assertEqual(plan["launchOptions"], "")
        plan = asyncio.run(self.svc.shortcut_plan("retroarch"))["plan"]
        self.assertEqual(plan["launchOptions"], "run org.libretro.RetroArch")
        self.assertIsNone(asyncio.run(self.svc.shortcut_plan("dolphin"))["plan"])

    def test_settings_hide_the_token(self):
        view = asyncio.run(self.svc.set_settings({"github_token": "abc", "check_hours": 999, "bogus": 1}))
        self.assertNotIn("github_token", view)
        self.assertTrue(view["github_token_set"])
        self.assertEqual(view["check_hours"], 168)
        self.assertNotIn("bogus", view)


if __name__ == "__main__":
    unittest.main()
