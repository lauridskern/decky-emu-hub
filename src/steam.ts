/**
 * Emulators in the Steam library, so they start from Game Mode.
 *
 * Uses the client's own API (SteamClient.Apps), as ROM-Store does. Each
 * emulator gets one non-Steam shortcut: the AppImage itself, or
 * `flatpak run <id>` for a Flathub app. A shortcut that already starts the
 * same file or app is adopted instead of doubled. Only shortcuts EmuDecky made
 * are removed when the emulator is uninstalled.
 */
import { reportShortcut, shortcutPlan, ShortcutPlan } from "./api";

/** Steam's app type for non-Steam shortcuts. */
const SHORTCUT_TYPE = 1073741824;

const steam = (): any => (globalThis as any).SteamClient;
const store = (name: string): any => (globalThis as any)[name];

/** One change at a time, so two events never add the same emulator twice. */
let queue: Promise<unknown> = Promise.resolve();
function serial<T>(work: () => Promise<T>): Promise<T> {
  const next = queue.then(work);
  queue = next.catch(() => undefined);
  return next;
}

export function exists(appid: number | null | undefined): boolean {
  if (!appid) return false;
  try {
    return Boolean(store("appStore")?.GetAppOverviewByAppID(appid));
  } catch {
    return false;
  }
}

async function findByCommand(key: string): Promise<number | null> {
  const apps: any[] = (store("appStore")?.allApps ?? []).filter((app: any) => app?.app_type === SHORTCUT_TYPE);
  for (const app of apps) {
    let details = store("appDetailsStore")?.GetAppDetails?.(app.appid);
    if (!details) {
      try {
        details = await store("appDetailsStore")?.RequestAppDetails?.(app.appid);
      } catch {
        details = null;
      }
    }
    const command = `${details?.strShortcutExe ?? ""} ${details?.strShortcutLaunchOptions ?? ""}`;
    if (command.includes(key)) return app.appid;
  }
  return null;
}

async function add(plan: ShortcutPlan): Promise<number | null> {
  const apps = steam()?.Apps;
  if (!apps?.AddShortcut) return null;
  const appid: number = await apps.AddShortcut(plan.name, plan.exe, plan.startDir, plan.launchOptions);
  if (!appid) return null;
  // AddShortcut names the shortcut after the executable on some builds.
  apps.SetShortcutName?.(appid, plan.name);
  apps.SetShortcutExe?.(appid, plan.exe);
  apps.SetShortcutStartDir?.(appid, plan.startDir);
  apps.SetShortcutLaunchOptions?.(appid, plan.launchOptions);
  return appid;
}

export interface ShortcutResult {
  ok: boolean;
  appid?: number;
  adopted?: boolean;
  error?: string;
}

/** The emulator's shortcut: the tracked one, an adopted one, or a new one. */
export function ensureShortcut(emuId: string): Promise<ShortcutResult> {
  return serial(async () => {
    if (!steam()?.Apps) return { ok: false, error: "Not running inside Steam" };
    const info = await shortcutPlan(emuId);
    if (info.appid && exists(info.appid)) return { ok: true, appid: info.appid };
    if (!info.plan) return { ok: false, error: "It is not installed." };
    const adopted = await findByCommand(info.plan.key);
    if (adopted) {
      await reportShortcut(emuId, adopted, false);
      return { ok: true, appid: adopted, adopted: true };
    }
    const appid = await add(info.plan);
    if (!appid) return { ok: false, error: "Steam did not add the shortcut." };
    await reportShortcut(emuId, appid, true);
    return { ok: true, appid };
  });
}

/** Removes the shortcut if EmuDecky made it; forgets an adopted one. */
export function removeShortcut(emuId: string): Promise<ShortcutResult> {
  return serial(async () => {
    const info = await shortcutPlan(emuId);
    if (!info.appid) return { ok: true };
    try {
      if (info.made && exists(info.appid)) steam()?.Apps?.RemoveShortcut?.(info.appid);
    } catch (error) {
      return { ok: false, error: String(error) };
    }
    await reportShortcut(emuId, null, false);
    return { ok: true };
  });
}

/** Steam's 64-bit id of a shortcut: the app id in the high half, 0x02000000 in the low. */
function gameId(appid: number): string {
  const overview = store("appStore")?.GetAppOverviewByAppID(appid);
  if (overview?.m_gameid) return String(overview.m_gameid);
  return ((BigInt(appid) << BigInt(32)) | BigInt(0x02000000)).toString();
}

/** Start the emulator through its Steam shortcut (made first if needed). */
export async function launch(emuId: string): Promise<ShortcutResult> {
  if (!steam()?.Apps?.RunGame) return { ok: false, error: "Not running inside Steam" };
  const shortcut = await ensureShortcut(emuId);
  if (!shortcut.ok || !shortcut.appid) return shortcut;
  steam().Apps.RunGame(gameId(shortcut.appid), "", -1, 100);
  return shortcut;
}
