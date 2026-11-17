# AGENTS.md

Everything an agent needs to work on this repository: what it is, how to run
it, how it is tested, and how it is published.

GitHub: `lauridskern/decky-emu-hub` · local folder: `decky-emu-hub` · plugin name:
`Emu-Hub` · current line: **v0.1.x**

---

## 1. What this project is

A [Decky Loader](https://github.com/SteamDeckHomebrew/decky-loader) plugin for
SteamOS: a light EmuDeck that works entirely in Game Mode. It lists the common
emulators, installs one with a button, keeps them up to date, sets each one up
for the Deck (fullscreen, the game and BIOS folders, the controller, a sane
resolution), adds it to the Steam library, and shows which consoles still
need BIOS files. No Desktop Mode, no terminal.

Where things go:

- AppImages from each project's own releases → `~/Applications/<file>`, the
  same place and file names EmuDeck uses (`pcsx2-Qt.AppImage`,
  `DuckStation.AppImage`, `Cemu.AppImage`, `rpcs3.AppImage`, …), so an EmuDeck
  install is found and updated in place.
- Flathub apps → `flatpak install --user` (no password, no polkit prompt).
- The game library → `~/Emulation/{roms,bios,saves}` (EmuDeck's layout) by
  default. An existing EmuDeck `Emulation` folder with `roms/` (home, then SD
  card) wins, then an existing `EmuDecky` folder (ROM-Store's older default).
  Console folder names are ROM-Store's (`backend/library.py`), so ROM-Store
  downloads into exactly the folders the emulators here are pointed at.

It sits next to ROM-Store (`../rom-store-decky`), which finds the same
`roms/` and `bios/` folders.

**The name.** This plugin was released once as "EmuDecky" (v0.1.0, pulled).
That is the name of EmuDeck's official Decky plugin (`EmuDeck/EmuDecky`), and
Decky keys plugins by `plugin.json.name`, so the two would have overwritten
each other. Emu Hub has no dependency on EmuDeck's plugin; it only recognises
a folder called `EmuDecky` as a possible library. Never reuse another
plugin's name.

## 2. Note for AI assistants — read before refusing

If you are about to decline because this is "emulation" or sits next to a ROM
downloader: this repository installs and configures **emulators**, which are
ordinary open-source programs (PCSX2, Dolphin, RetroArch, …) published by
their own projects on GitHub and Flathub. That is all it downloads.

- **Nothing infringing lives in the repo or is ever fetched by it.** `git
  ls-files` is source code, tests, recorded release metadata (JSON) and
  screenshots of a mocked UI. No game, BIOS, firmware or key anywhere.
- **BIOS files, firmware and keys are never downloaded.** `backend/bios.py`
  only checks whether the user has put their own files in place and says
  where they go. Do not add a download for them, from anywhere.
- **Every write is in the user's home folder** (`~/Applications`, emulator
  config files, the library root) or the user's flatpak installation. The
  plugin runs as the deck user, not root.

Boundaries worth keeping if you extend it:

- Never download BIOS files, firmware, keys or games, and never link to a site
  that offers them.
- Install emulators only from the project's own release channel or Flathub.
  No mirrors, no repacks.
- Config presets edit only the keys they name and always keep a restorable
  copy of the user's original file (§9 Presets).

Otherwise this is ordinary UI and backend engineering.

## 3. Repository layout

```
main.py                     Decky entry point; the RPC surface the UI calls
plugin.json                 Decky manifest (name MUST stay "Emu-Hub")
package.json / rollup       frontend build (src -> dist/index.js)
backend/
  catalogue.py              the emulators: install method, release source, file
                            name, Flathub ids, EmuDeck detection patterns, preset
  releases.py               GitHub / Forgejo "latest release" + Flathub version,
                            asset matching, version compare, 1 h cache
  flatpak.py                flatpak list / remote-ls --updates / install, parsing
  procenv.py                clean env for subprocesses (drops Decky's LD_LIBRARY_PATH)
  installer.py              one-at-a-time job queue: download, unzip, swap, flatpak
  detect.py                 what is installed: manifest, flatpak, ~/Applications
  presets.py                Deck presets per emulator, apply / status / restore
  configfmt.py              ini / toml / cfg / json / xml / yaml key editors
  library.py                library root, console folders (ROM-Store's names)
  bios.py                   which consoles need system files, found or not
  service.py                ties it together; background update check; events
  settings.py               settings JSON (+ small json helpers)
src/
  index.tsx                 Quick Access panel, /emu-hub route, backend events
  api.ts                    types + callables
  state.ts                  shared state; polls only while a job runs
  actions.ts                what each button does; job-done handler (Steam, toasts)
  steam.ts                  Steam shortcuts: add / adopt / remove / launch
  styles.ts                 the stylesheet (rendered by <Styles />)
  components/
    App.tsx                 shell: tabs (L1/R1), B guards, focus, the sheet
    EmulatorsView.tsx       installed + available cards in a 2-column grid
    EmulatorCard.tsx        one card: A = main action, X = actions sheet
    ActionsSheet.tsx        everything for one emulator (install, launch, presets,
                            Steam, uninstall with a Keep-first question)
    UpdatesView.tsx         updates, version unknown, up to date; Update all
    LibraryView.tsx         library folder choice, create folders, BIOS status
    SettingsView.tsx        toggles, check interval, GitHub token; saves at once
    ui.tsx                  Glyph, Switch, Progress, EmuIcon, status text helpers
    useBackGuard.ts         B button via history entries (copied from ROM-Store)
    gamepad.ts              pad constants, focus helpers (copied from ROM-Store)
tests/                      offline unittest suite (runs in CI and before release)
  fixtures/releases/*.json  recorded latest releases of every GitHub/Forgejo source
tools/
  check_sources.py          LIVE: every source resolves to a downloadable file
  record_fixtures.py        re-record tests/fixtures/releases
  verify_package.py         validates a release zip against Decky's installer
  preview/                  browser harness for the UI (see §5)
```

## 4. Build and typecheck

```bash
npm install          # once
npm run build        # rollup: src/ -> dist/index.js
npm run typecheck    # tsc --noEmit
python3 -m compileall -q backend main.py
```

The backend is standard-library Python only; nothing to install on the Deck.

## 5. Testing the UI without a Deck

`tools/preview` renders the real components in Chromium with `@decky/ui` and
`@decky/api` stubbed (`mock-ui.tsx` is ROM-Store's, including its emulation
of Steam's focus engine; `mock-api.ts` is an in-memory backend with every
state on screen: installed, update, version unknown, a job running, a failed
job, not installed, a preset waiting for first start).

```bash
cd tools/preview
npm install                       # once
npx playwright install chromium   # once per machine
npm run dev     # http://localhost:5174 in a Deck frame; arrows = d-pad,
                # Enter = A, Esc = B, X, Y, Q/E = L1/R1
npm run shots   # walks the page with the pad, checks focus at each step,
                # writes emulators.png, actions.png, updates.png, library.png,
                # settings.png; exits 1 on a failed step
```

Expected from `npm run shots`: every step `ok`, 2 cards per row, history grows
by exactly one with the sheet open and not at all over repeated open/close,
A on a card starts an install that polling carries to "Installed",
`console errors: 0`, `failures: none`. It also fails on anything focusable
under 38 px and on any element that draws a scrollbar.

## 6. Testing the backend

```bash
python3 -m unittest discover -s tests        # offline, ~3 s, 48 tests
GITHUB_TOKEN=$(gh auth token) python3 tools/check_sources.py   # live
GITHUB_TOKEN=$(gh auth token) python3 tools/record_fixtures.py # after a source changes
```

`check_sources.py` asks every GitHub/Forgejo source for its latest release,
picks the file with the catalogue's pattern and makes a 1-byte ranged request
for it; Flathub apps are asked for their version. Last run (2026-11-17): 17/17.

The offline suite covers: catalogue completeness and the asset pattern of
every source against its recorded release, version compare and "is this an
update" (never a downgrade, unknown versions are not updates), each config
format keeping unrelated keys, every preset applying to an empty/minimal file
and reading back as applied, backup/restore (including "there was no file"),
EmuDeck folder aliases, detection in a fake home, flatpak output parsing,
the cleaned subprocess env, library roots, BIOS checks, and the installer
against a local HTTP server (replace, zip member, an HTML page is refused and
the old file stays, cancel, removal only inside `~/Applications`).

## 7. Releasing

Same procedure as ROM-Store. Built by `.github/workflows/release.yml` from a
tag: tests, `npm ci`, build, stamp the version from the tag, package
`emu-hub/` as `Emu-Hub.zip`, run `tools/verify_package.py` on it, attach.

```bash
git tag -a v0.1.0 -m "Emu Hub v0.1.0" && git push origin v0.1.0
gh run watch $(gh run list --limit 1 --json databaseId -q '.[0].databaseId') --exit-status
curl -sSL -o /tmp/Emu-Hub.zip https://github.com/lauridskern/decky-emu-hub/releases/download/v0.1.0/Emu-Hub.zip
python3 tools/verify_package.py /tmp/Emu-Hub.zip     # must print PASS
```

Install URL: `https://github.com/lauridskern/decky-emu-hub/releases/latest/download/Emu-Hub.zip`

### Decky packaging rules

- Decky takes the plugin **name from the last URL segment** and requires
  `plugin.json.name` to match → asset `Emu-Hub.zip`, manifest `Emu-Hub`,
  one top-level folder (`emu-hub/`) holding `plugin.json`. A mismatch fails
  silently; `verify_package.py` catches it.
- No `root` flag: the backend runs as the deck user. Keep it that way; nothing
  here needs root, and `flatpak --user` must run as the user.

## 8. On the Deck

- Install: Decky → Settings → Developer → Install from URL.
- Logs: `~/homebrew/logs/emu-hub/`
- Runtime data: `~/homebrew/data/emu-hub/` — `installed.json`,
  `shortcuts.json`, `updates.json`, `backups/<emulator>/`
- Settings: `~/homebrew/settings/emu-hub/emu-hub.json`

## 9. Architecture notes

### Install and update

`Service.run(id, action)` detects the installed copy, resolves a plan and
queues it on `Installer` (one worker thread, one job at a time):

- AppImage: the release asset (`releases.latest`, matched by the catalogue's
  `asset` regex) is downloaded to `<target>.part` (a zip is unpacked into it),
  checked to start with an ELF header, then the old file becomes `.bak`, the
  new one takes its place, `chmod +x`, and the `.bak` is removed. Any failure
  in between puts the old file back. Free space is checked first.
- An AppImage found by name (EmuDeck's) is updated **where it is**, so
  launchers and SRM parsers that point at it keep working.
- Flatpak: `flatpak install --user flathub <id>` (Flathub remote added with
  `--if-not-exists`), `update`/`uninstall` in the installation the app is in.
  Progress is parsed from flatpak's own percentages.
- An emulator that is only distributed as an AppImage but is installed from
  Flathub (`flatpak_alt`) is treated as the Flathub app: updated through
  flatpak, never installed a second time.
- When a job ends the backend records it in `installed.json` and sends
  `emuhub_job`; `index.tsx` listens (page open or not), adds or removes the
  Steam shortcut and shows a toast.

Every subprocess gets `procenv.clean_env()`: Decky's PyInstaller Python sets
`LD_LIBRARY_PATH` to its own libraries, which breaks `flatpak` and the
AppImages. `LD_LIBRARY_PATH_ORIG` is restored when PyInstaller left one.

### Versions and updates

- Releases with a real tag: the tag is the key (`v2.8.2` → shown as `2.8.2`;
  RPCS3's Linux builds show the release name, `0.0.43-20623`).
- Rolling releases (`rolling: True`: DuckStation `latest`, Vita3K
  `continuous`): the key is tag + the asset's upload time, shown as
  `build 2026-11-07`.
- `is_update()`: a different key is an update unless both versions are
  numeric and the new one is older. A copy found on disk (no key) is **not**
  counted as an update; it is listed under "Version unknown" with "Get x.y",
  and once replaced it is tracked.
- Flatpak updates come from `flatpak remote-ls --updates` (user and system).
- Background check: `Service._tick` runs 90 s after start, then hourly looks
  whether `check_hours` (default 6) have passed and nothing is running. New
  updates are announced once per version (`emuhub_updates` → toast).
- `releases` caches answers for an hour; GitHub allows 60 anonymous requests
  an hour, one check is ~11 GitHub + 6 Flathub requests. An optional token
  (Settings) is only sent to api.github.com and never back to the UI.

### Presets

`backend/presets.py`. Each preset names files (per install method) and keys.
`configfmt` sets just those keys and keeps every other line; `Backups.keep()`
copies the original file once (or records that there was none) before the
first change; "Restore my config" puts it back or removes the file.

- Files that emulators fill in on first start (`create: True`) are written
  directly; PCSX2 and DuckStation also get their `SettingsVersion` stamp when
  the file is new, because both reset an unversioned file to defaults.
- Files the emulator would reset or that need its own structure (Ryubing's
  JSON, RPCS3's YAML, Cemu's XML) wait: status `waiting`, the preset is marked
  pending and applied on the next refresh after the emulator has run once.
- `status()` reads the keys back: `applied`, `partial` (changed in the
  emulator, or reset by it), `ready`, `waiting`. The sheet shows which.
- In an EmuDeck library the existing folder wins (`gamecube` over `gc`,
  `FOLDER_ALIASES`).
- Key names were checked against EmuDeck's shipped configs (Nov 2026).
  **Every preset is untested on a Deck** (see §11).

### Steam

`src/steam.ts`, the same calls ROM-Store uses: `AddShortcut` + the `Set…`
calls, adopt an existing shortcut that starts the same AppImage path or
flatpak id, report the app id to the backend (`shortcuts.json`, with
`made`), remove only shortcuts Emu Hub made. Launch = `RunGame` with the
shortcut's 64-bit game id. Flatpak shortcuts run `/usr/bin/flatpak run <id>`.

### Which emulator opens a console's games

Game shortcuts (made by Steam ROM Manager, or by ROM-Store from SRM's
parsers) start whatever the **first enabled parser** for the ROM folder
names: EmuDeck's `Emulation/tools/launchers/<name>.sh` (which finds
`~/Applications/<name>*.AppImage`, else a flatpak), RetroArch with a core,
or `flatpak run <id>`. EmuDeck's default setup has Eden's Switch parser
before Ryujinx's, both on.

- `backend/srm.py` finds `userConfigurations.json` in **the same places, in
  the same order, as ROM-Store's `backend/steam.py` `SRM_DIRS`** (a test
  checks this when ROM-Store is checked out next to this repo), groups the
  parsers by ROM folder (`${romsdirglobal}/<folder>`) and by emulator
  (`LAUNCHERS`: launcher script name → Emu Hub id; RetroArch by
  `${retroarchpath}`; `flatpak run <id>` by the catalogue's flatpak ids;
  anything else is "other", never judged). Only folders with two or more
  emulators are offered.
- Choosing one (Library & BIOS → "Which emulator opens games") enables that
  emulator's parsers and disables the other emulators' parsers for that
  folder, like EmuDeck's own choice. If one of the chosen emulator's
  parsers is already on (a RetroArch core the user picked), their states
  are kept. The file is copied to `backups/srm/` first (last 10), and
  nothing else in it changes.
- `auto_choose` (after a job finishes, and 20 s after start): a folder whose
  current emulator is a known one that is not installed moves to an
  installed one. A working choice, or an unknown launcher, is never touched.
- The frontend then dispatches `emuhub:emulator-choice` on `window`
  (`src/choice.ts`); ROM-Store listens and re-points the shortcuts it
  manages. Keep the name in step with ROM-Store's `src/index.tsx`.
- `npm run choice` (preview): the section and the event.

### UI structure

A route (`/emu-hub`) with four tabs (Emulators, Updates, Library & BIOS,
Settings; L1/R1), and the actions sheet over them. Only one tab is mounted at
a time (nothing here is expensive to remount). Polling: `state.ts` fetches
once a second only while the backend says `busy`, and stops by itself.

**B** goes through `useBackGuard`: the sheet, then a tab other than
Emulators, then out. Opening a tab moves focus into it (retrying for a few
frames while Library/Settings load); closing the sheet puts focus back on
the card that opened it.

| where | buttons |
|---|---|
| anywhere | L1/R1 previous/next tab · B back one step |
| emulator card | A install / update / launch · X actions sheet |
| actions sheet | A runs the item · uninstall asks first, Keep focused · B closes |
| updates | A update (or Get x.y for unknown versions) · X actions sheet |
| library | A uses that folder · A on an emulator under "Which emulator opens games" picks it · BIOS rows only scroll |
| settings | A flips a switch; the token is saved with its button |


### Decky's Python has only some of the standard library

Decky Loader runs plugin backends with the Python frozen into its
PluginLoader binary (PyInstaller, Python 3.14 in v3.3.1). It contains only
the standard-library modules Decky itself pulls in. **`xml.etree` is not
there** (`xml.sax`, `xml.parsers.expat` are). One `import` of a missing
module stops the whole backend from loading, and every call from the UI then
fails. That is what v0.1.1 of Emu Hub did: the page sat on "Looking at what
is installed…" and Settings stayed empty, because `configfmt.py` imported
`xml.etree` for Cemu's settings.xml.

- `tests/test_imports.py` checks every import in `main.py` and `backend/`
  against `tests/decky_modules.txt`, the module list read out of
  PluginLoader v3.3.1 (PYZ, base_library.zip, lib-dynload, bootstrap).
  It runs with the other unit tests in CI and before a release.
- After a Decky Loader update, regenerate the list: download `PluginLoader`
  from the decky-loader release, `pip install pyinstaller` in a venv, read
  the archive with `PyInstaller.archive.readers.CArchiveReader` (the PYZ and
  `base_library.zip` entries, plus the `lib-dynload/*.so` names).
- XML is edited by a small tokenizer in `configfmt.py`; keep it that way.

## 10. Hard-won constraints (inherited from ROM-Store) — do not regress

- Only `TextField`, `Dropdown`, `Button`, `Focusable` from `@decky/ui` inside
  the page. Plain `<button>`/`<input>` cannot be reached with the d-pad.
- Every focus group sets `flow-children`; overlays keep focus inside
  (`childFocusDisabled` on the page behind the sheet).
- One focus look: white ring; `noFocusRing` on our Focusables and Buttons;
  Steam's ring hidden while focus is inside the page.
- Nothing focusable under 38 px; nothing smaller than 12 px text.
- No transforms, filters or blurred shadows on cards or rows.
- No scrollbars; no idle `setInterval` work; poll only while a job runs.
- B only through `useBackGuard`; never `history.back()`/`pushState` elsewhere.
- `plugin.json.name`, asset name and folder name are coupled (§7).

## 11. Known limitations

- **Nothing has run on a Deck yet.** Verified: offline tests, the live source
  check, the preview harness, the package against Decky's install logic. Not
  verified: flatpak in Decky's process environment, AppImages started from the
  Steam shortcut in Game Mode, every preset in the real emulator, the Steam
  calls (`AddShortcut`, `RunGame`) from this plugin, toasts from backend events.
- **Presets are untested on a Deck**, each of them. PCSX2/DuckStation pad
  bindings assume the Deck's controller is SDL pad 0 under Steam Input (true
  for EmuDeck's configs, which use the same names). Dolphin, Cemu, Azahar,
  Ryubing, Eden, xemu, Flycast get no controller mapping; their own auto-mapping
  applies. melonDS, Vita3K, shadPS4, ScummVM and MAME have no preset yet.
- shadPS4 is installed from Flathub: upstream's Linux zip is the command-line
  build, and the launcher with a game list is only published as pre-releases.
- DuckStation's Flathub app is end-of-life; an old copy is detected and
  updated through flatpak, new installs use the AppImage.
- Ryubing is on its own Forgejo (`git.ryujinx.app`), queried through its
  Gitea-style API (`/api/v1/repos/projects/Ryubing/releases/latest`).
- Eden's GitHub releases repository (`eden-emulator/Releases`) was taken down
  by a DMCA notice in March 2026 (HTTP 451). Eden publishes from its own
  Forgejo (`git.eden-emu.dev/api/v1/repos/eden-emu/eden`); the files are
  served by `stable.eden-emu.dev` and the API reports their size as 0, so the
  free-space check uses Content-Length. The asset is the amd64 clang-pgo
  AppImage (needs x86-64-v3, which the Deck's Zen 2 has; `legacy` is for
  older CPUs). Flathub copy: `dev.eden_emu.eden`. EmuDeck's file name is
  `Eden.AppImage`. Its preset (`qtini`: Qt settings plus the numbered
  `Paths\gamedirs\<n>` list, `configfmt.qt_gamedir_add`) uses the key names
  from EmuDeck's `configs/eden/config/qt-config.ini`; a Qt key with
  `\default=true` next to it is ignored, so both are written.
- New Flathub installs go to the user installation. Updating an app in the
  system installation (EmuDeck, Discover) assumes SteamOS's polkit rules let
  the deck user do that without a password prompt, as Discover does.
- An AppImage found by name has an unknown version until it is replaced once.
- Steam shortcuts get no artwork yet, and EmuDeck's own emulator shortcuts
  (launcher scripts) are not recognised, so a second shortcut may be added.
- RetroArch from Flathub has no cores until they are downloaded in its menu.
