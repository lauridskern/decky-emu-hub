import { FC, useState } from "react";
import { Button, Focusable } from "@decky/ui";
import { toaster } from "@decky/api";

import { checkUpdates, Emulator, isActive, State, updateAll } from "../api";
import * as actions from "../actions";
import { setState } from "../state";
import { ago, EmuIcon, Glyph, Progress, Spinner, statusLine } from "./ui";

const Row: FC<{ emu: Emulator; action: string; run?: () => void; onMore: (id: string) => void }> = ({ emu, action, run, onMore }) => (
  <Focusable
    noFocusRing
    className="ed-row ed-f"
    data-emu={emu.id}
    focusClassName="is-focus"
    onActivate={run ?? (() => onMore(emu.id))}
    onClick={run ?? (() => onMore(emu.id))}
    onOKActionDescription={action}
    onSecondaryButton={() => onMore(emu.id)}
    onSecondaryActionDescription="More"
  >
    <EmuIcon emu={emu} />
    <div className="ed-row-text">
      <div className="ed-row-label">{emu.name}</div>
      <div className="ed-row-hint">{statusLine(emu)}</div>
      {isActive(emu.job) ? <Progress value={emu.job!.progress} /> : null}
    </div>
    <div className="ed-row-side">
      {action}
      <Glyph round>A</Glyph>
    </div>
  </Focusable>
);

/** What can be updated, what has an unknown version, and what is current. */
const UpdatesView: FC<{ state: State | null; onMore: (id: string) => void }> = ({ state, onMore }) => {
  const [checking, setChecking] = useState(false);
  const [queueing, setQueueing] = useState(false);
  const emulators = state?.emulators ?? [];
  const updates = emulators.filter((emu) => emu.update || (isActive(emu.job) && emu.job?.action === "update"));
  const unknown = emulators.filter((emu) => emu.installed && emu.unknown_version && !emu.update && emu.latest);
  const current = emulators.filter((emu) => emu.installed && !emu.update && !emu.unknown_version && !isActive(emu.job));

  const check = () => {
    setChecking(true);
    checkUpdates(true)
      .then(setState)
      .catch((error) => toaster.toast({ title: "Update check failed", body: String(error) }))
      .finally(() => setChecking(false));
  };
  const all = () => {
    setQueueing(true);
    updateAll()
      .then((result) => setState(result.state))
      .finally(() => setQueueing(false));
  };
  const run = (emu: Emulator, call: (emu: Emulator) => Promise<string | null>) => () => {
    call(emu).then((error) => error && toaster.toast({ title: emu.name, body: error }));
  };

  return (
    <Focusable noFocusRing className="ed-view" flow-children="column">
      <Focusable noFocusRing className="ed-view-head" flow-children="row">
        <h2 className="ed-h2">
          {updates.length ? `${updates.length} update${updates.length === 1 ? "" : "s"}` : "Everything is up to date"}
        </h2>
        <span className="ed-muted">
          {checking || state?.checking ? <Spinner /> : `Checked ${ago(state?.checked_at ?? 0)}`}
        </span>
        <Button className="ed-btn ghost" noFocusRing onClick={check} disabled={checking}>
          {checking ? "Checking…" : "Check now"}
        </Button>
        {updates.some((emu) => emu.update) ? (
          <Button className="ed-btn" noFocusRing onClick={all} disabled={queueing}>
            Update all
          </Button>
        ) : null}
      </Focusable>
      {state?.check_error ? <div className="ed-banner warn">{state.check_error}</div> : null}

      {updates.length ? (
        <section className="ed-section">
          <div className="ed-section-title">Updates</div>
          <Focusable noFocusRing className="ed-rows" flow-children="column">
            {updates.map((emu) => (
              <Row key={emu.id} emu={emu} action={isActive(emu.job) ? "Details" : "Update"} run={isActive(emu.job) ? undefined : run(emu, actions.update)} onMore={onMore} />
            ))}
          </Focusable>
        </section>
      ) : null}

      {unknown.length ? (
        <section className="ed-section">
          <div className="ed-section-title">Version unknown</div>
          <p className="ed-note">
            Installed by EmuDeck or by hand, so Emu Hub cannot tell which version these are. Replacing one with the newest
            release keeps its place and its settings, and from then on its updates show here.
          </p>
          <Focusable noFocusRing className="ed-rows" flow-children="column">
            {unknown.map((emu) => (
              <Row key={emu.id} emu={emu} action={`Get ${emu.latest}`} run={run(emu, actions.update)} onMore={onMore} />
            ))}
          </Focusable>
        </section>
      ) : null}

      {current.length ? (
        <section className="ed-section">
          <div className="ed-section-title">Up to date</div>
          <Focusable noFocusRing className="ed-rows" flow-children="column">
            {current.map((emu) => (
              <Row key={emu.id} emu={emu} action="More" onMore={onMore} />
            ))}
          </Focusable>
        </section>
      ) : null}
    </Focusable>
  );
};

export default UpdatesView;
