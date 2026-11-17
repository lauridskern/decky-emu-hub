/**
 * Screenshots of every screen, taken the way a Deck is used: with the pad.
 * Keys stand in for buttons (see mock-ui.tsx): arrows = d-pad, Enter = A,
 * Escape = B, x / y, q / e = L1 / R1.
 *
 * Every step checks where focus ended up; a step that leaves focus somewhere
 * unexpected is a failure. Also fails on console errors, on anything focusable
 * shorter than 38px, and on a visible scrollbar. Writes emulators.png,
 * actions.png, updates.png, library.png, settings.png.
 */
import { chromium } from "playwright";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const out = (name) => path.join(here, name);
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1280, height: 800 }, deviceScaleFactor: 1 });
const errors = [];
page.on("console", (m) => m.type() === "error" && errors.push(m.text()));
page.on("pageerror", (e) => errors.push(String(e)));
// Keep the mock's running job where it is, so screenshots are repeatable.
await page.addInitScript(() => { window.__FREEZE = true; });

const failures = [];
const where = () =>
  page.evaluate(() => {
    const el = document.activeElement;
    if (!el || el === document.body) return "(nothing)";
    const cls = typeof el.className === "string" ? el.className.split(" ").filter((c) => c.startsWith("ed-")).join(".") : "";
    const tag = el.getAttribute("data-emu") || el.getAttribute("data-tab") || "";
    return `${el.tagName.toLowerCase()}${cls ? "." + cls : ""}${tag ? `[${tag}]` : ""}`;
  });
const expectFocus = async (step, selector) => {
  const ok = await page.evaluate((sel) => !!document.activeElement?.closest(sel), selector);
  const at = await where();
  console.log(`${ok ? "ok  " : "FAIL"} ${step.padEnd(40)} focus: ${at}`);
  if (!ok) failures.push(`${step}: expected ${selector}, focus is on ${at}`);
};
const key = async (name, wait = 300) => {
  await page.keyboard.press(name);
  await page.waitForTimeout(wait);
};
const checkSizes = async (screen) => {
  const small = await page.evaluate(() =>
    Array.from(document.querySelectorAll('[data-nav="target"]'))
      .filter((el) => !el.closest("[data-nav-off]"))
      .map((el) => ({ el, r: el.getBoundingClientRect() }))
      .filter(({ r }) => r.width > 0 && r.height > 0 && r.height < 38)
      .map(({ el, r }) => `${el.tagName.toLowerCase()}.${String(el.className).split(" ")[0]} ${Math.round(r.height)}px`),
  );
  if (small.length) failures.push(`${screen}: focusable under 38px: ${small.join(", ")}`);
  const bars = await page.evaluate(() =>
    Array.from(document.querySelectorAll(".ed-app *")).filter((el) => !/^(INPUT|SELECT|TEXTAREA)$/.test(el.tagName)).filter((el) => {
      const style = getComputedStyle(el);
      const borders = parseFloat(style.borderLeftWidth) + parseFloat(style.borderRightWidth);
      return el.offsetWidth - el.clientWidth - borders > 0.5 && style.overflowY !== "visible";
    }).length,
  );
  if (bars) failures.push(`${screen}: ${bars} element(s) draw a scrollbar`);
};

await page.goto(`file://${path.join(here, "index.html")}`);
await page.locator(".ed-emu").first().waitFor();
await page.waitForTimeout(500);

// --- Emulators
await expectFocus("page opens on the first emulator", ".ed-emu");
const perRow = await page.evaluate(() => {
  const cards = Array.from(document.querySelectorAll(".ed-grid"))[0]?.children ?? [];
  const top = cards[0]?.getBoundingClientRect().top;
  return Array.from(cards).filter((c) => c.getBoundingClientRect().top === top).length;
});
console.log(`     cards per row: ${perRow}`);
await checkSizes("emulators");
await page.screenshot({ path: out("emulators.png") });
await key("ArrowRight");
await expectFocus("right to the next card", '.ed-emu[data-emu="dolphin"]');
await key("ArrowDown");
await expectFocus("down a row", ".ed-emu");
await key("ArrowLeft");
await key("ArrowUp");
await key("ArrowUp");
await expectFocus("up to the tabs", ".ed-tab");
await key("ArrowDown");
await expectFocus("back down into the grid", ".ed-emu");

