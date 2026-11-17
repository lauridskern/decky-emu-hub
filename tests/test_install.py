"""Detection with a fake home, flatpak output parsing, the library, BIOS
status and the AppImage installer against a local HTTP server."""

import http.server
import io
import os
import tempfile
import threading
import unittest
import zipfile

import helpers  # noqa: F401
from backend import bios, catalogue, detect, flatpak, installer, library, procenv

ELF = b"\x7fELF" + b"\0" * 2000


def write(path, data=b"x" * 2000):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as handle:
        handle.write(data)


class FlatpakParseTest(unittest.TestCase):
    def test_list(self):
        out = ("org.libretro.RetroArch\t1.22.2\tsystem\n"
               "org.DolphinEmu.dolphin-emu\t2609b\tuser\n"
               "org.DolphinEmu.dolphin-emu\t2506\tsystem\n")
        apps = flatpak.parse_list(out)
        self.assertEqual(apps["org.libretro.RetroArch"], {"version": "1.22.2", "installation": "system"})
        # the user copy is the one `flatpak run` starts
        self.assertEqual(apps["org.DolphinEmu.dolphin-emu"]["installation"], "user")

    def test_updates(self):
        out = "Application ID\tVersion\nnet.pcsx2.PCSX2\t2.8.2\norg.ppsspp.PPSSPP\t\n"
        self.assertEqual(flatpak.parse_updates(out), {"net.pcsx2.PCSX2": "2.8.2", "org.ppsspp.PPSSPP": ""})

    def test_progress(self):
        self.assertAlmostEqual(flatpak.parse_progress("Installing 1/2… ████▍  23%  1.2 MB/s\r"), 0.23)
        self.assertAlmostEqual(flatpak.parse_progress("…  45% … 100%"), 1.0)
        self.assertIsNone(flatpak.parse_progress("Looking for matches…"))

    def test_commands(self):
        self.assertEqual(flatpak.command("install", "a.b.C"),
                         ["flatpak", "install", "--user", "-y", "--noninteractive", "flathub", "a.b.C"])
        self.assertIn("--system", flatpak.command("update", "a.b.C", "system"))
        self.assertIn("--user", flatpak.command("uninstall", "a.b.C", "user"))


class EnvTest(unittest.TestCase):
    def test_drops_pyinstaller_library_path(self):
        env = procenv.clean_env("/home/deck", {"LD_LIBRARY_PATH": "/tmp/_MEI123", "PATH": "/x", "LD_PRELOAD": "a.so"})
        self.assertNotIn("LD_LIBRARY_PATH", env)
        self.assertNotIn("LD_PRELOAD", env)
        self.assertEqual(env["HOME"], "/home/deck")
        self.assertEqual(env["XDG_DATA_HOME"], "/home/deck/.local/share")
        self.assertTrue(env["PATH"].startswith("/x:"))

    def test_restores_the_original_library_path(self):
        env = procenv.clean_env("/h", {"LD_LIBRARY_PATH": "/tmp/_MEI1", "LD_LIBRARY_PATH_ORIG": "/usr/lib32"})
        self.assertEqual(env["LD_LIBRARY_PATH"], "/usr/lib32")


