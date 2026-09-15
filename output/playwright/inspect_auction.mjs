import { createRequire } from "node:module";
const require = createRequire(import.meta.url);
const { chromium } = require("/tmp/cursor-sandbox-cache/0850849d51a44b46b0419a84b862bc50/npm/_npx/31e32ef8478fbf80/node_modules/playwright-core/index.js");
import fs from "node:fs";

const session = process.env.PORTAL_SESSION;
const out = "/home/alex/portal_kg-1/output/playwright";
const browser = await chromium.launch({
  executablePath: "/usr/bin/chromium",
  args: ["--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage"],
  headless: true,
});
const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
await context.addCookies([
  { name: "sessionid", value: session, url: "http://127.0.0.1:8011" },
]);
const page = await context.newPage();
const consoleLogs = [];
page.on("console", (msg) => consoleLogs.push({ type: msg.type(), text: msg.text() }));
page.on("pageerror", (err) => consoleLogs.push({ type: "pageerror", text: String(err) }));
const failed = [];
page.on("requestfailed", (req) => failed.push({ url: req.url(), err: req.failure()?.errorText }));

await page.goto("http://127.0.0.1:8011/auction/", { waitUntil: "networkidle", timeout: 60000 });
await page.waitForTimeout(800);

const report = await page.evaluate(() => {
  const floor = document.querySelector(".auction-floor");
  const cs = floor ? getComputedStyle(floor) : null;
  const header = document.querySelector(".af-header");
  const rail = document.querySelector(".af-rail");
  const row = document.querySelector(".af-row");
  const btn = document.querySelector(".af-btn--primary");
  const issues = [];
  if (!floor) issues.push("missing .auction-floor");
  if (cs && cs.backgroundColor === "rgba(0, 0, 0, 0)") issues.push("transparent floor bg");
  const overflowX = document.documentElement.scrollWidth > window.innerWidth + 2;
  if (overflowX) issues.push("horizontal overflow " + document.documentElement.scrollWidth + ">" + window.innerWidth);
  const cssLink = [...document.querySelectorAll('link[rel="stylesheet"]')].find((l) => l.href.includes("auction-floor.css"));
  if (!cssLink) issues.push("auction-floor.css not linked");
  const lowContrast = [];
  document.querySelectorAll(".auction-floor .af-title, .auction-floor .af-stat__value, .auction-floor .af-kicker").forEach((el) => {
    const s = getComputedStyle(el);
    lowContrast.push({ sel: el.className, color: s.color, bg: s.backgroundColor, font: s.fontFamily });
  });
  return {
    title: document.title,
    url: location.href,
    hasFloor: !!floor,
    floorBg: cs && cs.backgroundColor,
    floorColor: cs && cs.color,
    floorRadius: cs && cs.borderRadius,
    headerRadius: header && getComputedStyle(header).borderRadius,
    headerBg: header && getComputedStyle(header).backgroundColor,
    railRadius: rail && getComputedStyle(rail).borderRadius,
    rowCount: document.querySelectorAll(".af-row").length,
    empty: !!document.querySelector(".af-empty"),
    btnRadius: btn && getComputedStyle(btn).borderRadius,
    btnBg: btn && getComputedStyle(btn).backgroundColor,
    cssHref: cssLink && cssLink.href,
    jsPresent: !!document.querySelector('script[src*="auction-floor.js"]'),
    combos: document.querySelectorAll("[data-af-combo]").length,
    issues,
    lowContrast,
  };
});

await page.screenshot({ path: `${out}/desktop.png`, fullPage: true });

const comboBtn = page.locator("[data-af-combo] .af-combo__btn").first();
if (await comboBtn.count()) {
  await comboBtn.click();
  await page.waitForTimeout(300);
  report.comboOpen = await page.evaluate(() => !!document.querySelector(".af-combo.is-open"));
  await page.screenshot({ path: `${out}/desktop-combo.png` });
  await page.keyboard.press("Escape");
}

await page.setViewportSize({ width: 375, height: 812 });
await page.waitForTimeout(400);
report.mobileOverflow = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth + 2);
report.filtersBtnVisible = await page.locator("[data-af-open-filters]").evaluate((el) => getComputedStyle(el).display !== "none");
await page.screenshot({ path: `${out}/mobile.png`, fullPage: true });
if (report.filtersBtnVisible) {
  await page.locator("[data-af-open-filters]").click();
  await page.waitForTimeout(400);
  report.sheetOpen = await page.evaluate(() => document.querySelector(".auction-floor")?.classList.contains("is-filters-open"));
  await page.screenshot({ path: `${out}/mobile-filters.png` });
}

fs.writeFileSync(`${out}/report.json`, JSON.stringify({ report, consoleLogs, failed }, null, 2));
console.log(JSON.stringify({ report, consoleLogs, failed }, null, 2));
await browser.close();