// --- the actions sheet (X)
await page.evaluate(() => document.querySelector('.ed-emu[data-emu="pcsx2"]')?.focus());
const historyBefore = await page.evaluate(() => history.length);
await key("x", 400);
const historyOpen = await page.evaluate(() => history.length);
if (historyOpen !== historyBefore + 1) failures.push(`opening the sheet grew history by ${historyOpen - historyBefore}, not 1`);
await expectFocus("X opens the actions", ".ed-sheet .ed-menu-item");
const behind = await page.evaluate(() => !!document.querySelector(".ed-body[data-nav-off]"));
if (!behind) failures.push("the page behind the sheet still takes focus");
await key("ArrowDown");
await key("ArrowDown");
await expectFocus("down through the actions", ".ed-sheet .ed-menu-item");
await checkSizes("actions");
await page.screenshot({ path: out("actions.png") });
for (let i = 0; i < 8; i++) await key("ArrowDown", 120);
await key("Enter", 300);
await expectFocus("Uninstall asks first, Keep focused", ".ed-sheet .ed-menu-item");
const keep = await page.evaluate(() => document.activeElement?.textContent ?? "");
if (!keep.includes("Keep")) failures.push(`uninstall question focuses "${keep}", not Keep`);
await key("Enter", 300);
await key("Escape", 400);
await expectFocus("B closes it, focus back on the card", '.ed-emu[data-emu="pcsx2"]');
for (let round = 0; round < 3; round++) {
  await key("x", 300);
  await key("Escape", 300);
}
const historyAfter = await page.evaluate(() => history.length);
console.log(`     history: ${historyBefore} before, ${historyOpen} with the sheet, ${historyAfter} after 4 open/close rounds`);
if (historyAfter > historyOpen) failures.push(`history grows with each open/close (${historyAfter})`);

// --- tabs with R1
await key("e", 500);
await expectFocus("R1 opens Updates", ".ed-view .ed-f");
await checkSizes("updates");
await page.screenshot({ path: out("updates.png") });
await key("e", 600);
await expectFocus("R1 opens Library & BIOS", ".ed-view .ed-f");
await checkSizes("library");
await page.screenshot({ path: out("library.png") });
await key("e", 600);
await expectFocus("R1 opens Settings", ".ed-view .ed-f");
await checkSizes("settings");
await page.screenshot({ path: out("settings.png") });
await key("Enter", 300);
const switched = await page.evaluate(() => document.querySelector(".ed-switch")?.classList.contains("on"));
if (switched) failures.push("A on the first setting did not switch it off");
await key("Escape", 500);
await expectFocus("B goes back to Emulators", ".ed-emu");
const tab = await page.evaluate(() => document.querySelector(".ed-tab.active")?.getAttribute("data-tab"));
if (tab !== "emulators") failures.push(`after B the active tab is ${tab}`);

// --- install from a card (A)
await page.evaluate(() => { window.__FREEZE = false; document.querySelector('.ed-emu[data-emu="cemu"]')?.focus(); });
await key("Enter", 400);
const started = await page.evaluate(() => document.querySelector('.ed-emu[data-emu="cemu"] .ed-chip')?.textContent);
console.log(`     A on Cemu: chip says "${started}"`);
if (!started || !/%|Queued/.test(started)) failures.push(`A on a card did not start an install (chip: ${started})`);
await page.waitForTimeout(9000);
const done = await page.evaluate(() => document.querySelector('.ed-emu[data-emu="cemu"] .ed-chip')?.textContent);
console.log(`     after polling: chip says "${done}"`);
if (done !== "Installed") failures.push(`install did not finish through polling (chip: ${done})`);

console.log(`\nconsole errors: ${errors.length ? errors.join(" | ") : 0}`);
console.log(`failures: ${failures.length ? "\n  " + failures.join("\n  ") : "none"}`);
await browser.close();
process.exit(failures.length || errors.length ? 1 : 0);