class DetectTest(unittest.TestCase):
    def setUp(self):
        self.home = tempfile.mkdtemp()

    def test_emudeck_appimages_are_found_with_unknown_version(self):
        write(os.path.join(self.home, "Applications", "pcsx2-Qt.AppImage"), ELF)
        write(os.path.join(self.home, "Applications", "DuckStation.AppImage.bak"), ELF)
        found = detect.detect_all(self.home, {}, {})
        self.assertEqual(found["pcsx2"]["method"], "appimage")
        self.assertIsNone(found["pcsx2"]["version"])
        self.assertNotIn("duckstation", found)

    def test_vita3k_and_ryujinx_folders(self):
        write(os.path.join(self.home, "Applications", "Vita3K", "Vita3K"), ELF)
        write(os.path.join(self.home, "Applications", "publish", "Ryujinx"), ELF)
        found = detect.detect_all(self.home, {}, {})
        self.assertIn("vita3k", found)
        self.assertIn("ryubing", found)

    def test_emudeck_eden_appimage(self):
        write(os.path.join(self.home, "Applications", "Eden.AppImage"), ELF)
        found = detect.detect_all(self.home, {}, {})
        self.assertEqual(found["eden"]["method"], "appimage")
        self.assertNotIn("ryubing", found)
        found = detect.detect_all(tempfile.mkdtemp(), {}, {"dev.eden_emu.eden": {"version": "0.2.1", "installation": "user"}})
        self.assertEqual(found["eden"]["app_id"], "dev.eden_emu.eden")

    def test_flathub_copy_of_an_appimage_emulator(self):
        found = detect.detect_all(self.home, {}, {"org.ppsspp.PPSSPP": {"version": "1.20.3", "installation": "system"}})
        self.assertEqual(found["ppsspp"], {"method": "flatpak", "app_id": "org.ppsspp.PPSSPP", "version": "1.20.3",
                                           "installation": "system", "managed": False, "key": None})

    def test_manifest_wins_and_a_deleted_file_does_not_count(self):
        path = os.path.join(self.home, "Applications", "Cemu.AppImage")
        write(path, ELF)
        manifest = {"cemu": {"method": "appimage", "path": path, "version": "2.6", "key": "v2.6", "managed": True}}
        self.assertEqual(detect.detect_all(self.home, manifest, {})["cemu"]["version"], "2.6")
        os.remove(path)
        self.assertNotIn("cemu", detect.detect_all(self.home, manifest, {}))


class LibraryTest(unittest.TestCase):
    def test_emudeck_library_is_preferred(self):
        home = tempfile.mkdtemp()
        media = os.path.join(home, "media")
        self.assertEqual(library.default_root(home, media + "/*/*"), os.path.join(home, "Emulation"))
        os.makedirs(os.path.join(home, "EmuDecky"))
        self.assertEqual(library.default_root(home, media + "/*/*"), os.path.join(home, "EmuDecky"))
        os.makedirs(os.path.join(media, "deck", "sd", "Emulation", "roms"))
        self.assertEqual(library.default_root(home, media + "/*/*"), os.path.join(media, "deck", "sd", "Emulation"))
        os.makedirs(os.path.join(home, "Emulation", "roms"))
        self.assertEqual(library.default_root(home, media + "/*/*"), os.path.join(home, "Emulation"))

    def test_create_folders_uses_rom_store_names(self):
        root = os.path.join(tempfile.mkdtemp(), "Emulation")
        result = library.create_folders(root)
        self.assertTrue(result["ok"])
        for name in ("roms/gc", "roms/psx", "roms/ps2", "roms/switch", "roms/3ds", "roms/arcades", "bios", "saves"):
            self.assertTrue(os.path.isdir(os.path.join(root, name)), name)
        self.assertEqual(library.create_folders(root)["made"], 0)
        info = library.describe(root)
        self.assertTrue(info["ready"])


class BiosTest(unittest.TestCase):
    def test_found_and_missing(self):
        home = tempfile.mkdtemp()
        folder = os.path.join(home, "Emulation", "bios")
        write(os.path.join(folder, "SCPH5501.BIN"))
        write(os.path.join(home, ".config", "Ryujinx", "system", "prod.keys"))
        report = {r["console"]: r for r in bios.report(["psx", "ps2", "switch", "nes"], folder, home)}
        self.assertNotIn("nes", report)
        self.assertTrue(report["psx"]["found"])
        self.assertIsNone(report["ps2"]["found"])
        write(os.path.join(folder, "SCPH-70012_BIOS_V12_USA_200.BIN"))
        self.assertTrue(bios.report(["ps2"], folder, home)[0]["found"].endswith("200.BIN"))
        self.assertTrue(report["switch"]["found"].endswith("prod.keys"))
        eden_only = tempfile.mkdtemp()
        write(os.path.join(eden_only, ".local", "share", "eden", "keys", "prod.keys"))
        self.assertIn("/eden/keys/prod.keys", bios.report(["switch"], folder, eden_only)[0]["found"])


