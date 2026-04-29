# 20 — Source Materials

## Internal notes (gitignored — local only)

These files are excluded from the GitHub repo (`notes/` is in `.gitignore`). They exist in the working directory only.

| File | Contents |
|---|---|
| `notes/checks-architecture-2026-04-15.md` | Full two-view model (Framework Areas vs Trust Pillars), depth-by-tier check breakdown, regulatory mapping table, maturity journey, open questions |
| `notes/advisor-notes-2026-04-15.md` | April 2026 advisor call — demand signal, "now what?" problem, positioning refinements, 30-second pitch draft |

---

## Source data files (in repo)

| File | Contents |
|---|---|
| `checks/checks_registry.json` | Canonical checks registry v3.0.0 — all check definitions with schema |
| `checks/focus_areas.json` | 9 focus areas for the paid wizard — checks unlocked, follow-up questions, output sections |

---

## Live site

| URL | Description |
|---|---|
| [datapilots.tech](https://datapilots.tech) | Main site — homepage |
| [datapilots.tech/panel.html](https://datapilots.tech/panel.html) | Trust Panel product page |
| [datapilots.tech/about.html](https://datapilots.tech/about.html) | About page |
| [datapilots.tech/framework.html](https://datapilots.tech/framework.html) | Framework / methodology |
| [datapilots.tech/founder.html](https://datapilots.tech/founder.html) | Toni's story |

---

## GitHub repository

[github.com/toni20011/data-pilots-web](https://github.com/toni20011/data-pilots-web)

Branch: `main` — this is the only branch. Pushes to main trigger Cloudflare deployment.

---

## Third-party services

| Service | Purpose | Docs |
|---|---|---|
| Cloudflare Workers | Hosting + API proxy runtime | [developers.cloudflare.com/workers](https://developers.cloudflare.com/workers/) |
| Papaya | Live browser consent-check API | Internal — see `08_DP_Integrations_and_APIs.md` |
| Google Fonts | Inter + DM Serif Display | [fonts.google.com](https://fonts.google.com) |
| Brevo | Email / community signups (pending) | [brevo.com](https://www.brevo.com) |

---

## Key decisions log

| Decision | Rationale | When |
|---|---|---|
| No build step / no framework | Speed of iteration; single developer; static site fits Cloudflare Workers assets model | Early |
| Inline CSS per page | No external stylesheet means no dependency chain; each page is self-contained | Early |
| DM Serif Display for section headings | Creates editorial, premium character that differentiates from generic SaaS | April 2026 |
| "Your team the path to act" in brand line | Explicitly counters assumption that "Data Pilots" + "AI" means fully managed service | April 2026 |
| "Get Started" / "Get Access" for pricing nav | "Pricing" felt transactional too early; "Get Access" signals early community feel | April 2026 |
| Snapshot → Community → Panel funnel | Zero friction at top of funnel; community creates engagement and founding member pipeline | Early |
| Trust Panel moved to panel.html | Homepage was too long; panel mockup more valuable in context of the full panel narrative | April 2026 |
| Section heading order on homepage | How It Works before Value Story; Pricing before FAQ — mirrors user decision journey | April 2026 |
| Two-view model (Framework Areas + Trust Pillars) | Internal expert view vs product buyer view — translation between them is core IP | April 2026 |

---

## Pending decisions / open questions

See also the open questions sections in each relevant doc:

- Exact naming of the 6 Trust Panel instruments (`04_DP_Platform_Product.md`)
- Scoring algorithm for Trust Pillars (`07_DP_Data_Models_and_Logic.md`)
- Whether "risk assessment" language lands better than "trust score" in market (`01_DP_Strategy.md`)
- Ongoing monitoring model vs one-time audit (`01_DP_Strategy.md`)
- Sub-label naming for framework areas in paid wizard UI (`06_DP_Privacy_and_Trust.md`)
- L&D-specific regulations to add (xAPI, Ofsted, sector procurement) (`06_DP_Privacy_and_Trust.md`)
- Community form Brevo integration (`08_DP_Integrations_and_APIs.md`)
- Mobile nav implementation (`09_DP_Design_and_UX.md`)
