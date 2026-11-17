/**
 * What the buttons do. Each action calls the backend, takes the new state it
 * returns (which starts polling while a job runs) and gives back a line to
 * show, or null when there is nothing to say.
 */
import { toaster } from "@decky/api";
import * as api from "./api";
import { Emulator, isActive } from "./api";
import { setState, refresh } from "./state";
import { ensureShortcut, launch, removeShortcut } from "./steam";

export type Primary = "install" | "update" | "launch" | "busy";

export function primaryOf(emu: Emulator): Primary {
  if (isActive(emu.job)) return "busy";
  if (!emu.installed) return "install";
  if (emu.update) return "update";
  return "launch";
}

export const PRIMARY_LABEL: Record<Primary, string> = {
  install: "Install",
  update: "Update",
  launch: "Launch",
  busy: "Working…",
};

async function job(call: Promise<api.ActionResult>): Promise<string | null> {
  const result = await call;
  if (result.state) setState(result.state);
  return result.ok ? null : result.error ?? "That did not work.";
}

export function install(emu: Emulator): Promise<string | null> {
  return job(api.install(emu.id));
}

export function update(emu: Emulator): Promise<string | null> {
  return job(api.update(emu.id));
}

export function uninstall(emu: Emulator): Promise<string | null> {
  return job(api.uninstall(emu.id));
}

export function cancel(emu: Emulator): Promise<string | null> {
  return job(api.cancel(emu.id));
}

export async function start(emu: Emulator): Promise<string | null> {
  const result = await launch(emu.id);
  refresh().catch(() => undefined);
  return result.ok ? null : result.error ?? "It could not be started.";
}

export async function primary(emu: Emulator): Promise<string | null> {
  switch (primaryOf(emu)) {
    case "install":
      return install(emu);
    case "update":
      return update(emu);
    case "launch":
      return start(emu);
    default:
      return null;
  }
}

export async function applyPreset(emu: Emulator): Promise<{ ok: boolean; text: string }> {
  const result = await api.applyPreset(emu.id);
  if (result.state_all) setState(result.state_all);
  return result.ok
    ? { ok: true, text: "Deck settings applied." }
    : { ok: false, text: result.error ?? "The Deck settings could not be applied." };
}

export async function restoreConfig(emu: Emulator): Promise<{ ok: boolean; text: string }> {
  const result = await api.restoreConfig(emu.id);
  if (result.state_all) setState(result.state_all);
  return result.ok
    ? { ok: true, text: "Your previous config is back." }
    : { ok: false, text: result.error ?? "It could not be restored." };
}

export async function addToSteam(emu: Emulator): Promise<{ ok: boolean; text: string }> {
  const result = await ensureShortcut(emu.id);
  refresh().catch(() => undefined);
  if (!result.ok) return { ok: false, text: result.error ?? "It could not be added." };
  return { ok: true, text: result.adopted ? "It was already in your Steam library." : "Added to your Steam library." };
}

export async function removeFromSteam(emu: Emulator): Promise<{ ok: boolean; text: string }> {
  const result = await removeShortcut(emu.id);
  refresh().catch(() => undefined);
  return result.ok ? { ok: true, text: "Removed from your Steam library." } : { ok: false, text: result.error ?? "It could not be removed." };
}

/** Event from the backend: a job ended (works with the page closed). */
export async function onJobDone(event: {
  emu_id: string;
  name: string;
  action: "install" | "update" | "uninstall";
  state: string;
  error: string | null;
}): Promise<void> {
  refresh().catch(() => undefined);
  if (event.state === "cancelled") return;
  if (event.state !== "done") {
    toaster.toast({ title: `${event.name}: ${event.action} failed`, body: event.error ?? "See Emu Hub for details" });
    return;
  }
  if (event.action === "uninstall") {
    await removeShortcut(event.emu_id).catch(() => undefined);
    toaster.toast({ title: `${event.name} removed`, body: "Its settings and saves were kept." });
    return;
  }
  let body = event.action === "install" ? "Installed" : "Updated";
  try {
    const settings = await api.getSettings();
    if (settings.add_to_steam) {
      const shortcut = await ensureShortcut(event.emu_id);
      if (shortcut.ok && event.action === "install") body = "Installed and added to your Steam library";
    }
  } catch {
    /* the emulator is there; the shortcut can be added from its page */
  }
  toaster.toast({ title: event.name, body });
}
