import { FC, ReactNode } from "react";
import { CSS } from "../styles";
import { Emulator } from "../api";

/** Small visual pieces. None takes focus; the Focusable around them does. */

export const Styles: FC = () => <style id="emu-hub-styles" dangerouslySetInnerHTML={{ __html: CSS }} />;

export const Glyph: FC<{ children: ReactNode; round?: boolean }> = ({ children, round }) => (
  <span className={`ed-glyph${round ? " round" : ""}`} aria-hidden="true">
    {children}
  </span>
);

export const Switch: FC<{ on: boolean }> = ({ on }) => (
  <span className={`ed-switch${on ? " on" : ""}`} aria-hidden="true">
    <span />
  </span>
);

export const Spinner: FC = () => <span className="ed-spinner" />;

export const Progress: FC<{ value: number }> = ({ value }) => (
  <div className="ed-progress">
    <div style={{ width: `${Math.round(Math.min(1, Math.max(0, value)) * 1000) / 10}%` }} />
  </div>
);

/** A colour per emulator, for its icon tile. */
const TINTS: Record<string, string> = {
  retroarch: "#5b5fc7", dolphin: "#3d8bd9", pcsx2: "#3567c9", duckstation: "#c79a2a", ppsspp: "#2f9fb8",
  cemu: "#3aa3c2", rpcs3: "#8c3fd0", azahar: "#c74a3a", melonds: "#c45a8a", ryubing: "#d2453c",
  xemu: "#3e9b4f", vita3k: "#2b7ad6", shadps4: "#5b6ad6", flycast: "#d9822b", primehack: "#d06a2a",
  scummvm: "#46a36a", mame: "#8a8f99",
};

export const EmuIcon: FC<{ emu: Pick<Emulator, "id" | "name"> }> = ({ emu }) => {
  const letters = emu.name.replace(/[^A-Za-z0-9]/g, "").slice(0, 2);
  return (
    <span className="ed-emu-icon" style={{ ["--ed-tint" as any]: TINTS[emu.id] ?? "#3a4352" }} aria-hidden="true">
      {letters.charAt(0).toUpperCase() + letters.charAt(1).toLowerCase()}
    </span>
  );
};

/** /home/deck/... -> ~/... (shorter, and it is what the player knows). */
export const tilde = (path: string | null | undefined): string => (path ?? "").replace(/^\/home\/[^/]+(?=\/|$)/, "~");

export function bytes(n: number): string {
  if (!n) return "";
  if (n >= 1 << 30) return `${(n / (1 << 30)).toFixed(1)} GB`;
  return `${Math.max(1, Math.round(n / (1 << 20)))} MB`;
}

export function ago(seconds: number): string {
  if (!seconds) return "never";
  const diff = Math.max(0, Date.now() / 1000 - seconds);
  if (diff < 90) return "just now";
  if (diff < 3600) return `${Math.round(diff / 60)} min ago`;
  if (diff < 86400) return `${Math.round(diff / 3600)} h ago`;
  return `${Math.round(diff / 86400)} d ago`;
}

/** One line for a card: what is installed and what happens next. */
export function statusLine(emu: Emulator): string {
  const job = emu.job;
  if (job && (job.state === "queued" || job.state === "running")) {
    const verb = { install: "Installing", update: "Updating", uninstall: "Removing" }[job.action];
    if (job.state === "queued") return `${verb}: waiting`;
    const size = job.total ? ` · ${bytes(job.received)} of ${bytes(job.total)}` : "";
    return `${job.message} ${Math.round(job.progress * 100)}%${size}`;
  }
  if (job?.state === "error") return `Failed: ${job.error}`;
  if (!emu.installed) return emu.latest ? `Not installed · ${emu.latest} available` : "Not installed";
  const version = emu.installed.version ?? "version unknown";
  const where = emu.installed.method === "flatpak" ? "Flathub" : "AppImage";
  if (emu.update) return `${version} → ${emu.latest} · ${where}`;
  return `${version} · ${where}`;
}

/** The chip on the right of a card. */
export function chip(emu: Emulator): { text: string; tone: "" | "update" | "ok" | "warn" | "bad" } {
  const job = emu.job;
  if (job && (job.state === "queued" || job.state === "running"))
    return { text: job.state === "queued" ? "Queued" : `${Math.round(job.progress * 100)}%`, tone: "update" };
  if (job?.state === "error") return { text: "Failed", tone: "bad" };
  if (!emu.installed) return { text: "Get", tone: "" };
  if (emu.update) return { text: "Update", tone: "update" };
  if (emu.unknown_version) return { text: "Installed", tone: "warn" };
  return { text: "Installed", tone: "ok" };
}
