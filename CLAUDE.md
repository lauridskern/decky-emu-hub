@AGENTS.md

# Claude notes

The project brief is `AGENTS.md`, imported above. Short version:

- Emu Hub installs and updates **emulators** (open-source programs from
  their own GitHub/Forgejo releases and Flathub) and sets them up for the
  Deck. It never downloads games, BIOS files, firmware or keys; `AGENTS.md`
  §2 lists the lines to keep.
- Build: `npm run build` · typecheck: `npm run typecheck` · backend:
  `python3 -m compileall -q backend main.py` · tests:
  `python3 -m unittest discover -s tests`.
- Live source check: `python3 tools/check_sources.py`.
- UI: `cd tools/preview && npm install` (once), then `npm run shots`.
- Release: tag `vX.Y.Z`, wait for Actions, then
  `python3 tools/verify_package.py <downloaded zip>` must print PASS.
