/**
 * Emu Hub's styles, rendered into the page by <Styles /> (Decky loads no CSS).
 *
 * Same rules as ROM-Store (AGENTS.md §10): built for 1280 x 800 at arm's
 * length, nothing under 12px, anything focusable at least 38px tall, focus is
 * always a white ring (blue means "selected" or "the main action"), no
 * transforms, filters or blurred shadows on anything in a list, nothing that
 * animates while idle, no scrollbars.
 */
export const CSS = `
.ed-app {
  --ed-bg: #0b0e13;
  --ed-surface: rgba(255, 255, 255, 0.055);
  --ed-surface-2: rgba(255, 255, 255, 0.1);
  --ed-line: rgba(255, 255, 255, 0.08);
  --ed-text: #f1f3f6;
  --ed-text-2: #aab3be;
  --ed-text-3: #747e8b;
  --ed-accent: #3d9bff;
  --ed-accent-2: #6f6bff;
  --ed-good: #6ad37a;
  --ed-warn: #f3bd55;
  --ed-bad: #ff7d6b;
  --ed-focus: #ffffff;
  --ed-pad: 32px;

  position: fixed;
  top: var(--ed-chrome-top, var(--basicui-header-height, 40px));
  bottom: var(--ed-chrome-bottom, 40px);
  left: 0; right: 0;
  display: flex; flex-direction: column; overflow: hidden;
  background:
    radial-gradient(1000px 480px at 6% -14%, rgba(106, 211, 122, 0.10), rgba(106, 211, 122, 0) 60%),
    radial-gradient(900px 460px at 104% -6%, rgba(61, 155, 255, 0.11), rgba(61, 155, 255, 0) 58%),
    var(--ed-bg);
  color: var(--ed-text);
  font-family: "Motiva Sans", "Noto Sans", sans-serif;
  font-size: 14px; line-height: 1.35;
  user-select: none;
}
.ed-app [class^="ed-"], .ed-app [class*=" ed-"] { box-sizing: border-box; }
.ed-app, .ed-app * { scrollbar-width: none; }
.ed-app ::-webkit-scrollbar { display: none; width: 0; height: 0; }

/* ------------------------------------------------------------------ focus */
.ed-app .ed-f { outline: none; cursor: pointer; }
.ed-app .ed-f.is-focus, .ed-app .ed-f.gpfocus, .ed-app .ed-f:focus-visible,
.ed-app .ed-btn.gpfocus, .ed-app .ed-btn:focus-visible {
  outline: 3px solid var(--ed-focus); outline-offset: 2px;
}
.ed-app .ed-dd .gpfocus, .ed-app .ed-dd :focus-visible {
  outline: 3px solid var(--ed-focus) !important; outline-offset: 2px; border-radius: 10px; box-shadow: none !important;
}

/* ------------------------------------------------------------- small parts */
.ed-glyph {
  display: inline-flex; align-items: center; justify-content: center; flex: 0 0 auto;
  min-width: 26px; height: 20px; padding: 0 5px; border-radius: 6px;
  background: rgba(255, 255, 255, 0.14); color: var(--ed-text-2);
  font-size: 11px; font-weight: 800; letter-spacing: 0.3px; line-height: 1;
}
.ed-glyph.round { min-width: 20px; width: 20px; padding: 0; border-radius: 50%; }
.ed-h2 { margin: 0; font-size: 18px; line-height: 1.2; font-weight: 800; color: var(--ed-text); }
.ed-muted { color: var(--ed-text-3); }
.ed-path { font-family: monospace; font-size: 12.5px; color: var(--ed-text-2); word-break: break-all; }
.ed-good { color: var(--ed-good); }
.ed-warn { color: var(--ed-warn); }
.ed-bad { color: var(--ed-bad); }

.ed-app .ed-btn {
  display: inline-flex !important; align-items: center; justify-content: center; gap: 8px;
  flex: 0 0 auto !important; width: auto !important; min-width: 0 !important;
  height: 40px !important; padding: 0 18px !important;
  border: none !important; border-radius: 10px !important;
  background: #ffffff !important; color: #0b0e13 !important;
  font-size: 14px !important; font-weight: 700 !important; line-height: 1 !important;
  white-space: nowrap; cursor: pointer;
}
.ed-app .ed-btn.ghost { background: var(--ed-surface-2) !important; color: var(--ed-text) !important; }
.ed-app .ed-btn.danger { background: rgba(255, 125, 107, 0.2) !important; color: #ffab9d !important; }
.ed-app .ed-btn:disabled { opacity: 0.45; cursor: default; }

.ed-switch { position: relative; flex: 0 0 auto; width: 46px; height: 26px; border-radius: 13px; background: rgba(255, 255, 255, 0.18); }
.ed-switch.on { background: var(--ed-accent); }
.ed-switch > span { position: absolute; top: 3px; left: 3px; width: 20px; height: 20px; border-radius: 50%; background: #fff; }
.ed-switch.on > span { left: 23px; }

.ed-progress { height: 6px; border-radius: 3px; background: rgba(255, 255, 255, 0.1); overflow: hidden; }
.ed-progress > div { height: 100%; border-radius: 3px; background: linear-gradient(90deg, var(--ed-accent), var(--ed-accent-2)); transition: width 200ms linear; }

.ed-spinner {
  flex: 0 0 auto; width: 16px; height: 16px; border-radius: 50%;
  border: 2px solid rgba(255, 255, 255, 0.18); border-top-color: var(--ed-accent);
  animation: ed-spin 700ms linear infinite;
}
@keyframes ed-spin { to { transform: rotate(360deg); } }
@keyframes ed-fade { from { opacity: 0; } to { opacity: 1; } }

.ed-chip {
  display: inline-flex; align-items: center; gap: 6px; flex: 0 0 auto;
  height: 26px; padding: 0 10px; border-radius: 13px;
  background: var(--ed-surface-2); color: var(--ed-text-2);
  font-size: 12.5px; font-weight: 800; white-space: nowrap;
}
.ed-chip.update { background: rgba(61, 155, 255, 0.2); color: #9ccbff; }
.ed-chip.ok { background: rgba(106, 211, 122, 0.16); color: #9fe3a9; }
.ed-chip.warn { background: rgba(243, 189, 85, 0.16); color: #f6d48c; }
.ed-chip.bad { background: rgba(255, 125, 107, 0.18); color: #ffab9d; }

/* ----------------------------------------------------------------- shell */
.ed-body { flex: 1 1 auto; min-height: 0; display: flex; flex-direction: column; }
.ed-top {
  flex: 0 0 auto; display: flex; align-items: center; gap: 22px;
  height: 60px; padding: 0 var(--ed-pad); border-bottom: 1px solid var(--ed-line);
}
.ed-brand { display: flex; align-items: center; gap: 10px; flex: 0 0 auto; font-size: 16px; font-weight: 800; letter-spacing: -0.2px; }
.ed-brand-mark {
  width: 30px; height: 30px; border-radius: 9px;
  display: flex; align-items: center; justify-content: center;
  background: linear-gradient(135deg, var(--ed-good), var(--ed-accent)); color: #0b0e13; font-size: 15px;
}
.ed-tabs { display: flex; align-items: center; gap: 4px; flex: 0 0 auto; }
.ed-tabs > .ed-glyph:first-child { margin-right: 6px; }
.ed-tabs > .ed-glyph:last-child { margin-left: 6px; }
.ed-tab {
  position: relative; display: flex; align-items: center; gap: 8px;
  height: 38px; padding: 0 16px; border-radius: 19px;
  font-size: 15px; font-weight: 700; color: var(--ed-text-2); white-space: nowrap;
}
.ed-tab.active { background: var(--ed-surface-2); color: #fff; }
.ed-tab-badge {
  min-width: 20px; height: 20px; padding: 0 6px; border-radius: 10px;
  display: inline-flex; align-items: center; justify-content: center;
  background: var(--ed-accent); color: #fff; font-size: 12px; font-weight: 800;
}
.ed-top-status { margin-left: auto; display: flex; align-items: center; gap: 10px; min-width: 0; font-size: 13px; color: var(--ed-text-3); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

.ed-view {
  flex: 1 1 auto; min-height: 0; display: flex; flex-direction: column; gap: 22px;
  overflow-y: auto; overscroll-behavior: contain;
  padding: 22px var(--ed-pad) 40px; scroll-padding: 22px 0 32px;
  animation: ed-fade 140ms ease-out;
}
.ed-view-head { display: flex; align-items: center; gap: 12px; flex: 0 0 auto; min-height: 40px; }
.ed-view-head .ed-h2 { flex: 1 1 auto; min-width: 0; }
.ed-section { display: flex; flex-direction: column; gap: 10px; min-width: 0; }
.ed-section-title { font-size: 12px; font-weight: 800; letter-spacing: 1.4px; text-transform: uppercase; color: var(--ed-text-3); }
.ed-note { margin: 0; max-width: 78ch; font-size: 13.5px; line-height: 1.5; color: var(--ed-text-2); }
.ed-banner {
  display: flex; align-items: center; gap: 14px; flex: 0 0 auto;
  padding: 12px 16px; border-radius: 12px; background: var(--ed-surface); color: var(--ed-text-2); font-size: 13.5px;
}
.ed-banner.warn { background: rgba(243, 189, 85, 0.12); color: #f6d48c; }

/* --------------------------------------------------------- emulator cards */
.ed-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; }
.ed-emu {
  position: relative; overflow: hidden; min-width: 0;
  display: flex; align-items: center; gap: 14px;
  height: 84px; padding: 0 16px 0 14px; border-radius: 14px;
  background: var(--ed-surface);
}
.ed-emu.is-focus, .ed-emu:hover { background: var(--ed-surface-2); }
.ed-emu-icon {
  flex: 0 0 auto; width: 52px; height: 52px; border-radius: 12px;
  display: flex; align-items: center; justify-content: center;
  background: var(--ed-tint, #3a4352); color: #fff; font-size: 17px; font-weight: 800; letter-spacing: -0.3px;
}
.ed-emu.off .ed-emu-icon { opacity: 0.55; }
.ed-emu-text { flex: 1 1 auto; min-width: 0; display: flex; flex-direction: column; gap: 3px; }
.ed-emu-name { font-size: 16px; font-weight: 800; color: var(--ed-text); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.ed-emu-sub, .ed-emu-status { font-size: 13px; color: var(--ed-text-3); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.ed-emu-status { color: var(--ed-text-2); }
.ed-emu-side { flex: 0 0 auto; display: flex; align-items: center; gap: 8px; }
.ed-emu-bar { display: flex; align-items: center; height: 17px; }
.ed-emu-bar > .ed-progress { flex: 1 1 auto; }

/* ----------------------------------------------------------------- rows */
.ed-rows { display: flex; flex-direction: column; gap: 6px; }
.ed-row {
  display: flex; align-items: center; gap: 16px; min-height: 58px;
  padding: 10px 16px; border-radius: 12px; background: var(--ed-surface);
}
.ed-row.is-focus { background: var(--ed-surface-2); }
.ed-row-text { flex: 1 1 auto; min-width: 0; }
.ed-row-label { font-size: 15px; font-weight: 700; color: var(--ed-text); }
.ed-row-hint { margin-top: 3px; max-width: 80ch; font-size: 13px; line-height: 1.45; color: var(--ed-text-3); }
.ed-row-side { flex: 0 0 auto; display: flex; align-items: center; gap: 10px; font-size: 13.5px; font-weight: 700; color: var(--ed-text-2); }
.ed-row-control { flex: 0 0 300px; min-width: 0; }
.ed-row-control > * { margin: 0 !important; }
.ed-row-control label:empty { display: none !important; }
.ed-row-control input {
  width: 100% !important; height: 40px !important; padding: 0 14px !important;
  border: 1px solid transparent !important; border-radius: 10px !important;
  background: rgba(0, 0, 0, 0.3) !important; color: var(--ed-text) !important; font-size: 14px !important;
}
.ed-row-control input:focus, .ed-row-control input.gpfocus { border-color: var(--ed-focus) !important; outline: 2px solid var(--ed-focus); }
.ed-actions { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }

/* Dropdowns: Steam draws its own; this is the preview's stand-in. */
.ed-app select {
  appearance: none; -webkit-appearance: none; width: 100%; height: 40px; padding: 0 14px;
  border: none; border-radius: 10px; outline: none; background: var(--ed-surface-2); color: var(--ed-text);
  font: 600 14px "Motiva Sans", "Noto Sans", sans-serif; cursor: pointer;
}
.ed-app select.gpfocus, .ed-app select:focus-visible { outline: 3px solid var(--ed-focus); outline-offset: 2px; }

/* --------------------------------------------------------- actions sheet */
.ed-scrim { position: absolute; inset: 0; z-index: 20; background: rgba(4, 6, 9, 0.72); display: flex; justify-content: flex-end; animation: ed-fade 120ms ease-out; }
.ed-sheet {
  width: 460px; max-width: 100%; height: 100%; overflow-y: auto; overscroll-behavior: contain;
  display: flex; flex-direction: column; gap: 18px;
  padding: 26px 28px 32px; background: #121720; border-left: 1px solid var(--ed-line);
  scroll-padding: 20px 0 28px;
}
.ed-sheet-head { display: flex; align-items: center; gap: 14px; }
.ed-sheet-head .ed-emu-icon { width: 56px; height: 56px; }
.ed-sheet-title { font-size: 22px; font-weight: 800; letter-spacing: -0.3px; }
.ed-facts { display: grid; grid-template-columns: auto minmax(0, 1fr); gap: 6px 16px; font-size: 13.5px; }
.ed-facts dt { color: var(--ed-text-3); }
.ed-facts dd { margin: 0; color: var(--ed-text); min-width: 0; overflow-wrap: anywhere; }
.ed-menu { display: flex; flex-direction: column; gap: 6px; }
.ed-menu-item {
  display: flex; align-items: center; gap: 12px; min-height: 52px;
  padding: 8px 16px; border-radius: 12px; background: var(--ed-surface);
}
.ed-menu-item.is-focus { background: var(--ed-surface-2); }
.ed-menu-item.primary { background: rgba(61, 155, 255, 0.22); }
.ed-menu-item.primary.is-focus { background: rgba(61, 155, 255, 0.34); }
.ed-menu-item.danger .ed-menu-label { color: #ffab9d; }
.ed-menu-item svg { flex: 0 0 auto; font-size: 16px; color: var(--ed-text-2); }
.ed-menu-label { font-size: 15px; font-weight: 700; }
.ed-menu-hint { font-size: 12.5px; color: var(--ed-text-3); }
.ed-menu-text { display: flex; flex-direction: column; gap: 2px; min-width: 0; }
.ed-sheet-msg { padding: 10px 14px; border-radius: 10px; background: var(--ed-surface); font-size: 13.5px; color: var(--ed-text-2); }
.ed-sheet-msg.bad { background: rgba(255, 125, 107, 0.14); color: #ffab9d; }
.ed-sheet-msg.good { background: rgba(106, 211, 122, 0.12); color: #9fe3a9; }

.ed-error-screen { padding: 40px; color: var(--ed-text); }
.ed-error-screen pre { white-space: pre-wrap; color: var(--ed-bad); }
`;
