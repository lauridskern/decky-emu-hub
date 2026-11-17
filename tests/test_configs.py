"""Config editors keep everything they do not set; presets back up and restore."""

import json
import os
import tempfile
import unittest

import helpers  # noqa: F401
from backend import configfmt, presets


class FormatTest(unittest.TestCase):
    def test_ini_replaces_keeps_and_appends(self):
        text = "; comment\n[UI]\nStartFullscreen = false\nTheme = dark\n\n[Folders]\nBios = /old\n"
        out = configfmt.ini_set(text, {"UI": {"StartFullscreen": "true", "ConfirmShutdown": "false"},
                                       "Folders": {"Bios": "/new"}, "Pad1": {"Up": "SDL-0/DPadUp"}})
        self.assertIn("; comment", out)
        self.assertIn("Theme = dark", out)
        self.assertIn("StartFullscreen = true", out)
        self.assertNotIn("StartFullscreen = false", out)
        self.assertEqual(out.count("[UI]"), 1)
        # the new key lands inside its section, before the blank line
        self.assertLess(out.index("ConfirmShutdown"), out.index("[Folders]"))
        self.assertIn("Bios = /new", out)
        self.assertTrue(out.rstrip().endswith("Up = SDL-0/DPadUp"))
        self.assertEqual(configfmt.ini_get(out, "UI", "Theme"), "dark")
        self.assertEqual(configfmt.ini_get(out, "Folders", "Bios"), "/new")

    def test_ini_does_not_touch_the_same_key_in_another_section(self):
        text = "[Pad1]\nType = DualShock2\n[Pad2]\nType = DualShock2\n"
        out = configfmt.ini_set(text, {"Pad1": {"Type": "None"}})
        self.assertEqual(configfmt.ini_get(out, "Pad2", "Type"), "DualShock2")
        self.assertEqual(configfmt.ini_get(out, "Pad1", "Type"), "None")

    def test_ini_keeps_the_files_separator_and_qt_keys(self):
        text = "[UI]\nfullscreen=false\nfullscreen\\default=true\n"
        out = configfmt.ini_set(text, {"UI": {"fullscreen": "true", "fullscreen\\default": "false", "confirmClose": "false"}})
        self.assertIn("fullscreen=true\n", out)
        self.assertIn("fullscreen\\default=false", out)
        self.assertIn("confirmClose=false", out)
        self.assertNotIn(" = ", out)

    def test_ini_prefix_keys_do_not_collide(self):
        text = "[Graphics]\nFullScreenMulti = False\nFullScreen = False\n"
        out = configfmt.ini_set(text, {"Graphics": {"FullScreen": "True"}})
        self.assertIn("FullScreenMulti = False", out)
        self.assertIn("FullScreen = True", out)

    def test_cfg(self):
        text = 'video_fullscreen = "false"\nmenu_driver = "ozone"\n'
        out = configfmt.cfg_set(text, {"video_fullscreen": "true", "system_directory": "/bios"})
        self.assertIn('menu_driver = "ozone"', out)
        self.assertEqual(configfmt.cfg_get(out, "video_fullscreen"), "true")
        self.assertEqual(configfmt.cfg_get(out, "system_directory"), "/bios")

    def test_json_merges_lists(self):
        text = json.dumps({"version": 73, "game_dirs": ["/mine"], "start_fullscreen": False})
        out = json.loads(configfmt.json_set(text, {"start_fullscreen": True, "game_dirs": ["/lib/switch", "/mine"]}))
        self.assertEqual(out["version"], 73)
        self.assertEqual(out["game_dirs"], ["/mine", "/lib/switch"])
        self.assertTrue(out["start_fullscreen"])

    def test_xml(self):
        text = "<?xml version='1.0'?>\n<content>\n<mlc_path></mlc_path>\n<fullscreen>false</fullscreen>\n<GamePaths><Entry>/a</Entry></GamePaths>\n</content>\n"
        out = configfmt.xml_set(text, {"fullscreen": "true", "check_update": "false", "GamePaths": ["/b"]})
        self.assertEqual(configfmt.xml_get(out, "fullscreen"), "true")
        self.assertEqual(configfmt.xml_get(out, "GamePaths"), ["/a", "/b"])
        self.assertIsNotNone(configfmt.xml_get(out, "mlc_path"))

    def test_yaml(self):
        text = "Core:\n  PPU Decoder: Recompiler (LLVM)\nMiscellaneous:\n  Start games in fullscreen mode: false\n  Show trophy popups: true\nLog: {}\n"
        out = configfmt.yaml_set(text, {"Miscellaneous": {"Start games in fullscreen mode": True,
                                                          "Exit RPCS3 when process finishes": True}})
        self.assertIn("  Start games in fullscreen mode: true", out)
        self.assertIn("  Show trophy popups: true", out)
        self.assertLess(out.index("Exit RPCS3"), out.index("Log: {}"))
        self.assertEqual(configfmt.yaml_get(out, "Core", "PPU Decoder"), "Recompiler (LLVM)")

    def test_toml(self):
        text = "[general]\nshow_welcome = true\n\n[input.bindings]\nport1 = 'abc'\n"
        out = configfmt.toml_set(text, {"general": {"show_welcome": False}, "sys.files": {"bootrom_path": "/b/mcpx_1.0.bin"}})
        self.assertIn("show_welcome = false", out)
        self.assertIn("port1 = 'abc'", out)
        self.assertIn('bootrom_path = "/b/mcpx_1.0.bin"', out)


