# 07b — Trust Snapshot Questionnaire: Questions, Answers & Scoring

This document is the **master reference** for the Trust Snapshot wizard. Any changes to question wording, answer options, scoring weights, or findings logic should be updated here first, then reflected in `index.html`.

---

## Overview

The wizard has a **URL gateway** followed by **5 questionnaire steps** collecting 11 data fields (F1–F11). Answers are used to:
1. Personalise the Trust Score (weight the 4 pillars by buyer segment)
2. Generate specific findings (plain-language issues with fix guides)
3. Provide compliance context (jurisdiction-appropriate framing)
4. Identify a "trust gap" (mismatch between self-assessed confidence and actual score)
5. Prioritise findings output by declared concern area (F8)

Answers stay in the browser — nothing is sent until the scan runs.

**Future intent:** The URL gateway should trigger a background Papaya session so the live site scan runs while the user completes the questionnaire, reducing overall wait time. See `TODO` comment in `wizNext(0)` in `index.html`.

---

## URL Gateway — Your Website

| Field | Type | Question |
|---|---|---|
| URL | Text input | Enter your website URL to get started |

**Validation:** Must be at least 5 characters. Error state shakes the input and highlights red.

**Step behaviour:** Progress dots are hidden until the URL is entered. After validation, dots appear and Step 1 begins.

**Scoring impact:** None directly — the URL is passed to the scanner.

---

## Step 1 — Your Visitors & Target Clients

### F9 — Special data types (multi-select)
**Question:** Does your work involve any of these? _(tick all that apply)_

| Value | Label |
|---|---|
| `children` | Children or under-18s |
| `health` | Health, mental health, or clinical information |
| `financial` | Financial account or payment data |
| `other_regulated` | Other specially regulated data |
| `none` | None of these |

`none` is mutually exclusive — selecting it deselects others, and selecting any other deselects `none`.

**Scoring impact:** None currently — flags higher-risk data categories for future enhanced findings.

---

### F10 — Client geography
**Question:** Where are most of your clients and learners based?

| Value | Label | Compliance context applied |
|---|---|---|
| `europe` | Primarily Europe (UK and EU) | UK GDPR / EU GDPR + PECR — lawful basis, rights, third-party tools |
| `us` | Primarily United States | CCPA/CPRA — right to know, right to delete, opt-out of sale |
| `global` | Global / multiple regions | EU GDPR as baseline + US state laws |
| `unsure` | I'm not sure | EU GDPR as strictest baseline (default) |

**Scoring impact:** Selects the **compliance context block** shown in results output — no effect on numeric score.

---

### F11 — Revenue (approximate)
**Question:** Roughly what's your annual business revenue? (USD)

| Value | Label |
|---|---|
| `lt1m` | Under $1M |
| `1m_25m` | $1M – $25M |
| `gt25m` | Over $25M |
| `withheld` | Prefer not to say |

**Scoring impact:** None currently — contextual segmentation for future use.

---

## Step 2 — Your Business

### F1 — Your role
**Question:** What best describes your role?

| Value | Label |
|---|---|
| `coach` | Independent coach or consultant |
| `small_team` | Small L&D team or training provider |
| `agency` | Multi-person consultancy or agency |
| `other` | Other |

**Scoring impact:** None directly — contextual, used for personalising output language.

---

### F2 — Who you sell to (multi-select)
**Question:** Who do you sell to? _(tick all that apply)_

| Value | Label |
|---|---|
| `consumer` | Consumers — individuals buying for themselves |
| `b2b_sme` | B2B — SMEs and mid-sized companies |
| `b2b_enterprise` | B2B — enterprise (large corporates) |
| `government` | Government and public sector |
| `other` | Other or not sure |

**Scoring impact:** Drives **pillar weighting** — the most demanding buyer segment selected determines how much each pillar contributes to the overall score.

| Segment | UX weight | Transparency | Safety | AI Trust |
|---|---|---|---|---|
| `consumer` | 25% | 40% | 20% | 15% |
| `b2b_sme` | 25% | 20% | 30% | 25% |
| `b2b_enterprise` | 15% | 25% | 30% | 30% |
| `government` | 15% | 30% | 30% | 25% |

When multiple segments are selected, the **maximum weight** for each pillar across all selected segments is used, then re-normalised to sum to 100%.

Default (if nothing selected): `b2b_sme` weights.

---

## Step 3 — Your Practices

### F3 — AI use
**Question:** Do you use AI tools in your work?

| Value | Label | AI Trust score |
|---|---|---|
| `no` | No, not at all | 100 |
| `own_drafts` | Yes, but only for my own drafts and productivity | 60 |
| `client_facing` | Yes, and AI touches client-facing content (summaries, materials) | 25 |
| `processes_data` | Yes, and AI processes client or learner data (names, transcripts, assessments) | 0 |
| `unsure` | I'm not sure | 50 |

**Scoring impact:** Directly sets the **AI Trust pillar score**.

**Findings triggered:**
- `processes_data` → critical finding: "Client data may be entering AI tools without a clear policy" (tag: FIX THIS WEEK)
- `client_facing` or `own_drafts` → warning: "You use AI — but buyers may not be able to tell from your site" (tag: QUICK WIN)

---

### F4 — Data management _(currently not shown in wizard UI — reserved field)_

| Value | Label | Transparency contribution |
|---|---|---|
| `email` | Primarily email | 40 |
| `crm` | CRM system | 60 |
| `multiple` | Multiple systems | 40 |
| `unsure` | Not sure | 20 |

