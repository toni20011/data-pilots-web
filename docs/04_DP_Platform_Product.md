# 04 — Platform Product (Trust Panel)

## What the Trust Panel is

The Trust Panel is the paid product — a working hub for online training businesses that need to close their trust gaps, not just see them.

**One sentence:** One place to see everything, get the right people fixing what's flagged, and track progress until the gaps are closed.

---

## The six instruments

The Trust Panel goes deeper than the 4 Trust Pillars in the free Snapshot. The Panel uses **6 instruments** (dimensions) to give a full picture.

The 6 instruments correspond to the product's deeper framework areas. They are shown as a dial/pie visual on the Trust Panel page — each instrument is a segment, and progress within each is shown as a fill level.

_(The 6 instruments are the 5 Framework Areas plus one additional dimension — exact naming to confirm. See `panel.html` Trust Dial section.)_

---

## What the panel does

### Full depth scan
- Runs all checks (free + paid tiers) across all 5 framework areas
- Not just "what's visible on the public website" — goes into documentation, configuration, and practice
- Results saved to the account, trackable over time

### Focus area selection (wizard)
Paid users select 1–3 focus areas to deepen the scan. The system runs all free checks + the paid checks tagged to the selected areas. Focus areas available:

| Focus Area | Who should select it |
|---|---|
| GDPR & EU/UK Data Protection | Any UK/EU clients or learners; GDPR asked in procurement |
| CCPA & US Privacy | US-based clients, especially California |
| Enterprise Procurement Readiness | Pitching to large employers, NHS, financial services |
| Learner Data Protection | Runs an LMS, delivers online learning, collects learner data |
| AI Disclosure & Governance | Uses AI in content creation, delivery, or operations |
| Cookie & Consent Compliance | Flagged for cookie issues; uses analytics/marketing trackers |
| Terms, Contracts & DPAs | Pitching to enterprise; been asked for a DPA |
| Technical Security | Asked to complete security questionnaire; regulated sector clients |
| First Impressions & Buyer Trust Signals | Wants to know what a buyer sees before a first call |

### Team coordination
- Findings assigned to the right person or tool
- Not just "here's what's wrong" — "here's who should fix it and how"
- Built for teams, not just solo founders

### Progress tracking
- Mark findings as resolved
- Rescan to verify fixes
- See improvement over time

### Proof package
- Shareable evidence of compliance posture
- For use in procurement questionnaires, due diligence, or supplier vetting

---

## Comparison: Snapshot vs Trust Panel

| | Free Snapshot | Trust Panel |
|---|---|---|
| Account needed | No | Yes |
| Check depth | Free tier only (visible signals) | Free + paid + paid_plus |
| Scope | Public website | Website + platform/portal (future) |
| Results saved | No | Yes, trackable |
| Team features | No | Assignments, notes, progress |
| Focus areas | No | 9 selectable |
| Follow-up questions | No | Yes (wizard step 3) |
| Proof package | No | Yes |
| Ongoing monitoring | No | Planned |

---

## Trust Panel page (`panel.html`)

Key sections on the product page:

**Bridge section** — positions the relationship between Snapshot and Panel:
- "Trust Snapshot shows you where to start."
- "Trust Panel gives you the full picture and how to fix it."
- "Your free score covers the four things buyers check first."
- "Trust Panel goes deeper — your platform, your tools, and a fix roadmap your whole team can act on."

**Features grid** — 6 feature cards covering what the Panel provides

**Trust Dial** — SVG dial visual showing the 6 instruments. Interactive: hover/click an instrument to highlight it and show details. Paired with an instrument list on the right showing:
- Number badge
- Instrument name
- What it covers (Snapshot view vs Panel depth)

**Results/report preview** — side-by-side mockup showing what a real Trust Panel report looks like (moved from homepage)

---

## Early access model

Trust Panel is in early access. Two paths for getting access:

**1. Done-with-you — Guided Deep Dive**
- Work through the panel with a Data Pilots team member
- Understand every finding, build the roadmap together
- Best for first-time enterprise procurement preparation

**2. Self-serve — Early Access**
- Immediate full access
- Community support + resource hub
- For technically confident users

**Community → Panel bridge:**
Community members are the primary pipeline. They've already seen their Snapshot, they know their gaps, they're motivated to fix them. Founding member rates are the conversion incentive.

---

## Future: platform/portal scan

The paid_plus tier (and eventual Trust Panel Plus) will extend beyond the public website to scan:
- The LMS / learning portal (learner data handling, consent, access controls)
- Internal governance documentation (AI policy, DPA availability, sub-processor list)
- Operational processes (data rights request process, incident response plan)

This requires human-in-the-loop guidance and is not automated at launch.

---

## Open product questions

- Exact naming of the 6 instruments in the Trust Panel dial
- Does the wizard use 3 steps or is Step 3 (follow-up questions) optional?
- What does the "proof package" look like — PDF export? Shareable link?
- Is there a rescan / monitoring frequency for paid accounts?
- Sub-label naming for framework areas in the paid wizard UI (product language vs compliance language — see `notes/checks-architecture-2026-04-15.md`)
