# 07 — Data Models and Logic

## Checks Registry (`checks/checks_registry.json`)

The canonical source of truth for all Trust Checks. Version `3.0.0` as of 15 April 2026.

### Check schema

Every check has:

```json
{
  "id": "string",                         // unique identifier (e.g. "papaya_banner", "https")
  "name": "string",                       // human-readable name
  "framework_area": "string",             // one of 5 framework areas
  "pillar": "string",                     // one of 4 trust pillars
  "maturity_level": 1-5,                  // 1=Aware ... 5=Advanced
  "tier": "free|paid|paid_plus",          // product tier required to run
  "severity": "critical|important|low",   // impact on buyer trust / compliance risk
  "what_we_check": "string",              // plain description of the check
  "why_it_matters_business": "string",    // business impact (non-technical)
  "why_it_matters_compliance": "string",  // regulatory/compliance reference
  "buyer_impact": ["string"],             // which buyer personas care
  "fix_guide": "string",                  // plain-language fix instruction
  "effort": "low|medium|high",            // effort to fix
  "time_to_fix": "string",                // e.g. "< 1 hour", "2–4 hours", "3–5 days"
  "source": "own|papaya",                 // how the check is performed
  "follow_up_questions_paid": ["string"]  // additional questions shown in paid wizard
}
```

### Buyer impact personas

| Key | Description |
|---|---|
| `enterprise_l&d` | Enterprise L&D buyer |
| `hr_buyer` | HR/people team buyer |
| `it_security` | IT and security teams |
| `legal_procurement` | Legal and procurement teams |

### Full check list (current registry)

**Free tier checks:**

| ID | Name | Framework Area | Pillar | Severity |
|---|---|---|---|---|
| `https` | HTTPS / Secure Connection | data_storage_security | safety | critical |
| `hsts` | HSTS header | data_storage_security | safety | important |
| `csp` | Content Security Policy | data_storage_security | safety | important |
| `xfo` | Clickjacking Protection | data_storage_security | safety | important |
| `privacy_page` | Privacy Policy Page | transparency | transparency | critical |
| `policy_gdpr` | GDPR Language in Privacy Policy | transparency | transparency | important |
| `policy_coverage` | Privacy Policy — Required Topics | transparency | transparency | important |
| `policy_date` | Privacy Policy — Last Updated Date | governance_data_usage | transparency | low |
| `policy_dpa` | DPA Language | data_sharing_transfers | transparency | important |
| `terms_page` | Terms of Service Page | data_sharing_transfers | transparency | important |
| `cookie_policy_page` | Cookie Policy Page | transparency | transparency | important |
| `footer_links` | Policy Links in Footer | transparency | ux | critical |
| `cookie_policy_link` | Cookie Policy Link in Footer | data_rights_control | ux | low |
| `contact_page` | Contact Page | data_rights_control | ux | important |
| `cookies` | Cookie Consent Language (HTML) | data_rights_control | transparency | important |
| `papaya_banner` | Consent Banner — Live Browser | data_rights_control | transparency | critical |
| `papaya_reject` | Reject-All Effectiveness — Live | data_rights_control | transparency | critical |
| `papaya_preload` | Pre-Consent Tracking Volume | data_sharing_transfers | transparency | important |
| `papaya_cmp` | CMP Identified | governance_data_usage | transparency | low |
| `papaya_categories` | Consent Category Granularity | data_rights_control | transparency | (see registry) |
| `ai_disclose` | AI Tool Mention on Public Site | governance_data_usage | ai_trust | (see registry) |
| `sitemap` | Sitemap / Findability | (see registry) | ux | (see registry) |

**Paid tier checks (sample):**

| ID | Name |
|---|---|
| `policy_ccpa` | CCPA / US Privacy Language |
| `lms_data_notice` | Data Collection Notice in LMS/Portal |
| `lms_data_retention` | Data Retention Policy Language |
| `lms_third_party` | LMS Third-Party Disclosure |
| `ai_learner_disclosure` | Learner AI Transparency |
| `incident_response` | Incident Response Plan |
| `privacy_reviews` | Privacy Reviews / Governance |
| `ai_governance_policy` | Internal AI Governance Policy |

**Paid Plus checks (sample):**

| ID | Name |
|---|---|
| `dpa_contract` | Standard DPA Available |
| `sub_processor_list` | Sub-Processor List Published |
| `continuous_improvement` | Continuous Improvement Process |

---

## Focus Areas (`checks/focus_areas.json`)

Selectable by paid users in the wizard (Step 2). Each focus area unlocks additional paid checks and a specific set of follow-up questions.

### Focus area schema

```json
{
  "id": "string",
  "label": "string",
  "icon": "emoji",
  "short_desc": "string",          // shown in wizard selection
  "why_select": "string",          // guidance on when to choose this
  "checks_unlocked": ["check_id"], // paid checks activated by this selection
  "follow_up_questions": ["string"],
  "output_section": "string",      // section heading in the report
  "output_intro": "string"         // intro paragraph for this section in the report
}
```

### 9 Focus areas

| ID | Label |
|---|---|
| `gdpr_eu` | GDPR & EU/UK Data Protection |
| `ccpa_us` | CCPA & US Privacy |
| `enterprise_procurement` | Enterprise Procurement Readiness |
| `learner_data` | Learner Data Protection |
| `ai_transparency` | AI Disclosure & Governance |
| `cookie_consent` | Cookie & Consent Compliance |
| `contracts_dpa` | Terms, Contracts & DPAs |
| `security_posture` | Technical Security |
| `brand_trust` | First Impressions & Buyer Trust Signals |

---

## Scoring model

**Trust Pillars:** The Snapshot produces a score for each of the 4 Trust Pillars (Transparency, Safety, UX, AI Trust). Each pillar score is derived from the checks that map to it.

**Overall score:** Aggregated from pillar scores, weighted by severity. Critical findings have greater negative impact than important or low findings.

_(Exact scoring algorithm not yet formally specified — inferred from check severity and pillar mapping. To be formalised when scanner is built.)_

---

## Key data relationships

```
Framework Area (5)
    └── has many Checks
            └── each Check maps to one Trust Pillar (4)
            └── each Check has a tier (free / paid / paid_plus)
            └── each Check has a maturity level (1–5)
            └── each Check has a source (own / papaya)

Focus Area (9)
    └── unlocks a set of Checks (paid tier)
    └── triggers a set of follow-up questions
    └── produces an output_section in the report
```
