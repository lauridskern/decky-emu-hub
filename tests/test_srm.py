"""Which emulator opens a console's games: Steam ROM Manager's parsers (backend/srm.py)."""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend import srm  # noqa: E402

L = "/home/deck/Emulation/tools/launchers"


def parser(title, exe, folder, disabled=False, args='"${filePath}"', glob="${title}@(.nsp|.xci)"):
    return {
        "parserType": "Glob", "configTitle": title, "disabled": disabled,
        "executable": {"path": exe, "shortcutPassthrough": False, "appendArgsToExecutable": True},
        "executableArgs": args, "romDirectory": "${romsdirglobal}/" + folder,
        "parserInputs": {"glob": glob}, "steamCategories": ["${parser}"],
    }


SETUP = [
    parser("Nintendo Switch - Eden", f"{L}/eden.sh", "switch"),
    parser("Nintendo Switch - Ryujinx", f"{L}/ryujinx.sh", "switch"),
    parser("Sony PlayStation - DuckStation", f"{L}/duckstation.sh", "psx", glob="${title}@(.chd|.m3u)"),
    parser("Sony PlayStation - RetroArch Beetle PSX HW", "${retroarchpath}", "psx", disabled=True,
           args="-L ${racores}/mednafen_psx_hw_libretro.so \"${filePath}\""),
    parser("Sony PlayStation - RetroArch SwanStation", "${retroarchpath}", "psx", disabled=True,
           args="-L ${racores}/swanstation_libretro.so \"${filePath}\""),
    parser("Nintendo GameCube - Dolphin", "/usr/bin/flatpak", "gc", args='run org.DolphinEmu.dolphin-emu -b -e "${filePath}"'),
    parser("Nintendo GameCube - PrimeHack", f"{L}/primehack.sh", "gc", disabled=True),
    parser("Nintendo Wii U - Cemu (.rpx)", f"{L}/cemu.sh", "wiiu/roms/"),
    parser("Nintendo Wii U - Cemu (.wud, .wux, .wua)", f"{L}/cemu.sh", "wiiu/roms/"),
    parser("Nintendo 3DS - Citra", f"{L}/citra.sh", "n3ds"),
    parser("Nintendo 3DS - Mystery", f"{L}/mystery-emu.sh", "n3ds", disabled=True),
]


