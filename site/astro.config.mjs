// @ts-check
import { defineConfig } from "astro/config";
import starlight from "@astrojs/starlight";
import starlightLlmsTxt from "starlight-llms-txt";

// Apex (root) domain. NOTE: nookcli.sh is the PLANNED domain — not yet bought/bound.
// This only sets canonical/OG URLs at build time; nothing here asserts the site is live.
const SITE = "https://nookcli.sh";

export default defineConfig({
  site: SITE,
  integrations: [
    starlight({
      title: "nook",
      description:
        "An agent-friendly, read-only Airbnb search + forward-availability CLI. JSON-first, booking excluded by design, no auth. Its wedge: a free per-day availability calendar (available / min-nights / price) no other free agent tool offers.",
      logo: { src: "./src/assets/mark.svg", alt: "nook" },
      customCss: ["./src/styles/tokens.css", "./src/styles/docs.css"],
      social: [
        { icon: "github", label: "GitHub", href: "https://github.com/rnwolfe/nook" },
      ],
      plugins: [starlightLlmsTxt()],
      // Head override sets per-page og:image/twitter:image (see src/components/Head.astro).
      components: { Head: "./src/components/Head.astro" },
      head: [
        { tag: "meta", attrs: { property: "og:type", content: "website" } },
        { tag: "meta", attrs: { name: "twitter:card", content: "summary_large_image" } },
        {
          tag: "link",
          attrs: {
            rel: "stylesheet",
            href: "https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,500;9..144,600;9..144,700&family=Figtree:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;700&display=swap",
          },
        },
      ],
      sidebar: [
        { label: "Introduction", link: "/introduction/" },
        {
          label: "Getting Started",
          items: [
            { slug: "getting-started/install" },
            { slug: "getting-started/quickstart" },
            { slug: "getting-started/no-auth" },
          ],
        },
        {
          label: "Guides",
          items: [
            { slug: "guides/searching" },
            { slug: "guides/availability" },
            { slug: "guides/listing-details" },
            { slug: "guides/place-resolution" },
            { slug: "guides/reviews" },
            { slug: "guides/bounding-output" },
            { slug: "guides/pagination" },
          ],
        },
        {
          label: "Concepts",
          items: [
            { slug: "concepts/output-envelope" },
            { slug: "concepts/read-only" },
            { slug: "concepts/legitimacy" },
            { slug: "concepts/etiquette" },
          ],
        },
        {
          label: "Reference",
          items: [
            { slug: "reference/commands" },
            { slug: "reference/flags" },
            { slug: "reference/exit-codes" },
            { slug: "reference/schema-agent" },
            { slug: "reference/version-check" },
          ],
        },
        {
          label: "Troubleshooting",
          items: [
            { slug: "troubleshooting/rate-limited" },
            { slug: "troubleshooting/upstream-drift" },
          ],
        },
      ],
      editLink: { baseUrl: "https://github.com/rnwolfe/nook/edit/main/site/" },
    }),
  ],
});
