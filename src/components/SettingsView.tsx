import { FC, useEffect, useState } from "react";
import { Button, Dropdown, Focusable, TextField } from "@decky/ui";

import { getSettings, setSettings, Settings } from "../api";
import { Switch } from "./ui";
import { BackendError } from "./EmulatorsView";

type Toggle = "auto_presets" | "add_to_steam" | "check_updates";

const TOGGLES: { key: Toggle; label: string; hint: string }[] = [
  {
    key: "auto_presets",
    label: "Set up new emulators for the Deck",
    hint: "Right after installing, apply its Deck settings: fullscreen, your game and BIOS folders, controller, resolution. Your original files are kept and can be restored.",
  },
  {
    key: "add_to_steam",
    label: "Add emulators to Steam",
    hint: "Each installed emulator gets a shortcut in your library, so it starts from Game Mode.",
  },
  {
    key: "check_updates",
    label: "Check for updates in the background",
    hint: "Looks for new versions now and then and tells you when there are some. Nothing is installed without you.",
  },
];

const INTERVALS = [3, 6, 12, 24, 72, 168].map((hours) => ({
  data: hours,
  label: hours < 24 ? `Every ${hours} hours` : hours === 24 ? "Once a day" : hours === 72 ? "Every 3 days" : "Once a week",
}));

/** Every change is saved at once; there is no Save button. */
const SettingsView: FC = () => {
  const [settings, setLocal] = useState<Settings | null>(null);
  const [token, setToken] = useState("");
  const [saved, setSaved] = useState<string | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);

  const load = () => {
    setLoadError(null);
    getSettings()
      .then(setLocal)
      .catch((error) => setLoadError(String(error)));
  };
  useEffect(load, []);

  const change = (changes: Partial<Settings> & { github_token?: string }) => {
    if (settings) setLocal({ ...settings, ...changes } as Settings);
    setSettings(changes)
      .then((next) => {
        setLocal(next);
        setSaved("Saved");
      })
      .catch((error) => setSaved(`Not saved: ${error}`));
  };

  if (!settings) return loadError ? <BackendError error={loadError} onRetry={load} /> : <div className="ed-view" />;

  return (
    <Focusable noFocusRing className="ed-view" flow-children="column">
      <div className="ed-view-head">
        <h2 className="ed-h2">Settings</h2>
        {saved ? <span className="ed-muted">{saved}</span> : null}
      </div>
      <Focusable noFocusRing className="ed-rows" flow-children="column">
        {TOGGLES.map((toggle) => (
          <Focusable
            noFocusRing
            key={toggle.key}
            className="ed-row ed-f"
            focusClassName="is-focus"
            onActivate={() => change({ [toggle.key]: !settings[toggle.key] })}
            onClick={() => change({ [toggle.key]: !settings[toggle.key] })}
            onOKActionDescription={settings[toggle.key] ? "Turn off" : "Turn on"}
          >
            <div className="ed-row-text">
              <div className="ed-row-label">{toggle.label}</div>
              <div className="ed-row-hint">{toggle.hint}</div>
            </div>
            <Switch on={Boolean(settings[toggle.key])} />
          </Focusable>
        ))}
        <Focusable noFocusRing className="ed-row" flow-children="row">
          <div className="ed-row-text">
            <div className="ed-row-label">How often</div>
            <div className="ed-row-hint">Background checks ask GitHub, Forgejo and Flathub; each check is about 20 small requests.</div>
          </div>
          <div className="ed-row-control ed-dd">
            <Dropdown
              rgOptions={INTERVALS}
              selectedOption={settings.check_hours}
              onChange={(option) => change({ check_hours: option.data })}
              menuLabel="How often"
            />
          </div>
        </Focusable>
        <Focusable noFocusRing className="ed-row" flow-children="row">
          <div className="ed-row-text">
            <div className="ed-row-label">GitHub token (optional)</div>
            <div className="ed-row-hint">
              GitHub answers 60 requests an hour without one. A token with no permissions raises that.{" "}
              {settings.github_token_set ? "A token is set." : "None set."} It is only sent to api.github.com.
            </div>
          </div>
          <div className="ed-row-control">
            <TextField label="" value={token} onChange={(event) => setToken(event.target.value)} />
          </div>
          <Button
            className="ed-btn ghost"
            noFocusRing
            onClick={() => {
              change({ github_token: token.trim() });
              setToken("");
            }}
          >
            {token.trim() ? "Save" : settings.github_token_set ? "Remove" : "Save"}
          </Button>
        </Focusable>
      </Focusable>
      <p className="ed-note">
        Emu Hub installs emulators from their projects' own releases and from Flathub, into ~/Applications and your Flatpak
        apps. It never downloads games, BIOS files, firmware or keys.
      </p>
    </Focusable>
  );
};

export default SettingsView;
