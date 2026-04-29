# 03 — External Website

## Site structure

| File | Purpose | Background |
|---|---|---|
| `index.html` | Main marketing homepage | Dark navy |
| `panel.html` | Trust Panel product page | Dark navy |
| `about.html` | Company / team | Light slate |
| `framework.html` | How the checks work (methodology) | Light slate |
| `founder.html` | Toni's story | Light slate |
| `trust-ecosystem.html` | Trust ecosystem overview | Light slate |
| `privacy.html` | Privacy policy | Light slate |
| `terms.html` | Terms of service | Light slate |

---

## Navigation

**Top nav links (3 on-page + 1 dropdown):**

```
How It Works (#results)  |  Get Started (#pricing)  |  FAQ (#faq)  |  Learn More ▾
```

**"Learn More" dropdown:**
- About Data Pilots → `about.html`
- Trust Panel → `panel.html`
- Our Framework → `framework.html`
- Get Involved ↓ this page → `#proof`

**CTA buttons (top right):**
- "Get Access" → `#pricing`
- "Take the Snapshot" → `#hero-scan`

**Announce bar (top of every page):**
> You built something worth trusting. Data Pilots gives you the full picture — and your team the path to act. · Free Trust Snapshot · Trust Panel

---

## Homepage section order

1. **Announce bar** — brand positioning line + product links
2. **Hero** (`#hero-scan`) — headline, URL scan widget, hero secondary links
3. **Pain** — "Deals go quiet. You never know why."
4. **Stats** — validation numbers
5. **How It Works** (`#journey`) — 3-step process
6. **Value Story** (`#value-story`) — before/after narrative
7. **Why Data Pilots** (`#why-dp`) — founder story + "what we keep seeing" grid
8. **Pricing / Get Started** (`#pricing`) — Community + Panel tiers
9. **FAQ** (`#faq`) — accordion
10. **Community / Get Involved** (`#proof`) — join form + early access programs
11. **Integrations** — tool logos

---

## Key copy decisions

### Brand line (3 placements)
- Announce bar — full line
- Why Data Pilots section — as italic pull-quote with teal left border
- About page thesis — as italic pull-quote with teal left border

### "Get Started" naming
- Nav link: "Get Started" (→ `#pricing`)
- CTA button in nav: "Get Access" (→ `#pricing`)
- Section kicker on homepage pricing section: "Get Started"
- Panel access CTA on panel.html: "Get Access" or "Join Early Access"

### Community section framing
- Community is **free always** — the entry point and what gives access to everything
- Not "Step 1" — the step numbering was removed (felt mechanical)
- "Early Access Programs" replaces "Step 2" as the divider between community join and Panel tiers

### Pain section language
- "Deals go quiet. You never know why." — the emotional hook
- Not framed as compliance failure — framed as silent business cost

---

## Why Data Pilots section

**Section H2:** "We've been on both sides. We built the bridge."

**Narrative (two paragraphs):**
1. Growth teams vs compliance teams — clients paid every time without knowing why a deal went quiet
2. Built specifically for L&D businesses — when they lose a deal to a trust gap, it's not just revenue. It's a team that doesn't get developed.

**Closing pull-quote:**
> "You built something worth trusting. Data Pilots gives you the full picture — and your team the path to act."

**Supporting "What we keep seeing" grid** (4 cards):
- ⚡ Growth vs. compliance — "One moving fast, one brought in to slow things down"
- 🔍 Buyers check first — (silent pre-deal due diligence)
- [2 more cards — deals going quiet / trust gaps]

---

## About page

**Structure:**
1. Hero — "Built for the businesses whose mission matters."
2. Thesis band — "Who we are" + thesis quote + brand line pull-quote
3. Co-founders section
4. When you see Data Pilots in the world
5. Advisors
6. Trust takes more than software
7. Where we show up
8. CTA — "Ready to see where you stand?"

**Thesis quote:**
> "Online training businesses are losing corporate deals silently — not because their work isn't good, but because trust gaps nobody checked are standing in the way."

---

## Framework page

**Structure:**
1. Hero — "For the business and the team behind it."
2. Intro explainer — "Why does this even matter for a small L&D business?"
3. Layer diagram — Three layers (business language → framework areas → regulatory standards)
4. Pillar detail — tabbed view of each framework area with specific checks
5. Papaya section — explaining the live browser agent checks
6. CTA

**Key message:** Data Pilots translates plain business language into expert and legal frameworks. The translation is the core IP — not the raw compliance data.

---

## Panel page (Trust Panel product page)

**Structure:**
1. Hero — "Trust Panel" with clear value statement
2. Bridge section — Snapshot vs Panel comparison
3. Features grid — "What's in the hub" (6 feature cards)
4. Trust Dial — 6 instruments visual (SVG dial with interactive instrument list)
5. Results / report preview — side-by-side mockup (moved from homepage)
6. "One place. Full control. Proof you can share." section
7. Built for L&D businesses section
8. Early access CTA

---

## Mini Snapshot preview (homepage)

A sample results card sits below the URL input widget on the homepage (visible on desktop only, hidden on mobile `@media max-width: 860px`). It shows:
- Sample trust score (numeric)
- 4 pillar bars with scores
- 3 sample findings with severity tags

Purpose: sets expectation before they scan. Shows the output format so visitors know what they'll get.

---

## Notes on visual consistency

- Dark pages (index, panel): navy background (`#0B1929`), teal accents, white text
- Light pages (about, framework, founder): slate-50 background, slate-800 text
- All pages share the same nav and footer pattern
- Section headings (h2): DM Serif Display weight 400 — editorial, not heavy
- Hero headings (h1): Inter 900 — bold impact
- Reveal animations: `.reveal` + IntersectionObserver on every page
