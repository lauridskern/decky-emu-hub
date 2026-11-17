import { FC, useState } from "react";
import { Button, Focusable } from "@decky/ui";

import { createFolders, State } from "../api";
import { refresh } from "../state";
import EmulatorCard from "./EmulatorCard";
import { Spinner } from "./ui";

/** Every emulator, installed ones first. */
const EmulatorsView: FC<{ state: State | null; onMore: (id: string) => void }> = ({ state, onMore }) => {
  const [making, setMaking] = useState(false);
  if (!state) {
    return (
      <div className="ed-view">
        <div className="ed-banner">
          <Spinner /> Looking at what is installed…
        </div>
      </div>
    );
  }
  const installed = state.emulators.filter((emu) => emu.installed);
  const available = state.emulators.filter((emu) => !emu.installed);
  const makeFolders = () => {
    setMaking(true);
    createFolders()
      .then(() => refresh())
      .finally(() => setMaking(false));
  };
  return (
    <Focusable noFocusRing className="ed-view" flow-children="column">
      {!state.library.ready ? (
        <Focusable noFocusRing className="ed-banner warn" flow-children="row">
          <span style={{ flex: "1 1 auto" }}>
            No game library yet. Emu Hub will make <span className="ed-path">{state.library.root}</span> with a folder per console.
          </span>
          <Button className="ed-btn" noFocusRing onClick={makeFolders} disabled={making}>
            {making ? "Creating…" : "Create folders"}
          </Button>
        </Focusable>
      ) : null}
      {!state.flatpak ? (
        <div className="ed-banner warn">flatpak was not found, so Flathub emulators cannot be installed here.</div>
      ) : null}
      {installed.length ? (
        <section className="ed-section">
          <div className="ed-section-title">Installed · {installed.length}</div>
          <Focusable noFocusRing className="ed-grid" flow-children="grid">
            {installed.map((emu) => (
              <EmulatorCard key={emu.id} emu={emu} onMore={onMore} />
            ))}
          </Focusable>
        </section>
      ) : null}
      {available.length ? (
        <section className="ed-section">
          <div className="ed-section-title">{installed.length ? "More emulators" : "Emulators"} · {available.length}</div>
          <Focusable noFocusRing className="ed-grid" flow-children="grid">
            {available.map((emu) => (
              <EmulatorCard key={emu.id} emu={emu} onMore={onMore} />
            ))}
          </Focusable>
        </section>
      ) : null}
    </Focusable>
  );
};

export default EmulatorsView;
