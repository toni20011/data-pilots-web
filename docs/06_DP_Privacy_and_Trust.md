# 06 — Privacy and Trust Framework

## The two-view model

Data Pilots checks are described in two parallel vocabularies that always map to each other:

### View 1 — Framework Areas (expert / compliance view)

The **internal knowledge backbone**. Derived from simplified principles + laws/standards (GDPR, UK DPA, CCPA, ISO 27001, SOC 2, NIST). Used for structuring the knowledge base, mapping to regulations, and advising clients.

| # | Framework Area | Core question |
|---|---|---|
| 1 | **Transparency** | Do you clearly tell people what you do with their data — before you do it? |
| 2 | **Data Storage & Security** | Is the data you hold protected — technically and procedurally? |
| 3 | **Data Sharing & Transfers** | Do you know what data leaves your organisation, where it goes, and on what terms? |
| 4 | **Governance & Data Usage** | Are you using data (including AI) only in ways people would reasonably expect and accept? |
| 5 | **Data Rights & Control** | Can people actually exercise their rights — access, correction, deletion, opt-out? |

### View 2 — Trust Pillars (buyer-facing / product view)

The **product surface** — language buyers and business owners actually use. Used for scan reports, scoring, and the product UI.

| # | Trust Pillar | Core question |
|---|---|---|
| 1 | **Transparency** | Do you clearly tell buyers and users what you do with their data? |
| 2 | **Safety** | Is your site technically secure and protected? |
| 3 | **UX** | Can buyers find what they need to feel confident before saying yes? |
| 4 | **AI Trust** | Are you transparent about how you use AI — for buyers and for learners? |

---

## Mapping between views

Each check belongs to one Framework Area AND scores under one Trust Pillar.

| Framework Area | Primary Trust Pillar | Secondary Trust Pillar |
|---|---|---|
| Transparency | Transparency | UX |
| Data Storage & Security | Safety | — |
| Data Sharing & Transfers | Transparency | Safety |
| Governance & Data Usage | AI Trust | Transparency |
| Data Rights & Control | Transparency | UX |

The translation layer between these two views is the **core IP** of Data Pilots.

---

## The maturity model — 5 levels

Each check is tagged with a maturity level (1–5) indicating the organisation's state:

| Level | Label | Description |
|---|---|---|
| 1 | Privacy-Aware | Beginning stages. Basic awareness exists but no formal processes. |
| 2 | Privacy-Proficient | Basic practices implemented, not consistently applied or reviewed. |
| 3 | Privacy-Savvy | Well-designed framework. Documented, communicated, integrated. |
| 4 | Privacy-Driven | Metrics-based management. Systematic but capable of improvement. |
| 5 | Privacy-Advanced | Highest maturity. Continuously improved via feedback loops and advanced tech. |

**Important:** Maturity level describes the organisation's state. Product tier describes what the scanner checks. These are related but not identical.

- Free tier: primarily surfaces level 1–2 signals (visible on the public website)
- Paid tier: assesses level 2–3 depth (are things documented, consistent, properly implemented?)
- Paid Plus: assesses level 3–4 depth (are things integrated, measured, regularly reviewed?)

---

## Regulatory mapping

Each Framework Area maps to specific regulations. Used to explain WHY a check matters to a specific buyer.

| Framework Area | GDPR | UK DPA 2018 | CCPA | ISO 27001 | SOC 2 | NIST |
|---|---|---|---|---|---|---|
| Transparency | Art. 13/14 | ✓ | §1798.100 | A.5 | CC2 | PR.IP |
| Data Storage & Security | Art. 25/32 | ✓ | §1798.150 | A.8 | CC6 | PR.DS |
| Data Sharing & Transfers | Art. 26/28 | ✓ | §1798.115 | A.5 | CC4 | PR.DS |
| Governance & Data Usage | Art. 5/22 | ✓ | §1798.185 | A.8 | CC3 | GV.RM |
| Data Rights & Control | Art. 15–22 | ✓ | §1798.105 | A.5 | CC2 | PR.IP |

---

## Check severity levels

Each check carries a severity:
- **Critical** — immediate buyer red flag or direct regulatory violation
- **Important** — significant procurement or compliance risk
- **Low** — good practice, but not immediately deal-blocking

---

## Source types

Each check has a `source` field indicating how it's performed:
- `"own"` — Data Pilots runs this check directly (HTTP request, HTML parse, header inspection)
- `"papaya"` — Papaya live browser agent performs this check (real browser, real consent flow)

Papaya checks are the most powerful because they simulate what a real buyer or auditor actually sees, not just what the static HTML says.

---

## Open questions (from architecture notes)

1. Are there additional sub-areas within the framework not yet captured?
2. Does the framework have its own severity/likelihood model (critical / high / medium / low risk)?
3. Are there L&D-specific regulations to add (xAPI/SCORM data, Ofsted, sector-specific procurement)?
4. Is "Aware → Prepared" journey language to be used in the product UI, or is it internal only?
5. Sub-label naming for framework areas in the paid wizard — product language vs compliance language (draft labels in `notes/checks-architecture-2026-04-15.md`)
