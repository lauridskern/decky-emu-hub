/** Library tab: "Which emulator opens games" (choice.png), and the event ROM-Store listens for. */
import { chromium } from "playwright";
import path from "node:path";
import { fileURLToPath } from "node:url";
const here = path.dirname(fileURLToPath(import.meta.url));
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1280, height: 800 } });
const errors = [];
page.on("pageerror", (e) => errors.push(String(e)));
page.on("console", (m) => m.type() === "error" && errors.push(m.text()));
await page.goto(`file://${path.join(here, "index.html")}`);
await page.evaluate(() => {
  window.__choices = [];
  window.addEventListener("emuhub:emulator-choice", (e) => window.__choices.push(e.detail));
});
await page.locator("text=Library & BIOS").first().click();
const section = page.locator("text=Which emulator opens games");
await section.waitFor();
await section.scrollIntoViewIfNeeded();
await page.waitForTimeout(300);
await page.screenshot({ path: path.join(here, "choice.png") });
await page.locator("button", { hasText: /^Ryubing$/ }).click();
await page.locator("text=Opens in Ryubing").waitFor();
const events = await page.evaluate(() => window.__choices);
console.log("event for ROM-Store:", JSON.stringify(events));
console.log(`console errors: ${errors.length}`);
await browser.close();
process.exit(errors.length || events.length !== 1 ? 1 : 0);