class PresetTest(unittest.TestCase):
    def setUp(self):
        self.home = tempfile.mkdtemp()
        self.root = os.path.join(self.home, "EmuDecky")
        os.makedirs(os.path.join(self.root, "roms", "ps2"))
        self.backups = presets.Backups(os.path.join(self.home, "runtime", "backups"))

    def path(self, rel):
        return os.path.join(self.home, rel)

    def test_every_preset_has_a_path_per_install_method_it_can_have(self):
        from backend import catalogue
        for emu in catalogue.EMULATORS:
            if not emu.get("preset"):
                continue
            preset = presets.PRESETS[emu["preset"]]
            for spec in preset["files"]:
                if emu["method"] == "appimage":
                    self.assertIn("appimage", spec["path"], emu["id"])
                if emu.get("flatpak") or emu.get("flatpak_alt"):
                    self.assertIn("flatpak", spec["path"], emu["id"])

    def test_apply_new_file_with_version_stamp_then_restore_removes_it(self):
        target = self.path(".config/PCSX2/inis/PCSX2.ini")
        self.assertEqual(presets.status("pcsx2", "appimage", self.home, self.root), "ready")
        result = presets.apply("pcsx2", "pcsx2", "appimage", self.home, self.root, self.backups)
        self.assertTrue(result["ok"], result)
        with open(target) as handle:
            text = handle.read()
        self.assertIn("SettingsVersion = 1", text)
        self.assertIn(f"RecursivePaths = {self.root}/roms/ps2", text)
        self.assertIn(f"Bios = {self.root}/bios", text)
        self.assertIn("Cross = SDL-0/A", text)
        self.assertEqual(presets.status("pcsx2", "appimage", self.home, self.root), "applied")
        restored = self.backups.restore("pcsx2")
        self.assertTrue(restored["ok"])
        self.assertFalse(os.path.exists(target))

    def test_apply_keeps_the_users_keys_and_restore_brings_back_the_original(self):
        target = self.path(".local/share/duckstation/settings.ini")
        os.makedirs(os.path.dirname(target))
        original = "[Main]\nSettingsVersion = 3\nStartFullscreen = false\nTheme = darkfusion\n[GPU]\nRenderer = Vulkan\n"
        with open(target, "w") as handle:
            handle.write(original)
        self.assertEqual(presets.status("duckstation", "appimage", self.home, self.root), "partial")
        self.assertTrue(presets.apply("duckstation", "duckstation", "appimage", self.home, self.root, self.backups)["ok"])
        with open(target) as handle:
            text = handle.read()
        self.assertIn("Theme = darkfusion", text)
        self.assertIn("Renderer = Vulkan", text)
        self.assertIn("StartFullscreen = true", text)
        self.assertEqual(text.count("SettingsVersion"), 1)
        # a second apply does not replace the saved original
        presets.apply("duckstation", "duckstation", "appimage", self.home, self.root, self.backups)
        self.assertTrue(self.backups.restore("duckstation")["ok"])
        with open(target) as handle:
            self.assertEqual(handle.read(), original)

    def test_json_preset_waits_for_first_start(self):
        self.assertEqual(presets.status("ryubing", "appimage", self.home, self.root), "waiting")
        result = presets.apply("ryubing", "ryubing", "appimage", self.home, self.root, self.backups)
        self.assertFalse(result["ok"])
        self.assertEqual(result["state"], "waiting")
        target = self.path(".config/Ryujinx/Config.json")
        os.makedirs(os.path.dirname(target))
        with open(target, "w") as handle:
            json.dump({"version": 73, "game_dirs": [], "start_fullscreen": False}, handle)
        self.assertTrue(presets.apply("ryubing", "ryubing", "appimage", self.home, self.root, self.backups)["ok"])
        self.assertEqual(presets.status("ryubing", "appimage", self.home, self.root), "applied")
        with open(target) as handle:
            data = json.load(handle)
        self.assertEqual(data["version"], 73)
        self.assertEqual(data["game_dirs"], [f"{self.root}/roms/switch"])

    def test_emudeck_folder_names_win(self):
        os.makedirs(os.path.join(self.root, "roms", "gamecube"))
        self.assertTrue(presets.apply("dolphin", "dolphin", "flatpak", self.home, self.root, self.backups)["ok"])
        with open(self.path(".var/app/org.DolphinEmu.dolphin-emu/config/dolphin-emu/Dolphin.ini")) as handle:
            text = handle.read()
        self.assertIn(f"ISOPath0 = {self.root}/roms/gamecube", text)
        self.assertIn(f"ISOPath1 = {self.root}/roms/wii", text)

    def test_unparseable_file_is_left_alone(self):
        target = self.path(".config/Cemu/settings.xml")
        os.makedirs(os.path.dirname(target))
        with open(target, "w") as handle:
            handle.write("<content><broken>")
        result = presets.apply("cemu", "cemu", "appimage", self.home, self.root, self.backups)
        self.assertFalse(result["ok"])
        with open(target) as handle:
            self.assertEqual(handle.read(), "<content><broken>")

    def test_every_preset_applies_to_an_empty_or_minimal_file(self):
        for preset_id, preset in presets.PRESETS.items():
            home = tempfile.mkdtemp()
            for method in ("appimage", "flatpak"):
                files = presets.files_for(preset_id, method, home)
                for spec in files:
                    if not spec.get("create"):
                        os.makedirs(os.path.dirname(spec["abs"]), exist_ok=True)
                        seed = {"json": "{}", "xml": "<content></content>", "yaml": "Core:\n  x: 1\n"}[spec["format"]]
                        with open(spec["abs"], "w") as handle:
                            handle.write(seed)
                if not files:
                    continue
                result = presets.apply(preset_id, preset_id, method, home, self.root, presets.Backups(os.path.join(home, "b")))
                self.assertTrue(result["ok"], (preset_id, method, result))
                self.assertEqual(presets.status(preset_id, method, home, self.root), "applied", (preset_id, method))


if __name__ == "__main__":
    unittest.main()
