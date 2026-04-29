# 02 — User Journey

## The funnel

```
Awareness
  │  (social, word-of-mouth, search, outreach)
  ▼
Free Trust Snapshot  ←── no account, no friction
  │  "See your score in 5 minutes"
  │  URL input → scan → results with score + findings
  ▼
Join Community  ←── free, no card
  │  Save results, revisit any time
  │  Resource hub access
  │  Founding member rates on Panel
  ▼
Trust Panel (paid, early access)  ←── from community, choose path
  │  Full depth scan
  │  Team coordination
  │  Remediation tracking
  ▼
Trust Panel Plus (future)
     Enterprise — DPA support, human-in-the-loop, portal/platform scan
```

---

## Step 1 — Free Trust Snapshot

**Entry point:** Homepage hero (`#hero-scan`) — URL input field.

**What happens:**
1. User enters their website URL
2. Scan runs (own checks + Papaya live browser agent)
3. Results returned: overall trust score + breakdown across 4 Trust Pillars + individual findings

**Output — Trust Score:**
- Numeric score (0–100) across 4 pillars: Transparency, Safety, UX, AI Trust
- Each finding has: severity (critical / important / low), business impact, fix guide, effort, time-to-fix

**No account required.** Results are shown immediately. The mini-preview card on the homepage (`#hero-scan` area) shows a sample result to set expectation before they scan.

**Conversion moment:** Results page shows what's broken. CTA = "Join Community to save your results and get your fix roadmap."

---

## Step 2 — Community

**Entry point:** `#proof` section on homepage, "Join Community free" button.

**What they get:**
- Free, always — no card, no commitment
- Save Snapshot results and revisit any time
- Resource hub — practical guides for L&D businesses
- Founding member rates on Trust Panel at launch
- Direct input into what gets built

**Current state:** Email collection form live (mailto: fallback — Brevo integration pending).

**Conversion moment:** Community members choose their path to Trust Panel via the "Early Access Programs" section.

---

## Step 3 — Trust Panel (paid)

**Entry point:** `#proof` section — "Early Access Programs" cards (after community join).

**Two early access paths:**

### Done-with-you — Guided Deep Dive
- Work through the panel with a Data Pilots team member
- Understand every finding, prioritise the roadmap
- Recommended for first-time enterprise procurement preparation

### Self-serve — Early Access
- Full Trust Panel access immediately
- Community support + resource hub
- For technically confident users or those wanting to explore at their own pace

**What Trust Panel includes:**
- Full depth scan across all 5 framework areas (deeper than Snapshot)
- Assignments — findings assigned to the right person/tool
- Progress tracking — mark gaps as resolved, track over time
- Proof package — shareable evidence of compliance posture
- 6 instruments (dimensions) — the full picture beyond the 4 Snapshot pillars

---

## The "Aware → Prepared" journey

Internal language mapping product tiers to a user's compliance maturity state:

```
AWARE       →  Free Snapshot
                Surface-level check. What's visible on the public website.
                "Can a buyer or auditor see this without asking?"
                No account needed. Snapshot only.

PREPARED    →  Trust Panel (paid)
                Depth within each framework area.
                Checks that require fetching/analysing content, not just detecting presence.
                Account required. Results saved. Progress trackable.

            →  Trust Panel Plus (future / paid_plus)
                Operational checks — do you actually have the DPA, the policy, the process?
                Human-in-the-loop. Portal/platform scan. Remediation support.
```

---

## Paid wizard flow (planned)

For paid users, the Trust Panel wizard has 3 steps:

**Step 1:** Run the full scan (all framework areas at paid depth)

**Step 2:** Select 1–3 focus areas to go deeper on. Options:
- GDPR & EU/UK Data Protection
- CCPA & US Privacy
- Enterprise Procurement Readiness
- Learner Data Protection
- AI Disclosure & Governance
- Cookie & Consent Compliance
- Terms, Contracts & DPAs
- Technical Security
- First Impressions & Buyer Trust Signals

**Step 3:** Answer follow-up questions tailored to the selected focus areas. Output: a section-by-section report with plain-language findings, prioritised actions, and regulatory context.

---

## Key UX principles

- **No account needed for the Snapshot** — friction reduction is critical to conversion
- **Plain language throughout** — no jargon. Business impact before compliance reference.
- **Action paired with every finding** — "here's what to fix" is part of the core value, not an add-on
- **Team-ready outputs** — findings are assigned, not just listed. The Panel is built for the whole team, not just the founder.
