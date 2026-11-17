import { FC, useEffect, useState } from "react";
import { Button, Focusable } from "@decky/ui";

import { createFolders, getLibrary, LibraryInfo, setLibraryRoot } from "../api";
import { refresh } from "../state";
import { Glyph, Spinner, tilde } from "./ui";

/**
 * Where games and BIOS files live, and which consoles still need system
 * files. EmuDecky never downloads BIOS files, firmware or keys; it only
 * checks for them.
 */
const LibraryView: FC = () => {
  const [info, setInfo] = useState<LibraryInfo | null>(null);
  const [busy, setBusy] = useState(false);
  const [note, setNote] = useState<string | null>(null);

  useEffect(() => {
    getLibrary().then(setInfo).catch((error) => setNote(String(error)));
  }, []);

  const choose = (path: string) => {
    setBusy(true);
    setLibraryRoot(path)
      .then((next) => {
        setInfo(next);
        setNote(null);
        return refresh();
      })
      .finally(() => setBusy(false));
  };
  const make = () => {
    setBusy(true);
    createFolders()
      .then((result) => {
        setInfo(result.library);
        setNote(result.ok ? (result.made ? `Created ${result.made} folders.` : "All folders were already there.") : result.errors[0]);
        return refresh();
      })
      .finally(() => setBusy(false));
  };

  if (!info) {
    return (
      <div className="ed-view">
        <div className="ed-banner">{note ?? <><Spinner /> Reading the library…</>}</div>
      </div>
    );
  }

  const withGames = info.consoles.filter((c) => c.files > 0).length;
  const folders = info.consoles.filter((c) => c.exists).length;
  const choices = [{ path: "", label: "Automatic", hint: "An EmuDeck library if there is one, else ~/EmuDecky" }].concat(
    info.candidates.map((c) => ({
      path: c.path,
      label: c.path,
      hint: `${c.kind === "emudeck" ? "EmuDeck library" : "EmuDecky library"} · ${c.where === "sd" ? "SD card" : "internal storage"}`,
    })),
  );

  return (
    <Focusable noFocusRing className="ed-view" flow-children="column">
      <Focusable noFocusRing className="ed-view-head" flow-children="row">
        <h2 className="ed-h2">Library</h2>
        <Button className="ed-btn" noFocusRing onClick={make} disabled={busy}>
          {info.ready ? "Add missing folders" : "Create folders"}
        </Button>
      </Focusable>
      <p className="ed-note">
        Games go in <span className="ed-path">{tilde(info.roms)}/&lt;console&gt;</span>, BIOS files in{" "}
        <span className="ed-path">{tilde(info.bios)}</span>. ROM-Store downloads into the same folders, and the Deck settings point each
        emulator at them. {info.exists ? `${folders} console folders, ${withGames} with games.` : "The folder does not exist yet."}
      </p>
      {note ? <div className="ed-banner">{note}</div> : null}

      <section className="ed-section">
        <div className="ed-section-title">Library folder</div>
        <Focusable noFocusRing className="ed-rows" flow-children="column">
          {choices.map((choice) => {
            const selected = info.automatic ? choice.path === "" : choice.path === info.root;
            return (
              <Focusable
                noFocusRing
                key={choice.path || "auto"}
                className="ed-row ed-f"
                focusClassName="is-focus"
                onActivate={() => choose(choice.path)}
                onClick={() => choose(choice.path)}
                onOKActionDescription="Use this folder"
              >
                <div className="ed-row-text">
                  <div className={`ed-row-label${choice.path ? " ed-path" : ""}`}>{choice.label}</div>
                  <div className="ed-row-hint">{choice.path === "" ? `${choice.hint} (now ${info.root})` : choice.hint}</div>
                </div>
                <div className="ed-row-side">{selected ? <span className="ed-chip ok">In use</span> : <Glyph round>A</Glyph>}</div>
              </Focusable>
            );
          })}
        </Focusable>
      </section>

      <section className="ed-section">
        <div className="ed-section-title">BIOS and system files</div>
        <p className="ed-note">
          EmuDecky never downloads these. Copy them from your own consoles; this list shows what each emulator still needs.
        </p>
        <Focusable noFocusRing className="ed-rows" flow-children="column">
          {info.bios_status.map((item) => (
            <Focusable
              noFocusRing
              key={item.console}
              className="ed-row ed-f"
              focusClassName="is-focus"
              // Focusable only so the d-pad can scroll the list; A does nothing.
              onActivate={() => undefined}
              onOKActionDescription={item.found ? "Found" : "Missing"}
            >
              <div className="ed-row-text">
                <div className="ed-row-label">{item.label}</div>
                <div className="ed-row-hint">
                  {item.found ? (
                    <span className="ed-path">{item.found}</span>
                  ) : (
                    <>
                      {item.files.length ? `${item.files.slice(0, 3).join(", ")}${item.files.length > 3 ? ", …" : ""}` : ""}
                      {item.files.length && item.hint ? " · " : ""}
                      {item.hint}
                      {item.folder ? <> · in <span className="ed-path">{item.folder}</span></> : null}
                    </>
                  )}
                </div>
              </div>
              <div className="ed-row-side">
                {item.found ? (
                  <span className="ed-chip ok">Found</span>
                ) : item.optional ? (
                  <span className="ed-chip">Optional</span>
                ) : (
                  <span className="ed-chip warn">Missing</span>
                )}
              </div>
            </Focusable>
          ))}
        </Focusable>
      </section>
    </Focusable>
  );
};

export default LibraryView;
