# 10 — Build and Dev

## Stack

| Layer | Technology |
|---|---|
| Site | Static HTML files — no framework, no build step |
| Hosting | Cloudflare Workers + Assets |
| Runtime | `worker.js` — Cloudflare Worker (ES module) |
| Config | `wrangler.jsonc` |
| Deployment | Git push → GitHub → Cloudflare auto-deploy |
| API proxy | Papaya consent-check API (via Worker) |

---

## Deployment

No build step. Edit HTML → commit → push.

```bash
git add <files>
git commit -m "message"
git push origin main
```

GitHub remote: `https://github.com/toni20011/data-pilots-web`

Cloudflare picks up the push and deploys automatically. Live at [datapilots.tech](https://datapilots.tech).

---

## Local development

To run the Worker locally (with API proxy):

```bash
npx wrangler dev
```

This starts a local server with the Worker logic. The `PAPAYA_API_KEY` secret won't be available locally — to test the Papaya proxy you can temporarily hardcode the key or use a `.dev.vars` file (gitignored):

```
# .dev.vars (gitignored)
PAPAYA_API_KEY=cck_live_...
```

For pure static HTML development (no Worker features needed), any local HTTP server works:

```bash
python3 -m http.server 3000
# or
npx serve .
```

---

## `wrangler.jsonc`

```jsonc
{
  "name": "data-pilots-web",
  "main": "worker.js",
  "compatibility_date": "2026-04-23",
  "compatibility_flags": ["nodejs_compat"],
  "observability": { "enabled": true },
  "assets": {
    "directory": ".",
    "binding": "ASSETS"
  }
}
```

The `"directory": "."` means all files in the repo root are served as static assets. The Worker intercepts `/api/papaya` before it reaches the asset handler.

---

## Worker (`worker.js`)

```
/api/papaya  →  Papaya proxy handler
                POST: start a run
                GET: poll status / fetch screenshots / fetch report
                OPTIONS: CORS preflight

/*           →  env.ASSETS.fetch(request)  (static files)
```

The Worker adds CORS headers to all API responses. The Papaya API key is injected server-side from `env.PAPAYA_API_KEY`.

---

## Security headers (`_headers`)

Cloudflare serves the `_headers` file automatically for Pages deployments. Since this is a Workers deployment, the headers in `_headers` are applied via Cloudflare's asset serving. Headers set:

- `Strict-Transport-Security` (HSTS, 2 years, preload)
- `X-Frame-Options: DENY`
- `X-Content-Type-Options: nosniff`
- `Referrer-Policy: strict-origin-when-cross-origin`
- `Permissions-Policy` (no camera/mic/geo/payment)
- `Content-Security-Policy`

Note: `unsafe-inline` is in the CSP for both `script-src` and `style-src` because all CSS and JS is inline in the HTML files.

---

## File structure

```
/
├── index.html            # Homepage
├── panel.html            # Trust Panel product page
├── about.html            # About
├── framework.html        # Methodology
├── founder.html          # Toni's story
├── trust-ecosystem.html  # Trust ecosystem
├── privacy.html          # Privacy policy
├── terms.html            # Terms
├── worker.js             # Cloudflare Worker
├── wrangler.jsonc        # Cloudflare config
├── _headers              # Security headers
├── CLAUDE.md             # Claude Code project context
├── checks/
│   ├── checks_registry.json  # Canonical checks (v3.0.0)
│   └── focus_areas.json      # Paid wizard focus areas
├── docs/                 # This documentation set
└── notes/                # (gitignored) Architecture + advisor notes
```

---

## Gitignore

The following are excluded from the repo:
- `notes/` — architecture decisions and advisor notes (internal working docs)
- `.claude/` — Claude Code session data and worktrees
- `*.env` / secrets — standard exclusions
- Python virtualenvs, OS files, editor files

---

## Environment / secrets

| Secret | Purpose | How to set |
|---|---|---|
| `PAPAYA_API_KEY` | Papaya API auth token | Cloudflare dashboard → Workers → data-pilots-web → Settings → Environment Variables |

---

## Known technical debt / pending

| Item | Notes |
|---|---|
| Brevo email integration | Community form uses `mailto:` fallback |
| `trust-ecosystem.html` font | Missing DM Serif Display in Google Fonts load |
| Mobile nav | No hamburger menu — nav links hidden on mobile |
| Scanner backend | No backend scanner built yet — Papaya proxy exists but own checks (`source: "own"`) are not yet automated |
| Account / auth system | No user accounts yet — needed for saving Snapshot results and Trust Panel access |

---

## Adding a new page

1. Copy the `<head>` block from `about.html` or `index.html`
2. Ensure Google Fonts URL includes **both** Inter and DM Serif Display:
   ```
   family=Inter:wght@300;400;500;600;700;800;900&family=DM+Serif+Display:ital@0;1
   ```
3. Include `--font-display: 'DM Serif Display', Georgia, serif;` in `:root`
4. Copy the nav HTML and update anchor links if the page has different sections
5. Copy the footer HTML
6. Add the IntersectionObserver script block before `</body>` for reveal animations
