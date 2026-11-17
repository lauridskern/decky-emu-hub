import { callable } from "@decky/api";

export type Method = "appimage" | "flatpak";
export type PresetState = "none" | "applied" | "partial" | "waiting" | "ready";

export interface Job {
  emu_id: string;
  action: "install" | "update" | "uninstall";
  state: "queued" | "running" | "done" | "error" | "cancelled";
  progress: number;
  received: number;
  total: number;
  message: string;
  error: string | null;
  version: string | null;
}

export interface Installed {
  method: Method;
  version: string | null;
  path: string | null;
  app_id: string | null;
  installation: string | null;
  managed: boolean;
}

export interface Emulator {
  id: string;
  name: string;
  blurb: string;
  consoles: string[];
  method: Method;
  source: "github" | "forgejo" | "flathub";
  installed: Installed | null;
  latest: string | null;
  latest_error: string | null;
  update: boolean;
  unknown_version: boolean;
  preset: { state: PresetState; summary: string | null; backup: boolean };
  shortcut: number | null;
  job: Job | null;
}

export interface State {
  emulators: Emulator[];
  updates: number;
  checked_at: number;
  checking: boolean;
  check_error: string | null;
  busy: boolean;
  flatpak: boolean;
  library: { root: string; ready: boolean };
}

export interface ActionResult {
  ok: boolean;
  error?: string;
  state?: State;
}

export interface PresetResult {
  ok: boolean;
  state?: PresetState;
  error?: string;
  files?: string[];
  state_all?: State;
}

export interface ShortcutPlan {
  emu_id: string;
  name: string;
  exe: string;
  startDir: string;
  launchOptions: string;
  key: string;
}

export interface ShortcutInfo {
  plan: ShortcutPlan | null;
  appid: number | null;
  made: boolean;
  enabled: boolean;
}

export interface BiosStatus {
  console: string;
  label: string;
  files: string[];
  hint: string | null;
  optional: boolean;
  found: string | null;
  folder: string | null;
}

export interface LibraryInfo {
  root: string;
  exists: boolean;
  roms: string;
  bios: string;
  ready: boolean;
  automatic: boolean;
  consoles: { key: string; label: string; folder: string; exists: boolean; files: number }[];
  candidates: { path: string; kind: "emudeck" | "emudecky"; where: "internal" | "sd" }[];
  bios_status: BiosStatus[];
}

export interface Settings {
  library_root: string;
  auto_presets: boolean;
  add_to_steam: boolean;
  check_updates: boolean;
  check_hours: number;
  github_token_set: boolean;
}

export const getState = callable<[], State>("get_state");
export const checkUpdates = callable<[force?: boolean], State>("check_updates");
export const install = callable<[id: string], ActionResult>("install");
export const update = callable<[id: string], ActionResult>("update");
export const updateAll = callable<[], ActionResult & { queued: string[] }>("update_all");
export const uninstall = callable<[id: string], ActionResult>("uninstall");
export const cancel = callable<[id: string], ActionResult>("cancel");
export const applyPreset = callable<[id: string], PresetResult>("apply_preset");
export const restoreConfig = callable<[id: string], PresetResult>("restore_config");
export const shortcutPlan = callable<[id: string], ShortcutInfo>("shortcut_plan");
export const reportShortcut = callable<[id: string, appid: number | null, made: boolean], { ok: boolean }>("report_shortcut");
export const getLibrary = callable<[], LibraryInfo>("get_library");
export const setLibraryRoot = callable<[path: string], LibraryInfo>("set_library_root");
export const createFolders = callable<[], { ok: boolean; made: number; errors: string[]; library: LibraryInfo }>("create_folders");
export const getSettings = callable<[], Settings>("get_settings");
export const setSettings = callable<[changes: Partial<Settings> & { github_token?: string }], Settings>("set_settings");

export const isActive = (job: Job | null | undefined): boolean => job?.state === "queued" || job?.state === "running";
