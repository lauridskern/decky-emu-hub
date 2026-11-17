# Emu Hub

Install, update and set up emulators on the Steam Deck without leaving Game
Mode. A light EmuDeck, as a [Decky Loader](https://decky.xyz) plugin.

- **One-button installs** for RetroArch, Dolphin, PCSX2, DuckStation, PPSSPP,
  Cemu, RPCS3, Azahar, melonDS, Ryubing, xemu, Vita3K, shadPS4, Flycast,
  PrimeHack, ScummVM and MAME, from each project's own releases (AppImages in
  `~/Applications`) or from Flathub.
- **Updates**: a badge and a notification when a new version is out; update
  one or all with a button. Emulators that EmuDeck installed are found and
  updated in place.
- **Set up for the Deck**: fullscreen, your game and BIOS folders, the
  controller, a sensible resolution. Only those settings are changed, and
  your original config can be restored.
- **In your Steam library**: every installed emulator gets a shortcut, so it
  starts from Game Mode.
- **BIOS check**: which consoles still need system files and where they go.
  Emu Hub never downloads BIOS files, firmware or keys.

Games go in `~/Emulation/roms/<console>`, EmuDeck's layout (an existing EmuDeck
library on the SD card is used if there is one). [ROM-Store](https://github.com/lauridskern/decky-rom-store) uses the
same folders.

## Install

Decky → Settings → Developer → **Install plugin from URL**:

```
https://github.com/lauridskern/decky-emu-hub/releases/latest/download/Emu-Hub.zip
```

## Status

Early. Everything is tested offline and in a browser harness, and every
emulator's download source is checked live, but it has not been run on a
Deck yet. The Deck settings for each emulator in particular are untested on
real hardware. See [AGENTS.md](AGENTS.md) §11 for the full list.

## Development

See [AGENTS.md](AGENTS.md).

## License

MIT
