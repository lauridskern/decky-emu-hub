import { useCallback, useEffect, useRef, useState, useSyncExternalStore } from "react";
import { Focusable, focusRingClasses, GamepadEvent } from "@decky/ui";
import { FaGamepad } from "react-icons/fa";

import { refresh, snapshot, subscribe } from "../state";
import { childFocus, focusElement, PAD } from "./gamepad";
import { useBackGuard } from "./useBackGuard";
import { ago, Glyph, Spinner, Styles } from "./ui";
import EmulatorsView from "./EmulatorsView";
import UpdatesView from "./UpdatesView";
import LibraryView from "./LibraryView";
import SettingsView from "./SettingsView";
import ActionsSheet from "./ActionsSheet";

type Tab = "emulators" | "updates" | "library" | "settings";
const TABS: { key: Tab; label: string }[] = [
  { key: "emulators", label: "Emulators" },
  { key: "updates", label: "Updates" },
  { key: "library", label: "Library & BIOS" },
  { key: "settings", label: "Settings" },
];

/** The first thing to focus in each tab. */
const FIRST: Record<Tab, string> = {
  emulators: ".ed-emu",
  updates: ".ed-view .ed-f",
  library: ".ed-view .ed-f",
  settings: ".ed-view .ed-f",
};

/**
 * The full-screen page: top bar with tabs (L1/R1), one view at a time, and
 * the actions sheet over it. B closes the sheet, then goes back to the
 * Emulators tab, then leaves the page.
 */
export default function App() {
  const state = useSyncExternalStore(subscribe, snapshot, snapshot);
  const [tab, setTab] = useState<Tab>("emulators");
  const [sheet, setSheet] = useState<string | null>(null);
  const rootRef = useRef<HTMLDivElement>(null);
  const opener = useRef<string | null>(null);

  useEffect(() => {
    refresh().catch(() => undefined);
  }, []);

  // Steam's focus ring would sit on top of ours (see ROM-Store's Store.tsx):
  // hidden while focus is inside the page.
  useEffect(() => {
    const ring = (focusRingClasses as Record<string, string> | undefined)?.FocusRing;
    if (!ring || typeof document === "undefined") return;
    const root = document.documentElement;
    const style = document.createElement("style");
    style.textContent = `html.ed-no-ring .${CSS.escape(ring)} { opacity: 0 !important; }`;
    document.head.appendChild(style);
    const update = (event: FocusEvent) =>
      root.classList.toggle("ed-no-ring", Boolean(rootRef.current?.contains(event.target as Node)));
    document.addEventListener("focusin", update);
    return () => {
      document.removeEventListener("focusin", update);
      root.classList.remove("ed-no-ring");
      style.remove();
    };
  }, []);

  // Library and Settings load their data after they mount, so this keeps
  // looking for a few frames (about half a second), and gives up as soon as
  // focus has moved somewhere inside the page by other means.
  const focusFirst = useCallback((which: Tab) => {
    let frames = 0;
    const attempt = () => {
      const root = rootRef.current;
      if (!root) return;
      const active = document.activeElement;
      const settled = active && active !== document.body && root.contains(active) && !active.closest(".ed-top");
      if (frames > 1 && settled) return;
      if (frames > 0 && focusElement(root.querySelector(FIRST[which]))) return;
      if (frames++ < 40) window.requestAnimationFrame(attempt);
    };
    window.requestAnimationFrame(attempt);
  }, []);

  // The page opens on the first emulator once the list is there.
  const opened = useRef(false);
  useEffect(() => {
    if (opened.current || !state) return;
    opened.current = true;
    const active = document.activeElement;
    if (!active || active === document.body || !rootRef.current?.contains(active)) focusFirst("emulators");
  }, [state, focusFirst]);

  const selectTab = useCallback(
    (next: Tab) => {
      setTab(next);
      focusFirst(next);
    },
    [focusFirst],
  );

  const stepTab = (step: number) => {
    const index = TABS.findIndex((item) => item.key === tab);
    const next = TABS[(index + step + TABS.length) % TABS.length].key;
    selectTab(next);
  };

  const openSheet = useCallback((id: string) => {
    opener.current = id;
    setSheet(id);
  }, []);

  const closeSheet = useCallback(() => {
    setSheet(null);
    const id = opener.current;
    window.requestAnimationFrame(() => {
      const root = rootRef.current;
      if (!root) return;
      focusElement(root.querySelector(`[data-emu="${id}"]`) ?? root.querySelector(FIRST.emulators));
    });
  }, []);

  useBackGuard(tab !== "emulators", () => selectTab("emulators"));
  useBackGuard(sheet !== null, closeSheet);

  const onShellButton = (event: GamepadEvent) => {
    const button = event.detail.button;
    if (button === PAD.BUMPER_LEFT) stepTab(-1);
    else if (button === PAD.BUMPER_RIGHT) stepTab(1);
  };

  const emu = sheet ? state?.emulators.find((item) => item.id === sheet) ?? null : null;
  const running = state?.emulators.filter((item) => item.job && (item.job.state === "queued" || item.job.state === "running")) ?? [];

  return (
    <div className="ed-app" ref={rootRef}>
      <Styles />
      <Focusable noFocusRing className="ed-body" flow-children="column" {...childFocus(!sheet)} onButtonDown={onShellButton}>
        <Focusable noFocusRing className="ed-top" flow-children="row">
          <div className="ed-brand">
            <span className="ed-brand-mark">
              <FaGamepad />
            </span>
            Emu Hub
          </div>
          <Focusable noFocusRing className="ed-tabs" flow-children="row">
            <Glyph>L1</Glyph>
            {TABS.map((item) => (
              <Focusable
                noFocusRing
                key={item.key}
                className={`ed-tab ed-f${tab === item.key ? " active" : ""}`}
                data-tab={item.key}
                focusClassName="is-focus"
                onActivate={() => selectTab(item.key)}
                onClick={() => selectTab(item.key)}
                onOKActionDescription={`Open ${item.label}`}
              >
                {item.label}
                {item.key === "updates" && state && state.updates > 0 ? <span className="ed-tab-badge">{state.updates}</span> : null}
              </Focusable>
            ))}
            <Glyph>R1</Glyph>
          </Focusable>
          <div className="ed-top-status">
            {running.length ? (
              <>
                <Spinner />
                {running.length === 1 ? running[0].name : `${running.length} jobs`}
              </>
            ) : state?.checking ? (
              <>
                <Spinner /> Checking for updates
              </>
            ) : state ? (
              `Checked ${ago(state.checked_at)}`
            ) : null}
          </div>
        </Focusable>

        {tab === "emulators" && <EmulatorsView state={state} onMore={openSheet} />}
        {tab === "updates" && <UpdatesView state={state} onMore={openSheet} />}
        {tab === "library" && <LibraryView />}
        {tab === "settings" && <SettingsView />}
      </Focusable>
      {emu ? <ActionsSheet emu={emu} /> : null}
    </div>
  );
}
