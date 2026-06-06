// Regenerate (from docs/): npm i playwright && npx playwright install chromium && node capture-screenshots.mjs
import { chromium } from "playwright";
import { mkdir } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const outDir = path.join(__dirname, "screenshots");
const baseUrl = process.env.RISKPULSE_URL || "http://localhost:8090/riskpulse-no-ml";

const shots = [
  { role: "owner", file: "owner-dashboard.png", wait: "#owner-headline" },
  { role: "manager", file: "manager-dashboard.png", wait: "#manager-headline" },
  { role: "technician", file: "technician-tasks.png", wait: "#tech-headline" },
];

await mkdir(outDir, { recursive: true });

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });

await page.goto(baseUrl, { waitUntil: "networkidle" });
await page.waitForSelector("#building", { state: "visible", timeout: 30000 });
await page.waitForFunction(
  () => !document.body.classList.contains("loading"),
  { timeout: 30000 },
);
await page.waitForSelector("#owner-headline", { state: "visible", timeout: 30000 });

for (const { role, file, wait } of shots) {
  await page.click(`.role-tab[data-role="${role}"]`);
  await page.waitForSelector(wait, { state: "visible", timeout: 30000 });
  if (role === "manager") {
    await page.waitForSelector("#risk-chart", { state: "visible", timeout: 30000 });
  }
  if (role === "technician") {
    await page.waitForSelector("#task-list .task-card, #task-list li", {
      timeout: 30000,
    });
  }
  await page.waitForTimeout(1200);
  await page.screenshot({
    path: path.join(outDir, file),
    fullPage: true,
  });
  console.log(`Wrote ${file}`);
}

await browser.close();