**Note:** F4 is defined in the scoring logic but not currently asked in the wizard. The transparency score defaults to using the F4 fallback value of 40 when unanswered. **Candidate for future wizard addition.**

---

### F5 — Privacy policy status
**Question:** What's your privacy policy situation?

| Value | Label | Transparency contribution |
|---|---|---|
| `legal_current` | Written or reviewed by a legal professional and kept current | 100 |
| `self_recent` | I wrote it myself or used a template, reviewed in the last 12 months | 60 |
| `old_unsure` | I have one but it's old or I'm not sure it's current | 20 |
| `none` | I don't have one | 0 |

**Scoring impact:** Contributes to **Transparency pillar score** (averaged with F4):
`transparency_score = round((F4_score + F5_score) / 2)`

With F4 at default (40), transparency = round((40 + F5_score) / 2)

**Findings triggered:**
- `none` → critical finding: "No privacy policy — your biggest trust gap right now" (tag: FIX THIS WEEK)
- `old_unsure` → warning: "Your privacy policy may be out of date" (tag: QUICK WIN)

---

## Step 4 — Your Confidence

### F6 — Confidence rating (scale 1–5)
**Question:** How confident are you that your website would pass a quick buyer trust check right now?

Scale: 1 (Not at all) → 5 (Very confident)

**Scoring impact:** Used for **trust gap detection** (see below). Does not directly affect pillar scores.

---

### F7 — Buyer questions
**Question:** In the last 12 months, has a buyer asked you unexpected questions about privacy, data, security, or AI?

| Value | Label |
|---|---|
| `yes_multiple` | Yes, multiple times |
| `yes_once` | Yes, once |
| `not_noticed` | Not that I've noticed |
| `dont_know` | I don't know |

**Scoring impact:** Contextual only — used for personalising output messaging.

---

## Step 5 — Your Priorities

### F8 — Priority concern (multi-select)
**Question:** Which of these best describes your main concern? _(tick all that apply)_

| Value | Label | Focus area |
|---|---|---|
| `first_impression` | Making a trustworthy first impression on visitors | UX pillar |
| `corporate_trust` | Demonstrating trust to corporate buyers and procurement teams | Transparency + Safety pillars |
| `avoid_compliance` | Avoiding mistakes that could trigger non-compliance | Safety + AI Trust pillars |

**Scoring impact:** Contextual only — used to prioritise and frame findings output. No direct effect on pillar scores.

**Note:** F8 was previously a single-select "fix priority" question (ux/transparency/safety/ai_trust). Updated May 2026 to outcome-focused multi-select with three buyer-journey options.

---

## Scoring logic summary

### Pillar scores

| Pillar | Source | Baseline |
|---|---|---|
| **AI Trust** | F3 lookup table | 50 if unanswered |
| **Transparency** | Average of F4 + F5 scores | F4 defaults to 40 |
| **Safety** | Fixed baseline | 55 (no questionnaire source yet) |
| **UX** | Fixed baseline | 60 (no questionnaire source yet) |

**Note:** Safety and UX baselines are fixed because full live-site checks (HTTP headers, page structure) are a paid-tier feature. These will be populated by the Papaya scan in the paid product.

### Overall score

```
overall = round(
  (UX × w.ux) + (Transparency × w.transparency) +
  (Safety × w.safety) + (AI Trust × w.ai_trust)
)
```

Clamped to 0–100.

### Score labels

| Range | Label |
|---|---|
| 80–100 | Buyer-Ready |
| 60–79 | Solid |
| 40–59 | Needs Work |
| 0–39 | Needs Attention |

### Trust gap detection (F6 vs overall score)

| Condition | Message type |
|---|---|
| F6 ≥ 4 AND overall < 60 | Gap — "You rated confidence at X/5, but score is Y/100. This is where deals go quiet." |
| F6 ≤ 2 AND overall ≥ 70 | Rebuild — "You rated confidence at X/5, but score is Y/100. You're further along than you think." |

---

## Findings catalogue

| ID | Trigger | Pillar | Severity | Tag |
|---|---|---|---|---|
| `no_policy` | F5 = `none` | transparency | critical | FIX THIS WEEK |
| `stale_policy` | F5 = `old_unsure` | transparency | warning | QUICK WIN |
| `ai_data` | F3 = `processes_data` | ai_trust | critical | FIX THIS WEEK |
| `ai_disclose` | F3 = `client_facing` or `own_drafts` | ai_trust | warning | QUICK WIN |

Up to 3 findings shown in the free Snapshot. Additional findings gated behind Trust Panel.

---

## Pending / open decisions

- **F4 (data management)** — defined in scoring but not asked. Should it be added to Step 3? Or removed from scoring?
- **Safety and UX baselines** — currently fixed at 55 and 60. Should the questionnaire add questions to derive these? Or keep as live-scan-only?
- **F9 (special data)** — no findings triggered yet. What enhanced findings should special data categories unlock?
- **F11 (revenue)** — no scoring impact yet. Is this retained for segmentation, or should it be removed?
- **Weighting review** — are the F2 buyer segment weights calibrated correctly? Particularly AI Trust for enterprise (30%) vs consumer (15%).
- **F8 (priorities)** — multi-select, contextual only. Should selections influence pillar weighting or findings ordering? e.g. `corporate_trust` selection could boost Transparency/Safety weight.
- **Background Papaya scan** — URL gateway should fire a Papaya session immediately so the live site scan runs while the user completes the questionnaire. Needs implementation in `wizNext(0)`.