class Server:
    def __init__(self, files):
        class Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):  # noqa: N802
                body = files.get(self.path)
                if body is None:
                    self.send_response(404)
                    self.end_headers()
                    return
                self.send_response(200)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *args):
                pass

        self.httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.httpd.server_address[1]}"
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()

    def close(self):
        self.httpd.shutdown()
        self.httpd.server_close()


class InstallerTest(unittest.TestCase):
    def setUp(self):
        zipped = io.BytesIO()
        with zipfile.ZipFile(zipped, "w") as zf:
            zf.writestr("melonDS-x86_64.AppImage", ELF)
        self.server = Server({"/app.AppImage": ELF, "/page.AppImage": b"<html>" + b" " * 3000, "/app.zip": zipped.getvalue()})
        self.home = tempfile.mkdtemp()
        self.target = os.path.join(self.home, "Applications", "Test.AppImage")

    def tearDown(self):
        self.server.close()

    def job(self, url, **extra):
        return installer.Job("test", "install", dict({"method": "appimage", "url": self.server.url + url,
                                                      "target": self.target, "size": 0}, **extra))

    def test_installs_and_replaces_keeping_nothing_behind(self):
        write(self.target, b"old")
        installer.install_appimage(self.job("/app.AppImage"))
        with open(self.target, "rb") as handle:
            self.assertEqual(handle.read(), ELF)
        self.assertTrue(os.access(self.target, os.X_OK))
        self.assertEqual(sorted(os.listdir(os.path.dirname(self.target))), ["Test.AppImage"])

    def test_zip_member(self):
        installer.install_appimage(self.job("/app.zip", zip_member=r"\.AppImage$"))
        with open(self.target, "rb") as handle:
            self.assertEqual(handle.read(), ELF)

    def test_a_web_page_is_never_installed_and_the_old_file_stays(self):
        write(self.target, b"old")
        with self.assertRaises(RuntimeError):
            installer.install_appimage(self.job("/page.AppImage"))
        with open(self.target, "rb") as handle:
            self.assertEqual(handle.read(), b"old")
        self.assertEqual(os.listdir(os.path.dirname(self.target)), ["Test.AppImage"])

    def test_cancel(self):
        job = self.job("/app.AppImage")
        job.cancel.set()
        with self.assertRaises(installer.Cancelled):
            installer.install_appimage(job)
        self.assertFalse(os.path.exists(self.target))

    def test_queue_runs_and_reports(self):
        done = threading.Event()
        finished = []

        def on_finished(job):
            finished.append(job.view())
            done.set()

        worker = installer.Installer(self.home, on_finished)
        worker.add("test", "install", {"method": "appimage", "url": self.server.url + "/app.AppImage", "target": self.target})
        self.assertTrue(done.wait(10))
        worker.stop()
        self.assertEqual(finished[0]["state"], "done")
        self.assertEqual(finished[0]["progress"], 1.0)

    def test_remove_only_inside_applications(self):
        outside = os.path.join(self.home, "elsewhere.AppImage")
        write(outside, ELF)
        with self.assertRaises(RuntimeError):
            installer.remove_appimage(installer.Job("x", "uninstall", {"path": outside}), self.home)
        self.assertTrue(os.path.exists(outside))
        write(self.target, ELF)
        installer.remove_appimage(installer.Job("x", "uninstall", {"path": self.target}), self.home)
        self.assertFalse(os.path.exists(self.target))


if __name__ == "__main__":
    unittest.main()