class SrmTest(unittest.TestCase):
    def setUp(self):
        self.home = tempfile.mkdtemp()
        self.folder = os.path.join(self.home, ".config", "steam-rom-manager", "userData")
        os.makedirs(self.folder)
        self.path = os.path.join(self.folder, "userConfigurations.json")
        self.write(SETUP)
        self.backups = os.path.join(self.home, "runtime", "backups", "srm")

    def write(self, data):
        with open(self.path, "w") as handle:
            json.dump(data, handle, indent=4)

    def read(self):
        with open(self.path) as handle:
            return {p["configTitle"]: p for p in json.load(handle)}

    def group(self, installed, console):
        return next(g for g in srm.choices(self.home, installed)["consoles"] if g["console"] == console)

    def test_same_places_as_rom_store(self):
        here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        rom_store = os.path.join(os.path.dirname(here), "rom-store-decky", "backend", "steam.py")
        if not os.path.isfile(rom_store):
            self.skipTest("ROM-Store is not checked out next to Emu Hub")
        with open(rom_store) as handle:
            text = handle.read()
        for rel in srm.SRM_DIRS:
            self.assertIn(f'"{rel}"', text)

    def test_consoles_with_a_choice(self):
        result = srm.choices(self.home, {"eden": {}, "duckstation": {}})
        self.assertEqual(result["srm"], self.path)
        self.assertEqual([g["console"] for g in result["consoles"]], ["gc", "n3ds", "psx", "switch"])  # not wiiu
        switch = self.group({"eden": {}}, "switch")
        self.assertEqual(switch["current"], "eden")                        # first enabled parser wins
        options = {o["key"]: o for o in switch["options"]}
        self.assertTrue(options["eden"]["installed"])
        self.assertFalse(options["ryubing"]["installed"])
        psx = self.group({}, "psx")
        retroarch = next(o for o in psx["options"] if o["key"] == "retroarch")
        self.assertEqual(len(retroarch["parsers"]), 2)                     # both cores, one option
        gc = self.group({}, "gc")
        self.assertEqual(gc["current"], "dolphin")                         # flatpak run <id> is recognised
        n3ds = self.group({}, "n3ds")
        unknown = next(o for o in n3ds["options"] if o["key"].startswith("other:"))
        self.assertIsNone(unknown["installed"])
        self.assertEqual(unknown["label"], "Mystery")

    def test_choose_switches_and_keeps_a_backup(self):
        result = srm.choose(self.home, "switch", "ryubing", self.backups)
        self.assertTrue(result["ok"] and result["changed"])
        parsers = self.read()
        self.assertTrue(parsers["Nintendo Switch - Eden"]["disabled"])
        self.assertFalse(parsers["Nintendo Switch - Ryujinx"]["disabled"])
        self.assertFalse(parsers["Sony PlayStation - DuckStation"]["disabled"])  # other consoles untouched
        self.assertEqual(len(os.listdir(self.backups)), 1)
        with open(os.path.join(self.backups, os.listdir(self.backups)[0])) as handle:
            self.assertFalse(json.load(handle)[0]["disabled"])                   # the backup is the old file
        self.assertEqual(self.group({}, "switch")["current"], "ryubing")
        again = srm.choose(self.home, "switch", "ryubing", self.backups)
        self.assertTrue(again["ok"])
        self.assertFalse(again["changed"])
        self.assertEqual(len(os.listdir(self.backups)), 1)

    def test_choosing_retroarch_enables_its_cores_unless_one_is_chosen(self):
        srm.choose(self.home, "psx", "retroarch", self.backups)
        parsers = self.read()
        self.assertTrue(parsers["Sony PlayStation - DuckStation"]["disabled"])
        self.assertFalse(parsers["Sony PlayStation - RetroArch Beetle PSX HW"]["disabled"])
        self.assertFalse(parsers["Sony PlayStation - RetroArch SwanStation"]["disabled"])
        # The user turns one core off; choosing RetroArch again keeps that.
        data = list(self.read().values())
        for p in data:
            if p["configTitle"].endswith("SwanStation"):
                p["disabled"] = True
            if p["configTitle"].endswith("DuckStation"):
                p["disabled"] = False
        self.write(data)
        srm.choose(self.home, "psx", "retroarch", self.backups)
        parsers = self.read()
        self.assertFalse(parsers["Sony PlayStation - RetroArch Beetle PSX HW"]["disabled"])
        self.assertTrue(parsers["Sony PlayStation - RetroArch SwanStation"]["disabled"])
        self.assertTrue(parsers["Sony PlayStation - DuckStation"]["disabled"])

    def test_unknown_choice_and_missing_file(self):
        self.assertFalse(srm.choose(self.home, "switch", "dolphin", self.backups)["ok"])
        empty = tempfile.mkdtemp()
        self.assertEqual(srm.choices(empty, {}), {"srm": None, "consoles": []})
        self.assertFalse(srm.choose(empty, "switch", "eden", self.backups)["ok"])

    def test_auto_choose_only_fixes_a_missing_emulator(self):
        # Eden (first) is not installed, Ryubing is: Switch games move to Ryubing.
        done = srm.auto_choose(self.home, {"ryubing": {}}, self.backups)
        self.assertEqual(done, [{"console": "switch", "from": "Eden", "to": "Ryubing"}])
        self.assertEqual(self.group({}, "switch")["current"], "ryubing")
        # Both installed: the user's choice stays.
        self.assertEqual(srm.auto_choose(self.home, {"ryubing": {}, "eden": {}}, self.backups), [])
        # Nothing installed for a console, or a launcher Emu Hub does not know: untouched.
        self.assertEqual(srm.auto_choose(self.home, {}, self.backups), [])
        self.assertEqual(self.group({}, "n3ds")["current"], "azahar")


if __name__ == "__main__":
    unittest.main()


