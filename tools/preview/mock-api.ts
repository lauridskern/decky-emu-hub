/**
 * Mock of @decky/api for the preview: an in-memory backend with a mix of
 * states (installed, update available, version unknown, a job running,
 * not installed) so every card and sheet can be looked at.
 */
import type { Emulator, Job, LibraryInfo, Settings, State } from "../../src/api";

export const toaster = {
  toast: (data: { title?: string; body?: string }) => {
    // eslint-disable-next-line no-console
    console.log("[toast]", data.title, data.body);
    return { dismiss: () => undefined };
  },
};
export const routerHook = { addRoute: () => undefined, removeRoute: () => undefined };
export const definePlugin = (fn: any) => fn;
export const addEventListener = () => () => undefined;
export const removeEventListener = () => undefined;

type Seed = Partial<Emulator> & Pick<Emulator, "id" | "name" | "consoles" | "method" | "source">;

const base = (seed: Seed): Emulator => ({
  blurb: "",
  installed: null,
  latest: null,
  latest_error: null,
  update: false,
  unknown_version: false,
  preset: { state: "none", summary: null, backup: false },
  shortcut: null,
  job: null,
  ...seed,
});

const flat = (app_id: string, version: string, installation = "user") => ({
  method: "flatpak" as const, version, path: null, app_id, installation, managed: true,
});
const app = (file: string, version: string | null, managed = true) => ({
  method: "appimage" as const, version, path: `/home/deck/Applications/${file}`, app_id: null, installation: null, managed,
});

const EMULATORS: Emulator[] = [
  base({ id: "retroarch", name: "RetroArch", consoles: ["NES", "Super Nintendo", "Nintendo 64", "Game Boy Advance", "Genesis / Mega Drive"],
    method: "flatpak", source: "flathub", blurb: "One front end for most retro systems, through its cores.",
    installed: flat("org.libretro.RetroArch", "1.22.1", "system"), latest: "1.22.2", update: true,
    preset: { state: "applied", summary: "Fullscreen, library as the start folder, BIOS folder, menu on L3+R3, quit on Start+Select.", backup: true }, shortcut: 3000000001 }),
  base({ id: "dolphin", name: "Dolphin", consoles: ["GameCube", "Wii"], method: "flatpak", source: "flathub", blurb: "GameCube and Wii.",
    installed: flat("org.DolphinEmu.dolphin-emu", "2609b"), latest: "2609b",
    preset: { state: "applied", summary: "Fullscreen, GameCube and Wii folders, 2x resolution, no stop prompt, no analytics question.", backup: true }, shortcut: 3000000002 }),
  base({ id: "pcsx2", name: "PCSX2", consoles: ["PlayStation 2"], method: "appimage", source: "github", blurb: "PlayStation 2.",
    installed: app("pcsx2-Qt.AppImage", null, false), latest: "2.8.2", unknown_version: true,
    preset: { state: "partial", summary: "Fullscreen, PS2 folder and BIOS, 2x resolution, pad 1 on the Deck's controls, Select+R3 pause menu, Select+Start quit.", backup: false } }),
  base({ id: "duckstation", name: "DuckStation", consoles: ["PlayStation"], method: "appimage", source: "github", blurb: "PlayStation.",
    installed: app("DuckStation.AppImage", "build 2026-10-02"), latest: "build 2026-11-07", update: true,
    preset: { state: "applied", summary: "Fullscreen, PlayStation folder and BIOS, 3x resolution, pad 1 on the Deck's controls.", backup: true } }),
  base({ id: "ppsspp", name: "PPSSPP", consoles: ["PSP"], method: "appimage", source: "github", blurb: "PlayStation Portable.", latest: "1.20.4",
    job: { emu_id: "ppsspp", action: "install", state: "running", progress: 0.42, received: 21_000_000, total: 50_689_748, message: "Downloading", error: null, version: "1.20.4" },
    preset: { state: "ready", summary: "Fullscreen, opens in the PSP folder, 2x resolution, no first-run screen.", backup: false } }),
  base({ id: "cemu", name: "Cemu", consoles: ["Wii U"], method: "appimage", source: "github", blurb: "Wii U.", latest: "2.6",
    preset: { state: "ready", summary: "Fullscreen, Wii U folder in the game list, no update check on start.", backup: false } }),
  base({ id: "rpcs3", name: "RPCS3", consoles: ["PlayStation 3"], method: "appimage", source: "github", blurb: "PlayStation 3. Needs the PS3 system software, installed from inside RPCS3.", latest: "0.0.43-20623",
    preset: { state: "ready", summary: "Games start in fullscreen, RPCS3 closes with the game.", backup: false } }),
  base({ id: "azahar", name: "Azahar", consoles: ["Nintendo 3DS"], method: "appimage", source: "github", blurb: "Nintendo 3DS (the successor of Citra and Lime3DS).",
    installed: app("azahar.AppImage", "2126.2"), latest: "2126.2",
    preset: { state: "applied", summary: "Fullscreen, no close prompt, 3DS folder in the game list.", backup: true }, shortcut: 3000000003 }),
  base({ id: "melonds", name: "melonDS", consoles: ["Nintendo DS"], method: "appimage", source: "github", blurb: "Nintendo DS.", latest: "1.1" }),
  base({ id: "ryubing", name: "Ryubing", consoles: ["Switch"], method: "appimage", source: "forgejo", blurb: "Nintendo Switch (the maintained Ryujinx). Needs your own keys and firmware.",
    installed: app("Ryujinx.AppImage", "1.3.3"), latest: "1.3.3",
    preset: { state: "waiting", summary: "Fullscreen, Switch folder in the game list, no exit prompt, no update check, docked mode.", backup: false } }),
  base({ id: "eden", name: "Eden", consoles: ["Switch"], method: "appimage", source: "forgejo", blurb: "Nintendo Switch (from the yuzu family). Needs your own keys and firmware.", latest: "0.2.1" }),
  base({ id: "xemu", name: "xemu", consoles: ["Xbox"], method: "appimage", source: "github", blurb: "Original Xbox.", latest: "0.8.139" }),
  base({ id: "vita3k", name: "Vita3K", consoles: ["PS Vita"], method: "appimage", source: "github", blurb: "PlayStation Vita.", latest: "build 2026-11-17" }),
  base({ id: "shadps4", name: "shadPS4", consoles: ["PlayStation 4"], method: "flatpak", source: "flathub", blurb: "PlayStation 4 (early; few games run well).", latest: "0.20.0" }),
  base({ id: "flycast", name: "Flycast", consoles: ["Dreamcast"], method: "appimage", source: "github", blurb: "Dreamcast, NAOMI and Atomiswave.", latest: "2.7",
    job: { emu_id: "flycast", action: "install", state: "error", progress: 0, received: 0, total: 0, message: "Failed", error: "no connection (timed out)", version: "2.7" } }),
  base({ id: "primehack", name: "PrimeHack", consoles: ["GameCube", "Wii"], method: "flatpak", source: "flathub", blurb: "Dolphin fork for the Metroid Prime Trilogy.", latest: "1.0.9" }),
  base({ id: "scummvm", name: "ScummVM", consoles: ["ScummVM"], method: "flatpak", source: "flathub", blurb: "Classic point-and-click adventures.", latest: "2026.4.0" }),
  base({ id: "mame", name: "MAME", consoles: ["Arcade (MAME)"], method: "flatpak", source: "flathub", blurb: "Arcade machines (standalone MAME).", latest: "0.289" }),
];

