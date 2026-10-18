// Druckt docs/loetplan/OwlBox-Loetplan.html als A4-quer-PDF (eine Seite pro Bauteil).
// Aufruf: node scripts/loetplan/render_pdf.cjs   (braucht playwright, lokal oder global)
const { chromium } = require("playwright");
const { readFileSync, existsSync } = require("node:fs");
const { resolve } = require("node:path");

const root = resolve(__dirname, "../..");
const html = readFileSync(resolve(root, "docs/loetplan/OwlBox-Loetplan.html"), "utf8");

(async () => {
  const exe = "/opt/pw-browsers/chromium";
  const browser = await chromium.launch(existsSync(exe) && !process.env.PLAYWRIGHT_BROWSERS_PATH ? { executablePath: exe } : {});
  const page = await browser.newPage();
  await page.emulateMedia({ media: "print", colorScheme: "light" });
  await page.setContent(
    `<!doctype html><html data-theme="light"><head><meta charset="utf-8"></head><body>${html}</body></html>`,
    { waitUntil: "networkidle" },
  );
  await page.pdf({ path: resolve(root, "docs/loetplan/OwlBox-Loetplan.pdf"), preferCSSPageSize: true, printBackground: true });
  await browser.close();
  console.log("geschrieben: docs/loetplan/OwlBox-Loetplan.pdf");
})();
