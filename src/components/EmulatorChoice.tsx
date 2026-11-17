import { FC, useEffect, useState } from "react";
import { Button, Focusable } from "@decky/ui";
import { toaster } from "@decky/api";

import { chooseEmulator, EmulatorChoices, emulatorChoices } from "../api";
import { announceChoice } from "../choice";

/**
 * "Which emulator opens … games": Steam ROM Manager's parsers decide which
 * emulator a game's Steam shortcut starts (backend/srm.py). Changing it here
 * switches the parsers, and ROM-Store re-points the shortcuts it manages.
 */
const EmulatorChoice: FC = () => {
  const [data, setData] = useState<EmulatorChoices | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [note, setNote] = useState<string | null>(null);

  useEffect(() => {
    emulatorChoices().then(setData).catch((error) => setNote(String(error)));
  }, []);

  const pick = (console: string, label: string, key: string) => {
    setBusy(console);
    setNote(null);
    chooseEmulator(console, key)
      .then((result) => {
        setData(result.choices);
        if (!result.ok) return setNote(result.error ?? "That did not work.");
        if (!result.changed) return;
        announceChoice({ console, emulator: label });
        toaster.toast({ title: `${label} now opens ${consoleName(result.choices, console)} games`, body: "ROM-Store updates your Steam shortcuts." });
      })
      .catch((error) => setNote(String(error)))
      .finally(() => setBusy(null));
  };

  if (!data) return null;
  return (
    <section className="ed-section">
      <div className="ed-section-title">Which emulator opens games</div>
      {!data.srm ? (
        <p className="ed-note">
          Steam ROM Manager is not set up on this Deck (EmuDeck sets it up), so there is no emulator to choose per console.
        </p>
      ) : !data.consoles.length ? (
        <p className="ed-note">
          {data.error ?? "Every console has one emulator in your Steam ROM Manager setup, so there is nothing to choose."}
        </p>
      ) : (
        <>
          <p className="ed-note">
            Steam shortcuts start the emulator chosen here; it is saved in Steam ROM Manager's setup, so SRM uses it too.
            ROM-Store re-points the games it added when you change one.
          </p>
          <Focusable noFocusRing className="ed-rows" flow-children="column">
            {data.consoles.map((group) => {
              const current = group.options.find((o) => o.key === group.current);
              return (
                <Focusable noFocusRing key={group.console} className="ed-row" flow-children="row">
                  <div className="ed-row-text">
                    <div className="ed-row-label">{group.label}</div>
                    <div className="ed-row-hint">
                      {current
                        ? `Opens in ${current.label}${current.installed === false ? " (not installed: the games will not start)" : ""}`
                        : "No emulator is switched on for these games"}
                    </div>
                  </div>
                  <Focusable noFocusRing className="ed-row-side" flow-children="row">
                    {group.options.map((option) => (
                      <Button
                        key={option.key}
                        noFocusRing
                        className={`ed-btn${option.key === group.current ? "" : " ghost"}`}
                        disabled={busy === group.console}
                        onClick={() => option.key !== group.current && pick(group.console, option.label, option.key)}
                      >
                        {option.label}
                        {option.installed === false ? " ·  not installed" : ""}
                      </Button>
                    ))}
                  </Focusable>
                </Focusable>
              );
            })}
          </Focusable>
        </>
      )}
      {note ? <div className="ed-banner warn">{note}</div> : null}
    </section>
  );
};

function consoleName(data: EmulatorChoices, console: string): string {
  return data.consoles.find((c) => c.console === console)?.label ?? console;
}

export default EmulatorChoice;
