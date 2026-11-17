import { FC, memo } from "react";
import { Focusable } from "@decky/ui";
import { toaster } from "@decky/api";

import { Emulator } from "../api";
import { primary, primaryOf, PRIMARY_LABEL } from "../actions";
import { chip, EmuIcon, Glyph, Progress, statusLine } from "./ui";

/**
 * One emulator. A runs its main action (install, update or launch), X opens
 * everything else. Borders and background colours only, no transforms
 * (AGENTS.md §10).
 */
const EmulatorCard: FC<{ emu: Emulator; onMore: (id: string) => void }> = ({ emu, onMore }) => {
  const action = primaryOf(emu);
  const tag = chip(emu);
  const running = emu.job && (emu.job.state === "queued" || emu.job.state === "running");
  const run = () => {
    if (action === "busy") {
      onMore(emu.id);
      return;
    }
    primary(emu)
      .then((error) => {
        if (error) toaster.toast({ title: emu.name, body: error });
      })
      .catch((error) => toaster.toast({ title: emu.name, body: String(error) }));
  };
  return (
    <Focusable
      noFocusRing
      className={`ed-emu ed-f${emu.installed ? "" : " off"}`}
      data-emu={emu.id}
      focusClassName="is-focus"
      onActivate={run}
      onClick={run}
      onOKActionDescription={action === "busy" ? "Details" : PRIMARY_LABEL[action]}
      onSecondaryButton={() => onMore(emu.id)}
      onSecondaryActionDescription="More"
    >
      <EmuIcon emu={emu} />
      <div className="ed-emu-text">
        <div className="ed-emu-name">{emu.name}</div>
        {running ? (
          // While a job runs its bar takes the consoles' line.
          <div className="ed-emu-bar">
            <Progress value={emu.job!.progress} />
          </div>
        ) : (
          <div className="ed-emu-sub">{emu.consoles.join(" · ")}</div>
        )}
        <div className={`ed-emu-status${emu.job?.state === "error" ? " ed-bad" : ""}`}>{statusLine(emu)}</div>
      </div>
      <div className="ed-emu-side">
        <span className={`ed-chip ${tag.tone}`}>{tag.text}</span>
        <Glyph round>X</Glyph>
      </div>
    </Focusable>
  );
};

export default memo(EmulatorCard);