let checkedAt = Date.now() / 1000 - 3 * 3600;
let settings: Settings = { library_root: "", auto_presets: true, add_to_steam: true, check_updates: true, check_hours: 6, github_token_set: false };

const state = (): State => {
  // Running jobs move on each time the UI asks.
  for (const emu of EMULATORS) {
    const job = emu.job;
    if (job && job.state === "running" && !(window as any).__FREEZE) {
      job.progress = Math.min(1, job.progress + 0.15);
      job.received = Math.round(job.total * job.progress);
      if (job.progress >= 1) finish(emu, job);
    } else if (job && job.state === "queued") job.state = "running";
  }
  return {
    emulators: EMULATORS.map((emu) => ({ ...emu, job: emu.job ? { ...emu.job } : null })),
    updates: EMULATORS.filter((emu) => emu.update).length,
    checked_at: checkedAt,
    checking: false,
    check_error: null,
    busy: EMULATORS.some((emu) => emu.job && (emu.job.state === "running" || emu.job.state === "queued")),
    flatpak: true,
    library: { root: "/home/deck/Emulation", ready: true },
  };
};

function finish(emu: Emulator, job: Job) {
  job.state = "done";
  job.message = job.action === "uninstall" ? "Removed" : "Installed";
  if (job.action === "uninstall") {
    emu.installed = null;
    emu.shortcut = null;
  } else {
    emu.installed = emu.method === "flatpak" ? flat(`org.example.${emu.id}`, emu.latest ?? "1.0") : app(`${emu.name}.AppImage`, emu.latest);
    emu.update = false;
    emu.unknown_version = false;
  }
  window.setTimeout(() => { emu.job = null; }, 1500);
}

const start = (id: string, action: Job["action"]) => {
  const emu = EMULATORS.find((item) => item.id === id)!;
  emu.job = { emu_id: id, action, state: "queued", progress: 0, received: 0, total: 60_000_000, message: action === "uninstall" ? "Removing" : "Downloading", error: null, version: emu.latest };
  return { ok: true, state: state() };
};

