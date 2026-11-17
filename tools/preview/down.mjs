/** A backend that never loaded: the Emulators and Settings tabs say so (down.png). */
import { chromium } from "playwright";
import path from "node:path";
import { fileURLToPath } from "node:url";
const here = path.dirname(fileURLToPath(import.meta.url));
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1280, height: 800 } });
await page.goto(`file://${path.join(here, "index.html")}?down`);
await page.locator("text=backend did not answer").first().waitFor({ timeout: 5000 });
await page.waitForTimeout(600);
await page.screenshot({ path: path.join(here, "down.png") });
console.log("emulators tab: error shown, retry buttons:", await page.locator("text=Retry").count());
await browser.close();
