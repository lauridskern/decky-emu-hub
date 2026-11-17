import { FC, ReactNode, useEffect, useRef, useState } from "react";
import { Focusable } from "@decky/ui";
import {
  FaBroom,
  FaDownload,
  FaPlay,
  FaSlidersH,
  FaSteam,
  FaStop,
  FaSyncAlt,
  FaTrashAlt,
  FaUndo,
} from "react-icons/fa";

import { Emulator, isActive, PresetState } from "../api";
import * as actions from "../actions";
import { focusElement } from "./gamepad";
import { EmuIcon, Progress, statusLine, tilde } from "./ui";

const PRESET_HINT: Record<PresetState, string> = {
  none: "",
  applied: "In place. A again re-applies it.",
  partial: "Some of its settings differ (changed in the emulator, or never applied).",
  ready: "Not applied yet.",
  waiting: "Start the emulator once first; Emu Hub applies it after that.",
};

interface Item {
  key: string;
  label: string;
  hint?: string;
  icon: ReactNode;
  tone?: "primary" | "danger";
  run: () => Promise<{ ok: boolean; text: string } | string | null | void>;
}

/**
 * Everything one emulator can do, over the page (X on a card). Focus stays
 * inside it (the page behind has child focus off); B closes it through the
 * page's history guard (App.tsx) and focus goes back to the card.
 */
const ActionsSheet: FC<{ emu: Emulator }> = ({ emu }) => {
  const [message, setMessage] = useState<{ ok: boolean; text: string } | null>(null);
  const [confirm, setConfirm] = useState(false);
  const [working, setWorking] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    window.requestAnimationFrame(() => focusElement(ref.current?.querySelector(".ed-menu-item")));
  }, [confirm]);

  const run = (item: Item) => {
    if (working) return;
    setWorking(true);
    item
      .run()
      .then((result) => {
        if (typeof result === "string") setMessage({ ok: false, text: result });
        else if (result) setMessage(result);
      })
      .catch((error) => setMessage({ ok: false, text: String(error) }))
      .finally(() => setWorking(false));
  };

  const active = isActive(emu.job);
  const primary = actions.primaryOf(emu);
  const items: Item[] = [];

  if (confirm) {
    items.push({ key: "keep", label: "Keep it", icon: <FaUndo />, run: async () => setConfirm(false) });
    items.push({
      key: "really",
      label: `Uninstall ${emu.name}`,
      hint: "Its settings, saves and your games stay.",
      icon: <FaTrashAlt />,
      tone: "danger",
      run: async () => {
        setConfirm(false);
        return actions.uninstall(emu);
      },
    });
  } else {
    if (active) {
      items.push({ key: "cancel", label: "Cancel", hint: emu.job?.message, icon: <FaStop />, tone: "primary", run: () => actions.cancel(emu) });
    } else if (primary === "install") {
      items.push({
        key: "install",
        label: "Install",
        hint: emu.method === "flatpak" ? "From Flathub" : emu.latest ? `${emu.latest}, from the project's releases` : undefined,
        icon: <FaDownload />,
        tone: "primary",
        run: () => actions.install(emu),
      });
    } else if (primary === "update") {
      items.push({ key: "update", label: `Update to ${emu.latest ?? "the newest version"}`, icon: <FaSyncAlt />, tone: "primary", run: () => actions.update(emu) });
    }
    if (emu.installed && !active) {
      items.push({ key: "launch", label: "Launch", hint: "Through its Steam shortcut", icon: <FaPlay />, tone: primary === "launch" ? "primary" : undefined, run: () => actions.start(emu) });
    }
    if (emu.installed && emu.unknown_version && !active && emu.latest) {
      items.push({
        key: "replace",
        label: `Replace with ${emu.latest}`,
        hint: "Its version is unknown (installed by EmuDeck or by hand). The file is replaced where it is.",
        icon: <FaSyncAlt />,
        run: () => actions.update(emu),
      });
    }
    if (emu.installed && emu.preset.state !== "none") {
      items.push({
        key: "preset",
        label: "Apply Deck settings",
        hint: PRESET_HINT[emu.preset.state],
        icon: <FaSlidersH />,
        run: () => actions.applyPreset(emu),
      });
    }
    if (emu.preset.backup) {
      items.push({ key: "restore", label: "Restore my config", hint: "Puts back the files from before the Deck settings.", icon: <FaBroom />, run: () => actions.restoreConfig(emu) });
    }
    if (emu.installed) {
      items.push(
        emu.shortcut
          ? { key: "steam", label: "Remove from Steam", icon: <FaSteam />, run: () => actions.removeFromSteam(emu) }
          : { key: "steam", label: "Add to Steam", hint: "So it can be started from the library", icon: <FaSteam />, run: () => actions.addToSteam(emu) },
      );
    }
    if (emu.installed && !active) {
      items.push({ key: "uninstall", label: "Uninstall", icon: <FaTrashAlt />, tone: "danger", run: async () => setConfirm(true) });
    }
  }

  const where = emu.installed
    ? emu.installed.method === "flatpak"
      ? `Flathub · ${emu.installed.app_id} (${emu.installed.installation ?? "user"})`
      : tilde(emu.installed.path)
    : emu.method === "flatpak"
      ? "Flathub"
      : "AppImage in ~/Applications";

  return (
    <div className="ed-scrim">
      <Focusable
        noFocusRing
        className="ed-sheet"
        flow-children="column"
        ref={ref}
        onCancelActionDescription="Close"
      >
        <div className="ed-sheet-head">
          <EmuIcon emu={emu} />
          <div>
            <div className="ed-sheet-title">{emu.name}</div>
            <div className="ed-muted">{emu.consoles.join(" · ")}</div>
          </div>
        </div>
        <div className="ed-note">{emu.blurb}</div>
        <dl className="ed-facts">
          <dt>Status</dt>
          <dd>{statusLine(emu)}</dd>
          <dt>Installed as</dt>
          <dd className={emu.installed?.method === "appimage" ? "ed-path" : undefined}>{where}</dd>
          {emu.latest ? (
            <>
              <dt>Newest</dt>
              <dd>{emu.latest}</dd>
            </>
          ) : null}
          {emu.latest_error ? (
            <>
              <dt>Update check</dt>
              <dd className="ed-warn">{emu.latest_error}</dd>
            </>
          ) : null}
          {emu.preset.summary ? (
            <>
              <dt>Deck settings</dt>
              <dd>{emu.preset.summary}</dd>
            </>
          ) : null}
        </dl>
        {active ? <Progress value={emu.job!.progress} /> : null}
        {message ? <div className={`ed-sheet-msg ${message.ok ? "good" : "bad"}`}>{message.text}</div> : null}
        <Focusable noFocusRing className="ed-menu" flow-children="column">
          {items.map((item) => (
            <Focusable
              noFocusRing
              key={item.key}
              className={`ed-menu-item ed-f${item.tone ? ` ${item.tone}` : ""}`}
              focusClassName="is-focus"
              onActivate={() => run(item)}
              onClick={() => run(item)}
              onOKActionDescription={item.label}
            >
              {item.icon}
              <span className="ed-menu-text">
                <span className="ed-menu-label">{item.label}</span>
                {item.hint ? <span className="ed-menu-hint">{item.hint}</span> : null}
              </span>
            </Focusable>
          ))}
        </Focusable>
      </Focusable>
    </div>
  );
};

export default ActionsSheet;