const library = (): LibraryInfo => ({
  root: settings.library_root || "/home/deck/Emulation",
  exists: true,
  roms: `${settings.library_root || "/home/deck/Emulation"}/roms`,
  bios: `${settings.library_root || "/home/deck/Emulation"}/bios`,
  ready: true,
  automatic: !settings.library_root,
  consoles: [{ key: "psx", label: "PlayStation", folder: "psx", exists: true, files: 12 }, { key: "ps2", label: "PlayStation 2", folder: "ps2", exists: true, files: 4 }],
  candidates: [
    { path: "/home/deck/Emulation", kind: "emudeck", where: "internal" },
    { path: "/run/media/deck/SD/Emulation", kind: "emudeck", where: "sd" },
    { path: "/home/deck/EmuDecky", kind: "emudecky", where: "internal" },
  ],
  bios_status: [
    { console: "psx", label: "PlayStation BIOS", files: ["scph5501.bin", "scph5500.bin", "scph5502.bin"], hint: null, optional: false, found: "/home/deck/Emulation/bios/scph5501.bin", folder: "/home/deck/Emulation/bios" },
    { console: "ps2", label: "PlayStation 2 BIOS", files: [], hint: "any PS2 BIOS dump (.bin) for PCSX2", optional: false, found: null, folder: "/home/deck/Emulation/bios" },
    { console: "ps3", label: "PS3 system software", files: [], hint: "install PS3UPDAT.PUP from inside RPCS3 (File → Install Firmware)", optional: false, found: null, folder: null },
    { console: "switch", label: "Switch keys", files: [], hint: "prod.keys from your own Switch, then firmware from inside Ryubing or Eden", optional: false, found: null, folder: null },
    { console: "dreamcast", label: "Dreamcast BIOS", files: ["dc/dc_boot.bin", "dc_boot.bin"], hint: "Flycast runs most games without it", optional: true, found: null, folder: "/home/deck/Emulation/bios" },
    { console: "nds", label: "DS BIOS and firmware", files: ["bios7.bin", "bios9.bin", "firmware.bin"], hint: "melonDS runs most games without them", optional: true, found: null, folder: "/home/deck/Emulation/bios" },
  ],
});

const delay = <T,>(value: T, ms = 120): Promise<T> => new Promise((resolve) => window.setTimeout(() => resolve(value), ms));

const handlers: Record<string, (...args: any[]) => any> = {
  get_state: () => state(),
  check_updates: () => { checkedAt = Date.now() / 1000; return delay(state(), 600); },
  install: (id: string) => start(id, "install"),
  update: (id: string) => start(id, "update"),
  uninstall: (id: string) => start(id, "uninstall"),
  update_all: () => {
    const queued = EMULATORS.filter((emu) => emu.update).map((emu) => emu.id);
    queued.forEach((id) => start(id, "update"));
    return { ok: true, queued, state: state() };
  },
  cancel: (id: string) => {
    const emu = EMULATORS.find((item) => item.id === id)!;
    if (emu.job) emu.job = { ...emu.job, state: "cancelled", error: "Cancelled" };
    return { ok: true, state: state() };
  },
  apply_preset: (id: string) => {
    const emu = EMULATORS.find((item) => item.id === id)!;
    if (emu.preset.state === "waiting")
      return { ok: false, state: "waiting", error: "Start the emulator once, then apply the Deck settings (it writes its config on first start).", state_all: state() };
    emu.preset = { ...emu.preset, state: "applied", backup: true };
    return { ok: true, state: "applied", state_all: state() };
  },
  restore_config: (id: string) => {
    const emu = EMULATORS.find((item) => item.id === id)!;
    emu.preset = { ...emu.preset, state: "partial", backup: false };
    return { ok: true, state_all: state() };
  },
  shortcut_plan: (id: string) => {
    const emu = EMULATORS.find((item) => item.id === id)!;
    return {
      plan: emu.installed ? { emu_id: id, name: emu.name, exe: emu.installed.path ? `"${emu.installed.path}"` : '"/usr/bin/flatpak"', startDir: '"/home/deck/Applications"', launchOptions: emu.installed.app_id ? `run ${emu.installed.app_id}` : "", key: emu.installed.path ?? emu.installed.app_id } : null,
      appid: emu.shortcut, made: true, enabled: settings.add_to_steam,
    };
  },
  report_shortcut: (id: string, appid: number | null) => {
    EMULATORS.find((item) => item.id === id)!.shortcut = appid;
    return { ok: true };
  },
  get_library: () => delay(library()),
  set_library_root: (path: string) => { settings = { ...settings, library_root: path }; return library(); },
  create_folders: () => ({ ok: true, made: 0, errors: [], library: library() }),
  get_settings: () => delay(settings),
  set_settings: (changes: Partial<Settings> & { github_token?: string }) => {
    const { github_token, ...rest } = changes;
    settings = { ...settings, ...rest, github_token_set: github_token !== undefined ? Boolean(github_token) : settings.github_token_set };
    return settings;
  },
};

export const callable =
  <Args extends any[] = [], Return = void>(route: string) =>
  async (...args: Args): Promise<Return> => {
    // ?down: a backend that never loaded (every call fails), see BackendError.
    if (typeof location !== "undefined" && new URLSearchParams(location.search).has("down")) {
      throw new Error("Plugin Emu-Hub is not loaded");
    }
    const handler = handlers[route];
    if (!handler) throw new Error(`No mock for ${route}`);
    return (await handler(...args)) as Return;
  };
