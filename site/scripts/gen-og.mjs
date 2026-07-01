// Generate 1200×630 OG/social cards in the nook "vacancy board" brand style, one per page + a
// default. Renders an HTML template (top-anchored absolute layout so nothing drifts) with headless
// Chrome, then crops the top 1200×630 with sharp (render-tall, crop-top avoids Chrome viewport
// rounding/scrollbar artifacts). Run: `node scripts/gen-og.mjs`.
import { execSync } from "node:child_process";
import { mkdirSync, writeFileSync, rmSync, existsSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";
import sharp from "sharp";

const W = 1200, H = 630;

const __dir = dirname(fileURLToPath(import.meta.url));
const root = resolve(__dir, "..");
const outDir = resolve(root, "public/og");
const tmpDir = resolve(root, ".og-tmp");
mkdirSync(outDir, { recursive: true });
mkdirSync(tmpDir, { recursive: true });

const CHROME =
  process.env.CHROME_BIN ||
  ["google-chrome", "google-chrome-stable", "chromium", "chromium-browser"].find((b) => {
    try { execSync(`command -v ${b}`, { stdio: "ignore" }); return true; } catch { return false; }
  });
if (!CHROME) { console.error("No Chrome/Chromium found (set CHROME_BIN)."); process.exit(1); }

const pages = [
  { slug: "default", title: "The Airbnb availability calendar your agent can read", sub: "Read-only · JSON-first · booking excluded by design" },
  { slug: "index", title: "The Airbnb availability calendar your agent can read", sub: "A free forward calendar — per-day available / min-nights / price" },
  { slug: "introduction", title: "Introduction", sub: "Read-only, JSON-first Airbnb search + availability for agents" },
  { slug: "getting-started-install", title: "Install", sub: "uvx nook · uv tool install nook · pipx install nook" },
  { slug: "getting-started-quickstart", title: "Quickstart", sub: "search → availability → listing, as bounded JSON" },
  { slug: "getting-started-no-auth", title: "No auth", sub: "Public, logged-out reads — scope says so on every response" },
  { slug: "guides-searching", title: "Searching listings", sub: "dates · price · guests · room-type · amenities · bbox" },
  { slug: "guides-availability", title: "Checking availability", sub: "The wedge — per-day available / min-nights / price" },
  { slug: "guides-listing-details", title: "Listing details", sub: "Full structured detail for one listing" },
  { slug: "guides-place-resolution", title: "Place resolution", sub: "a location string → placeId · coordinates · bbox" },
  { slug: "guides-reviews", title: "Reviews", sub: "Recent reviews — free text fenced untrusted" },
  { slug: "guides-bounding-output", title: "Bounding output", sub: "--limit and --select keep responses in budget" },
  { slug: "guides-pagination", title: "Pagination", sub: "an opaque cursor, echoed back as nextCursor" },
  { slug: "concepts-output-envelope", title: "The output envelope", sub: "schemaVersion · scope · data · nextCursor · meta" },
  { slug: "concepts-read-only", title: "Read-only & booking-excluded", sub: "Mutation flags are inert · no transactions, by design" },
  { slug: "concepts-legitimacy", title: "The legitimacy boundary", sub: "Public, logged-out, personal scale · if blocked, stop" },
  { slug: "concepts-etiquette", title: "Etiquette & circuit-breaker", sub: "Self-throttle · circuit-break · no evasion" },
  { slug: "reference-commands", title: "Command reference", sub: "search · availability · listing · reviews · schema · agent" },
  { slug: "reference-flags", title: "Flags", sub: "--json · --limit · --select · --cursor · --currency" },
  { slug: "reference-exit-codes", title: "Exit codes", sub: "0 ok · 3 empty · 5 not found · 7 rate-limited · 20 drift" },
  { slug: "reference-schema-agent", title: "schema & agent", sub: "Discover the contract straight from the binary" },
  { slug: "reference-version-check", title: "version --check", sub: "Report an available upgrade — never self-update" },
  { slug: "troubleshooting-rate-limited", title: "Rate-limited · exit 7", sub: "Back off — don't retry into a block" },
  { slug: "troubleshooting-upstream-drift", title: "Upstream drift · exit 20", sub: "Airbnb changed its internals — update nook" },
];

// A faint mini vacancy-board as brand texture, top-right.
const miniBoard = () => {
  const states = ["s", "s", "o", "o", "o", "m", "o", "o", "o", "m", "s", "o", "o", "o", "m", "m", "o", "o", "o", "o", "s"];
  return `<div class="mini">${states.map((s) => `<span class="mc ${s}"></span>`).join("")}</div>`;
};

const card = (title, sub) => `<!doctype html><html><head><meta charset="utf-8"/>
<style>
  @import url("https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,600;9..144,700&family=JetBrains+Mono:wght@500;700&display=swap");
  *{margin:0;box-sizing:border-box}
  html,body{width:${W}px;height:${H}px}
  body{font-family:"JetBrains Mono",monospace;color:#f7efe2;background:#17110d;position:relative;overflow:hidden}
  .glow{position:absolute;inset:0;background:
    radial-gradient(46rem 30rem at 88% -12%, rgba(224,122,95,.28), transparent 60%),
    radial-gradient(40rem 30rem at -8% 20%, rgba(238,177,90,.16), transparent 55%)}
  .grain{position:absolute;inset:0;opacity:.05;mix-blend-mode:overlay;
    background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='140' height='140'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='.82' numOctaves='2'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E")}
  .mini{position:absolute;top:70px;right:84px;width:266px;display:grid;grid-template-columns:repeat(7,1fr);gap:8px;opacity:.9}
  .mc{aspect-ratio:1/1;border-radius:6px;border:1px solid #46362a;background:#30241b}
  .mc.o{background:rgba(238,177,90,.18);border-color:#eeb15a}
  .mc.m{background:rgba(224,122,95,.16);border-color:#e07a5f}
  .mc.s{background:#2b2018}
  .brand{position:absolute;top:72px;left:84px;display:flex;align-items:center;gap:16px}
  .brand svg{width:52px;height:52px}
  .brand b{font-family:"Fraunces",serif;font-size:42px;font-weight:600;letter-spacing:-.01em}
  .status{position:absolute;top:150px;left:84px;font-size:18px;color:#eeb15a;letter-spacing:.05em}
  .block{position:absolute;top:300px;left:84px;right:84px}
  h1{font-family:"Fraunces",serif;font-size:62px;font-weight:600;line-height:1.06;letter-spacing:-.02em;max-width:1010px;color:#f7efe2}
  .sub{color:#b39d86;font-size:25px;margin-top:22px;font-family:"JetBrains Mono",monospace}
  .pills{position:absolute;left:84px;bottom:44px;display:flex;gap:14px;font-size:19px}
  .pill{border:1px solid #46362a;border-radius:999px;padding:8px 18px;color:#e4d7c5;background:#1e1610}
  .url{position:absolute;right:84px;bottom:48px;color:#eeb15a;font-size:23px}
  .grad{background:linear-gradient(100deg,#e07a5f,#eeb15a 72%);-webkit-background-clip:text;background-clip:text;color:transparent}
</style></head><body>
  <div class="glow"></div>
  <div class="grain"></div>
  ${miniBoard()}
  <div class="brand">
    <svg viewBox="0 0 32 32" fill="none"><linearGradient id="g" x1="4" y1="30" x2="28" y2="4" gradientUnits="userSpaceOnUse"><stop stop-color="#e07a5f"/><stop offset=".6" stop-color="#ef9d7f"/><stop offset="1" stop-color="#eeb15a"/></linearGradient>
    <path d="M16 3.5 4 13.2c-.5.4-.8 1-.8 1.6V15h3.2l9.6-7.7 9.6 7.7h3.2v-.2c0-.6-.3-1.2-.8-1.6L16 3.5Z" fill="url(#g)"/>
    <path d="M7 16.4v10.1c0 .8.6 1.5 1.5 1.5H12v-6.2a4 4 0 0 1 8 0V28h3.5c.8 0 1.5-.7 1.5-1.5V16.4L16 9.7 7 16.4Z" fill="url(#g)" opacity=".82"/>
    <circle cx="16" cy="17.6" r="2.15" fill="#17110d"/></svg>
    <b>nook</b>
  </div>
  <div class="status">◐ availability · read-only · booking excluded</div>
  <div class="block">
    <h1>${title.replace(/(availability|agent can read|boundary|circuit-breaker|contract)/i, (m) => `<span class="grad">${m}</span>`)}</h1>
    <div class="sub">${sub}</div>
  </div>
  <div class="pills"><span class="pill">read-only</span><span class="pill">JSON-first</span><span class="pill">no evasion</span></div>
  <div class="url">nookcli.sh</div>
</body></html>`;

for (const p of pages) {
  const html = resolve(tmpDir, `${p.slug}.html`);
  const shot = resolve(tmpDir, `${p.slug}.raw.png`);
  const png = resolve(outDir, `${p.slug}.png`);
  const sub = p.sub.replace(/</g, "&lt;").replace(/>/g, "&gt;");
  const title = p.title.replace(/</g, "&lt;").replace(/>/g, "&gt;");
  writeFileSync(html, card(title, sub));
  execSync(
    `"${CHROME}" --headless=new --no-sandbox --disable-gpu --hide-scrollbars ` +
      `--force-device-scale-factor=1 --window-size=${W},${H * 2} --screenshot="${shot}" "file://${html}"`,
    { stdio: "ignore" }
  );
  if (!existsSync(shot)) { console.error("failed:", p.slug); process.exit(1); }
  await sharp(shot).extract({ left: 0, top: 0, width: W, height: H }).png().toFile(png);
  console.log("og:", p.slug + ".png");
}
rmSync(tmpDir, { recursive: true, force: true });
console.log("done →", outDir);