class LauncherTest(unittest.TestCase):
    """Emu Hub's own launchers (backend/launchers.py) and the switch in SRM."""

    def setUp(self):
        self.home = tempfile.mkdtemp()
        folder = os.path.join(self.home, ".config", "steam-rom-manager", "userData")
        os.makedirs(folder)
        self.path = os.path.join(folder, "userConfigurations.json")
        launchers_dir = os.path.join(self.home, "Emulation", "tools", "launchers")
        os.makedirs(launchers_dir)
        for name in ("eden.sh", "ryujinx.sh"):
            with open(os.path.join(launchers_dir, name), "w") as handle:
                handle.write("#!/bin/bash\n")
        with open(self.path, "w") as handle:
            json.dump([
                parser("Nintendo Switch - Eden", f"{launchers_dir}/eden.sh", "switch",
                       args='vblank_mode=0 %command% -f -g "${filePath}"'),
                parser("Nintendo Switch - Ryujinx", f"{launchers_dir}/ryujinx.sh", "switch", disabled=True),
                parser("Sony PlayStation Portable - PPSSPP", f"{launchers_dir}/ppsspp.sh", "psp"),
                parser("SNES - RetroArch", "${retroarchpath}", "snes"),
            ], handle, indent=4)
        self.runtime = os.path.join(self.home, "runtime")
        self.state = os.path.join(self.runtime, "launchers.json")
        self.backups = os.path.join(self.runtime, "backups", "srm")

    def parsers(self):
        with open(self.path) as handle:
            return {p["configTitle"]: p for p in json.load(handle)}

    def test_check_names_the_problems(self):
        installed = {"eden": {"method": "appimage"}}
        check = {row["emu_id"]: row for row in srm.launch_check(self.home, installed)["emulators"]}
        self.assertNotIn("retroarch", check)
        self.assertNotIn("ryubing", check)  # its parser is off
        eden = check["eden"]
        self.assertEqual(eden["kind"], "emudeck")
        self.assertFalse(eden["ok"])
        self.assertIn("EmuDeck's files", eden["problems"][0])   # no ~/.config/EmuDeck here
        self.assertTrue(any("ppsspp.sh does not exist" in p for p in check["ppsspp"]["problems"]))

    def test_switch_to_emu_hub_and_back(self):
        result = srm.use_emuhub_launchers(self.home, self.backups, self.state)
        self.assertTrue(result["ok"])
        self.assertEqual(result["changed"], 3)                   # not RetroArch
        parsers = self.parsers()
        eden = parsers["Nintendo Switch - Eden"]["executable"]["path"]
        self.assertEqual(eden, os.path.join(self.home, ".local/share/emu-hub/launchers/eden.sh"))
        self.assertEqual(parsers["Nintendo Switch - Eden"]["executableArgs"], 'vblank_mode=0 %command% -f -g "${filePath}"')
        self.assertEqual(parsers["SNES - RetroArch"]["executable"]["path"], "${retroarchpath}")
        self.assertTrue(os.access(eden, os.X_OK))
        # Still recognised as Eden for "Which emulator opens games".
        self.assertEqual(srm.emulator_of(parsers["Nintendo Switch - Eden"])[1], "eden")
        check = {row["emu_id"]: row for row in srm.launch_check(self.home, {"eden": {}})["emulators"]}
        self.assertTrue(check["eden"]["ok"])
        self.assertEqual(check["eden"]["kind"], "emuhub")
        self.assertEqual(srm.use_emuhub_launchers(self.home, self.backups, self.state)["changed"], 0)
        back = srm.use_original_launchers(self.home, self.backups, self.state)
        self.assertEqual(back["changed"], 3)
        self.assertTrue(self.parsers()["Nintendo Switch - Eden"]["executable"]["path"].endswith("tools/launchers/eden.sh"))

    def test_launcher_script_starts_the_appimage_with_the_arguments(self):
        import subprocess
        from backend import launchers
        apps = os.path.join(self.home, "Applications")
        os.makedirs(apps)
        out = os.path.join(self.home, "args.txt")
        fake = os.path.join(apps, "Eden.AppImage")
        with open(fake, "w") as handle:
            handle.write(f'#!/bin/sh\nprintf "%s|" "$@" > "{out}"\n')
        os.chmod(fake, 0o755)
        script = launchers.write(self.home, "eden")
        env = dict(os.environ, HOME=self.home)
        subprocess.run([script, "-f", "-g", "/roms/switch/Super Mario Bros. Wonder.nsp"], env=env, check=True, timeout=10)
        with open(out) as handle:
            self.assertEqual(handle.read(), "-f|-g|/roms/switch/Super Mario Bros. Wonder.nsp|")
        # Another name in ~/Applications (an EmuDeck or hand install) is found too.
        os.rename(fake, os.path.join(apps, "eden-nightly.AppImage"))
        os.remove(out)
        subprocess.run([script, "x"], env=env, check=True, timeout=10)
        self.assertTrue(os.path.isfile(out))
        # Nothing installed: fails, and says so in launch.log.
        os.remove(os.path.join(apps, "eden-nightly.AppImage"))
        env["PATH"] = "/usr/bin:/bin"
        self.assertNotEqual(subprocess.run([script], env=env, timeout=10).returncode, 0)
        self.assertIn("Eden is not installed", launchers.last_failures(self.home)[-1])
