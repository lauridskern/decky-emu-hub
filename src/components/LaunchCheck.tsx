import { FC, useEffect, useState } from "react";
import { Button, Focusable } from "@decky/ui";
import { toaster } from "@decky/api";

import { LaunchCheck as Check, launchCheck, switchLaunchers } from "../api";
import { announceChoice } from "../choice";

const KIND: Record<string, string> = {
  emudeck: "EmuDeck's launcher",
  emuhub: "Emu Hub's launcher",
  other: "its own program",
};

/**
 * "Starting games from Steam": which launcher each emulator's game
 * shortcuts start (Steam ROM Manager's parsers), whether it can work, and a
 * switch to Emu Hub's own launchers (backend/launchers.py), which do not need
 * EmuDeck's files. ROM-Store re-points the shortcuts afterwards.
 */
const LaunchCheck: FC = () => {
  const [check, setCheck] = useState<Check | null>(null);
  const [busy, setBusy] = useState(false);
  const [note, setNote] = useState<string | null>(null);

  useEffect(() => {
    launchCheck().then(setCheck).catch((error) => setNote(String(error)));
  }, []);

  if (!check || !check.srm || !check.emulators.length) return null;
  const allEmuHub = check.emulators.every((row) => row.kind === "emuhub");
  const broken = check.emulators.filter((row) => !row.ok).length;

  const toggle = () => {
    setBusy(true);
    setNote(null);
    switchLaunchers(!allEmuHub)
      .then((result) => {
        setCheck(result.check);
        if (!result.ok) return setNote(result.error ?? "That did not work.");
        if (!result.changed) return;
        const label = allEmuHub ? "the previous launchers" : "Emu Hub's launchers";
        announceChoice({ console: "all", emulator: label });
        toaster.toast({ title: `Games now start through ${label}`, body: "ROM-Store updates your Steam shortcuts." });
      })
      .catch((error) => setNote(String(error)))
      .finally(() => setBusy(false));
  };

  return (
    <section className="ed-section">
      <Focusable noFocusRing className="ed-view-head" flow-children="row">
        <div className="ed-section-title">Starting games from Steam</div>
        <Button className={`ed-btn${allEmuHub ? " ghost" : ""}`} noFocusRing disabled={busy} onClick={toggle}>
          {busy ? "Working…" : allEmuHub ? "Use the previous launchers" : "Start games through Emu Hub"}
        </Button>
      </Focusable>
      <p className="ed-note">
        {allEmuHub
          ? "Game shortcuts start Emu Hub's launchers, which find each emulator wherever it is installed (AppImage or Flathub)."
          : `Game shortcuts start the launcher Steam ROM Manager names for each emulator.${
              broken ? ` ${broken === 1 ? "One of them" : `${broken} of them`} cannot start games right now.` : ""
            } Emu Hub's launchers find each emulator wherever it is installed and do not need EmuDeck's files.`}
      </p>
      <Focusable noFocusRing className="ed-rows" flow-children="column">
        {check.emulators.map((row) => (
          <Focusable
            noFocusRing
            key={row.emu_id}
            className="ed-row ed-f"
            focusClassName="is-focus"
            onActivate={() => undefined}
            onOKActionDescription={row.ok ? "Works" : "Cannot start games"}
          >
            <div className="ed-row-text">
              <div className="ed-row-label">{row.name}</div>
              <div className="ed-row-hint">
                {KIND[row.kind]} · {row.consoles.join(", ")}
                {row.problems.length ? <span className="ed-warn-text"> · {row.problems.join(" · ")}</span> : null}
              </div>
            </div>
            <div className="ed-row-side">
              {row.ok ? <span className="ed-chip ok">Works</span> : <span className="ed-chip warn">Won't start</span>}
            </div>
          </Focusable>
        ))}
      </Focusable>
      {check.failures?.length ? (
        <p className="ed-note">Last failed starts: {check.failures.slice(-2).join(" · ")}</p>
      ) : null}
      {note ? <div className="ed-banner warn">{note}</div> : null}
    </section>
  );
};

export default LaunchCheck;
