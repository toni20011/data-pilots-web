# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Data Pilots is a trust and compliance checking product for online training (L&D) businesses selling to corporate clients. The public site at datapilots.tech is the marketing + product surface. There is no separate app repo yet — everything lives here.

The core product loop:
1. **Free Trust Snapshot** — scan a public website URL, no account required, returns a score across 4 Trust Pillars
2. **Trust Panel** — paid product: deeper analysis, team coordination, remediation tracking

## Deployment

There is **no build step**. Edit HTML files, commit, push to `main` → Cloudflare auto-deploys.

```bash
git add <files>
git commit -m "message"
git push origin main
```

The site runs on **Cloudflare Workers** via `wrangler.jsonc`. The worker (`worker.js`) serves static assets and proxies the Papaya API at `/api/papaya`. To test locally with the Worker:

```bash
npx wrangler dev
```

The `PAPAYA_API_KEY` is a Cloudflare Worker secret (set in the dashboard, not in the repo).

## Architecture

### Static HTML site

All pages are self-contained HTML files with inline `<style>` and `<script>` blocks — no external CSS files, no JS bundler. Each page includes:
- Google Fonts (`Inter` + `DM Serif Display`) loaded via `<link>` in `<head>`
- CSS variables defined in `:root` (colors, radii, easing, `--font-display`)
- Reveal animation system: elements start at `opacity: 0; transform: translateY(20px)` and become visible via IntersectionObserver adding `.visible` class

### Design system (inline, repeated per page)

All pages share the same CSS variable palette:
- Navy: `#0B1929` (dark bg), `#112238` (mid), `#1A3350` (soft)
- Accent: `--teal: #00C8A8`, `--cyan: #00AFCC`
- Text scale: `--slate-400/500/600/800`

Typography:
- **Body / UI**: Inter (weights 300–900)
- **Section headings (h2)**: `font-family: var(--font-display); font-weight: 400` — DM Serif Display, not heavy Inter
- **Hero h1s**: Inter 900 (intentional — punch/impact)

When adding a new page, copy the `:root` block and Google Fonts `<link>` from an existing page. Both Inter and DM Serif Display must be in the fonts URL.

### Worker routing (`worker.js`)

```
/api/papaya  → Papaya consent-check API proxy (POST = start run, GET = poll/screenshots/report)
/*           → env.ASSETS.fetch() (static file serving)
```

### Checks data (`checks/`)

Two JSON files define the product's knowledge backbone:

- `checks_registry.json` — canonical registry of all checks, versioned (currently v3.0.0). Each check has: `id`, `framework_area`, `trust_pillar`, `tier` (free/paid/paid_plus), and maturity level (1–5).
- `focus_areas.json` — the 9 focus areas a paid user selects in the wizard (e.g. GDPR, Enterprise Procurement, AI Transparency). Each focus area declares which `checks_unlocked` it activates and what `follow_up_questions` to ask.

### Two-view model (critical concept)

Checks are described in two parallel vocabularies that always map to each other:

| Internal (expert/compliance) | Product surface (buyer-facing) |
|---|---|
| Transparency | Transparency |
| Data Storage & Security | Safety |
| Data Sharing & Transfers | *(maps to Transparency + Safety)* |
| Governance & Data Usage | AI Trust |
| Data Rights & Control | *(maps to Transparency + UX)* |

The **5 Framework Areas** are the knowledge backbone. The **4 Trust Pillars** are what users see in their Snapshot score. The framework layer that translates between them is the core IP.

### Product tiers

| Tier | What it covers |
|---|---|
| free | Public website scan. What a buyer or auditor can see without asking. No account. |
| paid | Deeper scan per framework area. Account required. Results saved and trackable. |
| paid_plus | Operational checks, human-in-the-loop, remediation support. |

This maps to the "Aware → Prepared" journey language used internally.

## Key pages

| File | Purpose |
|---|---|
| `index.html` | Main marketing homepage — hero, scan widget, How It Works, pricing, FAQ, community signup |
| `panel.html` | Trust Panel product page — features, 6-instrument dial, results preview |
| `about.html` | Company/team page — thesis, co-founders, advisors |
| `framework.html` | Methodology explainer — three layers (business, expert, legal), the 5 framework areas |
| `founder.html` | Toni's story — personal founder narrative |
| `trust-ecosystem.html` | Trust ecosystem overview |
| `worker.js` | Cloudflare Worker — API proxy + asset serving |
| `checks/checks_registry.json` | Canonical checks registry |
| `checks/focus_areas.json` | Paid wizard focus area definitions |
| `_headers` | Static security headers (HSTS, CSP, X-Frame-Options, etc.) |

## Nav structure

The nav has 3 on-page anchor links + a "Learn More ▾" dropdown for separate pages:

```
How It Works (#results)  |  Get Started (#pricing)  |  FAQ (#faq)  |  Learn More ▾
                                                                        → About Data Pilots
                                                                        → Trust Panel
                                                                        → Our Framework
                                                                        → Get Involved ↓ (this page)
```

CTA buttons: "Get Access" (→ `#pricing`) and "Take the Snapshot" (→ `#hero-scan`).

## Brand line

The central positioning statement placed in the announce bar, Why Data Pilots section, and About page thesis:

> "You built something worth trusting. Data Pilots gives you the full picture — and your team the path to act."

This explicitly names "your team" as the actor to counter the assumption that Data Pilots is a fully managed/done-for-you service.

## Papaya API integration

Papaya is a third-party consent-check service that runs a live browser agent against a URL. The worker proxies it at `/api/papaya`:

- `POST /api/papaya` `{ url }` → starts a run, returns `{ session_id, ... }`
- `GET /api/papaya?session_id=X` → polls run status
- `GET /api/papaya?session_id=X&screenshots=1` → returns screenshots
- `GET /api/papaya?session_id=X&report=1` → returns markdown report

The key check IDs that use Papaya are prefixed `papaya_` in the checks registry (e.g. `papaya_banner`, `papaya_reject`, `papaya_preload`, `papaya_cmp`, `papaya_categories`).

## Notes (gitignored)

The `notes/` directory contains architecture decisions and advisor call notes — not committed to the repo. Key documents:
- `notes/checks-architecture-2026-04-15.md` — full two-view model, depth-by-tier breakdown, regulatory mapping (GDPR/CCPA/ISO/SOC2/NIST), open questions
- `notes/advisor-notes-2026-04-15.md` — product positioning refinements, "the Trust Check IS the risk assessment" framing
