# 08 — Integrations and APIs

## Papaya Consent-Check API

The primary third-party integration. Papaya runs a **live browser agent** that visits a URL and performs real consent-flow checks — the gold standard because it sees exactly what a buyer or regulator would see.

**Base URL:** `https://papaya-consent-check-be11a0846ed5.herokuapp.com/api/v1`

**Auth:** Bearer token (`PAPAYA_API_KEY` — Cloudflare Worker secret, not in repo)

### Endpoints (proxied at `/api/papaya`)

| Method | Path / Params | Purpose |
|---|---|---|
| `POST /api/papaya` | body: `{ "url": "https://example.com" }` | Start a scan run |
| `GET /api/papaya?session_id=X` | — | Poll run status |
| `GET /api/papaya?session_id=X&screenshots=1` | — | Fetch screenshots from the run |
| `GET /api/papaya?session_id=X&report=1` | — | Fetch markdown report |

**POST request body to Papaya:**
```json
{
  "url": "https://example.com",
  "task": "reject_all",
  "state": "US-CA",
  "wait_for_debug_url_seconds": 2
}
```

**What Papaya checks (5 checks that use source: "papaya"):**

| Check ID | What it tests |
|---|---|
| `papaya_banner` | Does a real browser see a consent banner with Accept, Decline, and Settings? |
| `papaya_reject` | Does clicking "Decline All" actually stop tracking? |
| `papaya_preload` | How many trackers fire before any consent is given? |
| `papaya_cmp` | Is a recognised CMP (OneTrust, Cookiebot, etc.) identified? |
| `papaya_categories` | Does the banner offer granular category-level consent? |

---

## Cloudflare Worker (`worker.js`)

The Worker handles two concerns:

1. **API proxy** — `/api/papaya` routes to the Papaya API with CORS headers and secret injection
2. **Static asset serving** — everything else goes to `env.ASSETS.fetch(request)`

```javascript
// Routing logic
if (pathname === '/api/papaya') {
  return handlePapaya(request, env);
}
return env.ASSETS.fetch(request);
```

**CORS headers applied to all API responses:**
```
Access-Control-Allow-Origin: *
Access-Control-Allow-Methods: POST, GET, OPTIONS
Access-Control-Allow-Headers: Content-Type
```

---

## Brevo (community email)

**Purpose:** Collect community member emails and trigger welcome sequence.

**Current state:** The community join form uses a `mailto:` fallback — Brevo is **not yet wired up**. This is a pending integration.

**When implemented:** The form `action` on the community signup should POST to Brevo's API (or a Brevo-hosted form endpoint) to add the subscriber to the community list and trigger any automated sequences.

---

## Planned / future integrations

| Integration | Purpose | Status |
|---|---|---|
| Brevo | Community email list + welcome flow | Pending |
| LMS / portal scanning | Extend paid_plus tier to scan LMS data handling | Future |
| Cyber Essentials / certification lookup | Verify existing certifications in enterprise procurement checks | Future |
| Sub-processor database | Identify and verify known sub-processors from tool names | Future |

---

## Security headers (`_headers`)

Applied to all static assets by Cloudflare:

```
Strict-Transport-Security: max-age=63072000; includeSubDomains; preload
X-Frame-Options: DENY
X-Content-Type-Options: nosniff
Referrer-Policy: strict-origin-when-cross-origin
Permissions-Policy: camera=(), microphone=(), geolocation=(), payment=()
Content-Security-Policy: default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; connect-src 'self'; frame-ancestors 'none'
```

Note: `unsafe-inline` is present for both `script-src` and `style-src` because the site uses inline `<style>` and `<script>` blocks throughout.

---

## Environment secrets

| Secret | Where | How set |
|---|---|---|
| `PAPAYA_API_KEY` | Cloudflare Worker environment | Cloudflare dashboard → Workers → Settings → Variables |
