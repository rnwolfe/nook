// Generate the GitHub social-preview card (1280×640) — a proof-forward card showing the nook
// "vacancy board" (a real forward-availability calendar) beside a bounded JSON day entry, with a
// version-free kicker so it never goes stale. Outputs to BOTH public/social-card.png (shipped on
// the site) and .github/social-preview.png (upload manually in repo Settings → Social preview).
// Run: node scripts/gen-social.mjs
import { execSync } from "node:child_process";
import { mkdirSync, writeFileSync, rmSync, existsSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";
import sharp from "sharp";

const W = 1280, H = 640;

const __dir = dirname(fileURLToPath(import.meta.url));
const siteRoot = resolve(__dir, ".."); // site/scripts -> site
const repoRoot = resolve(siteRoot, ".."); // site -> repo root
const outPublic = resolve(siteRoot, "public", "social-card.png");
const outGithub = resolve(repoRoot, ".github", "social-preview.png");
const tmp = resolve(siteRoot, ".social-tmp");
mkdirSync(dirname(outPublic), { recursive: true });
mkdirSync(dirname(outGithub), { recursive: true });
mkdirSync(tmp, { recursive: true });

const CHROME =
  process.env.CHROME_BIN ||
  ["google-chrome", "google-chrome-stable", "chromium", "chromium-browser"].find((b) => {
    try { execSync(`command -v ${b}`, { stdio: "ignore" }); return true; } catch { return false; }
  });
if (!CHROME) { console.error("No Chrome/Chromium found (set CHROME_BIN)."); process.exit(1); }

// A compact availability board — the wedge, made literal.
const board = () => {
  const st = ["s","s","s","s","m","o","o","o","o","o","m","o","m","s","s","o","o","o","o","m","m","o","o","o","o","o","m","s"];
  return `<div class="cal">${st.map((s) => `<span class="c ${s}"></span>`).join("")}</div>`;
};

const html = `<!doctype html><html><head><meta charset="utf-8"/>
<style>
  @import url("https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,600;9..144,700&family=JetBrains+Mono:wght@400;500;700&display=swap");
  *{margin:0;box-sizing:border-box}
  html,body{width:${W}px;height:${H}px}
  body{font-family:"JetBrains Mono",monospace;color:#f7efe2;background:#17110d;position:relative;overflow:hidden;padding:52px 64px;display:flex;flex-direction:column}
  .glow{position:absolute;inset:0;background:
    radial-gradient(48rem 30rem at 92% -12%, rgba(224,122,95,.26), transparent 60%),
    radial-gradient(40rem 30rem at -8% 18%, rgba(238,177,90,.15), transparent 55%)}
  .grain{position:absolute;inset:0;opacity:.05;mix-blend-mode:overlay;
    background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='140' height='140'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='.82' numOctaves='2'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E")}
  .top{display:flex;align-items:center;justify-content:space-between;position:relative}
  .brand{display:flex;align-items:center;gap:14px}
  .brand svg{width:46px;height:46px}
  .brand b{font-family:"Fraunces",serif;font-size:36px;font-weight:600;letter-spacing:-.01em}
  .url{color:#eeb15a;font-size:22px}
  h1{font-family:"Fraunces",serif;position:relative;font-size:47px;font-weight:600;line-height:1.06;letter-spacing:-.02em;margin-top:20px;max-width:1160px}
  .grad{background:linear-gradient(100deg,#e07a5f,#eeb15a 72%);-webkit-background-clip:text;background-clip:text;color:transparent}
  .split{position:relative;display:grid;grid-template-columns:300px 1fr;gap:26px;margin-top:22px;align-items:stretch}
  .panel{border:1px solid #46362a;border-radius:16px;background:#1e1610;box-shadow:0 24px 60px -30px rgba(0,0,0,.8);overflow:hidden}
  .phead{padding:11px 16px;border-bottom:1px solid #46362a;color:#b39d86;font-size:14px;letter-spacing:.05em}
  .cal{padding:16px;display:grid;grid-template-columns:repeat(7,1fr);gap:8px}
  .c{aspect-ratio:1/1;border-radius:6px;border:1px solid #46362a;background:#30241b}
  .c.o{background:rgba(238,177,90,.2);border-color:#eeb15a}
  .c.m{background:rgba(224,122,95,.17);border-color:#e07a5f}
  .c.s{background:#2b2018}
  .code{font-size:17px;line-height:1.55;padding:16px 20px;white-space:pre}
  .p{color:#e07a5f}.k{color:#b39d86}.s2{color:#f2cf95}.n{color:#eeb15a}.on{color:#9fb089}
  .row{display:flex;align-items:center;justify-content:space-between;margin-top:auto;position:relative;padding-top:22px}
  .pills{display:flex;gap:12px;font-size:18px}
  .pill{border:1px solid #46362a;border-radius:999px;padding:7px 16px;color:#e4d7c5;background:#1e1610}
  .install{font-size:20px;color:#f7efe2;border:1px solid #46362a;border-radius:10px;padding:10px 16px;background:#1e1610}
  .install .d{color:#e07a5f}
  .legend{display:flex;gap:14px;padding:0 16px 14px;font-size:13px;color:#b39d86}
  .legend i{display:inline-block;width:11px;height:11px;border-radius:3px;vertical-align:-1px;margin-right:5px}
  .lo{background:rgba(238,177,90,.2);border:1px solid #eeb15a}.lm{background:rgba(224,122,95,.17);border:1px solid #e07a5f}.ls{background:#2b2018;border:1px solid #46362a}
</style></head><body>
  <div class="glow"></div>
  <div class="grain"></div>
  <div class="top">
    <div class="brand">
      <svg viewBox="0 0 32 32" fill="none"><linearGradient id="g" x1="4" y1="30" x2="28" y2="4" gradientUnits="userSpaceOnUse"><stop stop-color="#e07a5f"/><stop offset=".6" stop-color="#ef9d7f"/><stop offset="1" stop-color="#eeb15a"/></linearGradient>
      <path d="M16 3.5 4 13.2c-.5.4-.8 1-.8 1.6V15h3.2l9.6-7.7 9.6 7.7h3.2v-.2c0-.6-.3-1.2-.8-1.6L16 3.5Z" fill="url(#g)"/>
      <path d="M7 16.4v10.1c0 .8.6 1.5 1.5 1.5H12v-6.2a4 4 0 0 1 8 0V28h3.5c.8 0 1.5-.7 1.5-1.5V16.4L16 9.7 7 16.4Z" fill="url(#g)" opacity=".82"/>
      <circle cx="16" cy="17.6" r="2.15" fill="#17110d"/></svg>
      <b>nook</b>
    </div>
    <div class="url">nookcli.sh</div>
  </div>

  <h1>The Airbnb availability calendar<br/>your agent can <span class="grad">actually read</span>.</h1>

  <div class="split">
    <div class="panel">
      <div class="phead">availability · aug 2026</div>
      ${board()}
      <div class="legend"><span><i class="lo"></i>open</span><span><i class="lm"></i>min-nights</span><span><i class="ls"></i>booked</span></div>
    </div>
    <div class="panel">
      <div class="phead">read-only · JSON-first · no auth · booking excluded</div>
<div class="code"><span class="p">$</span> nook availability <span class="n">1234</span> --months 3 --json
{
  <span class="k">"schemaVersion"</span>: <span class="n">1</span>,
  <span class="k">"scope"</span>: { <span class="k">"auth"</span>: <span class="s2">"none"</span>, <span class="k">"corpus"</span>: <span class="s2">"public-logged-out"</span> },
  <span class="k">"data"</span>: [ { <span class="k">"date"</span>: <span class="s2">"2026-08-16"</span>, <span class="k">"available"</span>: <span class="on">true</span>,
    <span class="k">"minNights"</span>: <span class="n">2</span>, <span class="k">"price"</span>: <span class="n">116</span> } ],
  <span class="k">"nextCursor"</span>: <span class="s2">null</span>
}</div>
    </div>
  </div>

  <div class="row">
    <div class="pills">
      <span class="pill">forward availability</span><span class="pill">no evasion</span><span class="pill">MIT</span>
    </div>
    <div class="install"><span class="d">$</span> uvx nook</div>
  </div>
</body></html>`;

const f = resolve(tmp, "social.html");
const shot = resolve(tmp, "social.raw.png");
writeFileSync(f, html);
execSync(
  `"${CHROME}" --headless=new --no-sandbox --disable-gpu --hide-scrollbars ` +
    `--force-device-scale-factor=1 --window-size=${W},${H * 2} --screenshot="${shot}" "file://${f}"`,
  { stdio: "ignore" }
);
if (!existsSync(shot)) { console.error("failed to render"); process.exit(1); }
await sharp(shot).extract({ left: 0, top: 0, width: W, height: H }).png().toFile(outPublic);
await sharp(shot).extract({ left: 0, top: 0, width: W, height: H }).png().toFile(outGithub);
rmSync(tmp, { recursive: true, force: true });
console.log("social card →", outPublic, "+", outGithub);
