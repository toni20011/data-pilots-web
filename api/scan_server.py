#!/usr/bin/env python3
"""
Data Pilots - Trust Scan API  v3
Website trust check (our own checks) + authenticated proxy to Papaya consent API.

Usage:
    python3 api/scan_server.py [--port 3001]

Endpoints (ours):
    POST /scan                           { "url": "https://example.com" }
    GET  /health

Papaya proxy endpoints (authenticated pass-through — no caching or transformation):
    GET  /papaya/<session_id>            → GET /api/v1/runs/<session_id>
    GET  /papaya/<session_id>/screenshots → GET /api/v1/runs/<session_id>/screenshots
    GET  /papaya/<session_id>/report      → GET /api/v1/runs/<session_id>/report
"""

import json
import os
import sys
import re
import ssl
import urllib.request
import urllib.parse
import urllib.error
from http.server import HTTPServer, BaseHTTPRequestHandler
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime


# ─────────────────────────────────────────────
# Config — use environment variables in production
# ─────────────────────────────────────────────
PORT             = int(os.environ.get("PORT", 3001))   # Render/Railway assign PORT via env
TIMEOUT          = 6            # seconds per individual HTTP check
MAX_HTML_BYTES   = 80_000       # bytes for content checks (keywords, etc.)
MAX_FOOTER_BYTES = 400_000      # enough to reach footer on large CMS-built sites
PAPAYA_API_BASE  = "https://papaya-consent-check-be11a0846ed5.herokuapp.com/api/v1"
PAPAYA_API_KEY   = os.environ.get("PAPAYA_API_KEY", "cck_live_270ac2d1_NUoykoCcU_5ux3cvXRy0enhmysyvTgjX")

PRIVACY_PATHS = ["/privacy-policy", "/privacy", "/privacy.html",
                 "/data-protection", "/data-privacy", "/cookie-policy", "/gdpr"]
TERMS_PATHS   = ["/terms", "/terms-of-service", "/terms-and-conditions",
                 "/legal", "/tos", "/terms.html", "/legal-notice"]
CONTACT_PATHS = ["/contact", "/contact-us", "/about", "/get-in-touch", "/about-us"]

AI_KEYWORDS = [
    "artificial intelligence", "ai-powered", "ai powered", "powered by ai",
    "machine learning", "chatgpt", "openai", "generative ai", "llm",
    "large language model", "ai assistant", "ai insights",
    "ai-generated", "ai generated",
]
COOKIE_KEYWORDS = [
    "cookie", "gdpr", "ccpa", "consent", "data protection",
    "we use cookies", "privacy preference",
]
GDPR_KEYWORDS = [
    "gdpr", "general data protection regulation", "data controller",
    "data processor", "right to access", "right to erasure", "right to be forgotten",
    "lawful basis", "legitimate interest", "data subject rights", "supervisory authority",
]
CCPA_KEYWORDS = [
    "ccpa", "california consumer privacy", "do not sell my",
    "right to know", "right to delete", "opt-out of sale",
]
DPA_KEYWORDS = [
    "data processing agreement", " dpa ", "data processor agreement",
    "sub-processor", "standard contractual clauses", "model clauses",
]
POLICY_REQUIRED_TOPICS = {
    "what is collected": ["we collect", "information we collect", "data we collect", "personal data we collect", "personal information we collect"],
    "why it is collected": ["we use your", "purposes", "why we collect", "legal basis", "how we use"],
    "third-party sharing": ["third party", "third-party", "share your data", "we share", "disclose to", "our partners"],
    "your rights":         ["your rights", "right to access", "right to delete", "right to object", "opt out", "opt-out"],
    "contact details":     ["contact us", "data controller", "data protection officer", "dpo@", "privacy@", "info@"],
}
COOKIE_POLICY_PATHS = ["/cookie-policy", "/cookie-notice", "/cookies", "/cookie-disclosure"]


# ─────────────────────────────────────────────
# Generic HTTP helpers
# ─────────────────────────────────────────────
def _ssl_ctx():
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_OPTIONAL
    return ctx


def fetch(url: str, method="GET", headers=None, body=None, max_bytes=MAX_HTML_BYTES) -> dict:
    """Returns { ok, status, headers, body, text, error }"""
    req_headers = {
        "User-Agent": "DataPilots-TrustCheck/1.0 (+https://datapilots.tech)",
    }
    if headers:
        req_headers.update(headers)

    data = json.dumps(body).encode() if body else None
    if data:
        req_headers["Content-Type"] = "application/json"

    req = urllib.request.Request(url, data=data, headers=req_headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT, context=_ssl_ctx()) as resp:
            raw = resp.read(max_bytes)
            ct  = resp.headers.get("Content-Type", "")
            text = raw.decode("utf-8", errors="replace")
            parsed = None
            try:
                if "json" in ct:
                    parsed = json.loads(raw)
            except Exception:
                pass
            return {
                "ok": True, "status": resp.status,
                "headers": dict(resp.headers),
                "text": text, "data": parsed, "error": None,
            }
    except urllib.error.HTTPError as e:
        return {"ok": False, "status": e.code, "headers": {}, "text": "", "data": None, "error": str(e)}
    except Exception as e:
        return {"ok": False, "status": None, "headers": {}, "text": "", "data": None, "error": str(e)}


def page_exists(base: str, paths: list) -> tuple:
    """Check if any of the given paths exist. Uses GET with tiny read to follow redirects."""
    for path in paths:
        r = fetch(base + path, method="GET", max_bytes=500)
        if r["ok"] and r["status"] and r["status"] < 400:
            return True, path
    return False, None


# ─────────────────────────────────────────────
# Papaya API — thin authenticated calls
# ─────────────────────────────────────────────
def papaya_call(method: str, path: str, body=None, max_bytes=200_000) -> dict:
    """Authenticated call to Papaya API. Returns fetch-style dict."""
    url = PAPAYA_API_BASE + path
    return fetch(
        url, method=method,
        headers={"Authorization": f"Bearer {PAPAYA_API_KEY}"},
        body=body, max_bytes=max_bytes,
    )


def papaya_start_run(url: str) -> dict:
    """
    Start a Papaya consent check run (reject_all, California).
    Returns the full Papaya run object on success, or {} on failure.
    The caller can use run['session_id'] and run['links'] as needed.
    """
    resp = papaya_call("POST", "/runs", {
        "url": url,
        "task": "reject_all",
        "state": "US-CA",
        "wait_for_debug_url_seconds": 2,
    })
    if not resp["ok"] or not resp["data"]:
        print(f"  [Papaya] start failed: {resp.get('error')} status={resp.get('status')}", flush=True)
        return {}
    run = resp["data"]
    print(f"  [Papaya] run started  session_id={run.get('session_id')}", flush=True)
    return run


# ─────────────────────────────────────────────
# Individual trust checks  (fast, own logic)
# ─────────────────────────────────────────────
def check_https(base: str, home: dict) -> dict:
    is_https = base.startswith("https://")
    if is_https and home["ok"]:
        return {"id": "https", "pillar": "safety", "status": "pass",
                "title": "Site uses HTTPS",
                "detail": "Your connection is encrypted. Buyers can see the padlock in the browser bar.",
                "tag": None}
    elif not is_https:
        return {"id": "https", "pillar": "safety", "status": "fail",
                "title": "Site is not on HTTPS",
                "detail": "Browsers mark non-HTTPS sites as 'Not Secure'. This is an immediate red flag for any buyer checking your site before a meeting.",
                "tag": "FIX THIS WEEK"}
    else:
        return {"id": "https", "pillar": "safety", "status": "warn",
                "title": "HTTPS but site did not respond cleanly",
                "detail": "Your URL starts with HTTPS but the site returned an error. Check your hosting.",
                "tag": "REVIEW"}


def check_security_headers(headers: dict) -> list:
    findings = []
    h = {k.lower(): v for k, v in headers.items()}

    if "content-security-policy" not in h:
        findings.append({
            "id": "csp", "pillar": "safety", "status": "warn",
            "title": "No Content Security Policy header",
            "detail": "CSP is a standard browser protection. Procurement security questionnaires often ask about it. A developer can add it in under an hour.",
            "tag": "REVIEW"
        })
    else:
        findings.append({"id": "csp", "pillar": "safety", "status": "pass",
                         "title": "Content Security Policy header present", "detail": None, "tag": None})

    if "x-frame-options" not in h and "content-security-policy" not in h:
        findings.append({
            "id": "xfo", "pillar": "safety", "status": "warn",
            "title": "No clickjacking protection header",
            "detail": "X-Frame-Options or CSP prevents your site being embedded in malicious pages. Easy to add.",
            "tag": "REVIEW"
        })

    if "strict-transport-security" not in h:
        findings.append({
            "id": "hsts", "pillar": "safety", "status": "warn",
            "title": "HSTS not enabled",
            "detail": "HSTS tells browsers to always use HTTPS. Without it, the first connection could be intercepted.",
            "tag": "QUICK WIN"
        })
    else:
        findings.append({"id": "hsts", "pillar": "safety", "status": "pass",
                         "title": "HSTS enabled", "detail": None, "tag": None})

    return findings


def check_privacy_page(base: str) -> dict:
    found, path = page_exists(base, PRIVACY_PATHS)
    if found:
        return {"id": "privacy", "pillar": "transparency", "status": "pass",
                "title": f"Privacy page found ({path})",
                "detail": "Buyers and procurement teams expect to see a privacy policy. You have one.",
                "tag": None}
    return {"id": "privacy", "pillar": "transparency", "status": "fail",
            "title": "No privacy page detected",
            "detail": "Over 70% of B2B buyers check for a privacy policy before signing. A missing policy is the most common trust-killer we find.",
            "tag": "FIX THIS WEEK"}


def check_terms_page(base: str) -> dict:
    found, path = page_exists(base, TERMS_PATHS)
    if found:
        return {"id": "terms", "pillar": "transparency", "status": "pass",
                "title": f"Terms of service found ({path})",
                "detail": "Your terms are findable. Good.", "tag": None}
    return {"id": "terms", "pillar": "transparency", "status": "warn",
            "title": "No terms of service page detected",
            "detail": "Enterprise procurement often requires a link to your terms. A missing terms page can stall a deal.",
            "tag": "QUICK WIN"}


def check_contact_page(base: str) -> dict:
    found, path = page_exists(base, CONTACT_PATHS)
    if found:
        return {"id": "contact", "pillar": "ux", "status": "pass",
                "title": f"Contact page found ({path})",
                "detail": "Buyers can find a way to reach you. This matters for trust.", "tag": None}
    return {"id": "contact", "pillar": "ux", "status": "warn",
            "title": "No contact page detected",
            "detail": "If a buyer can't easily find how to contact you, they lose confidence. A visible contact page lifts trust scores.",
            "tag": "QUICK WIN"}


def check_ai_disclosure(html: str) -> dict:
    lower = html.lower()
    if any(kw in lower for kw in AI_KEYWORDS):
        return {"id": "ai_disclose", "pillar": "ai_trust", "status": "pass",
                "title": "AI tool mention found on site",
                "detail": "Your site mentions AI tools or partners. Transparent AI disclosure builds buyer confidence.",
                "tag": None}
    return {"id": "ai_disclose", "pillar": "ai_trust", "status": "warn",
            "title": "No AI disclosure found on public site",
            "detail": "Over half of enterprise L&D buyers now ask about AI use before signing. If you use AI tools, a short note on your site prevents the question coming up in procurement.",
            "tag": "QUICK WIN"}


def check_cookie_consent(html: str) -> dict:
    lower = html.lower()
    found = [kw for kw in COOKIE_KEYWORDS if kw in lower]
    if len(found) >= 2:
        return {"id": "cookies", "pillar": "transparency", "status": "pass",
                "title": "Cookie or consent language found",
                "detail": "Your site appears to address cookies and consent. This is expected by EU and enterprise buyers.",
                "tag": None}
    return {"id": "cookies", "pillar": "transparency", "status": "warn",
            "title": "No cookie consent language detected",
            "detail": "GDPR requires most sites to inform visitors about cookies. Missing consent banners are a common finding in procurement reviews.",
            "tag": "REVIEW"}


def check_footer_policy_links(html: str, full_html: str = "") -> list:
    """
    Check whether Privacy, Terms, and Cookie policy links appear in the footer.
    full_html may be a larger fetch of the page used only for footer detection.
    """
    findings = []
    search_html = full_html if full_html else html
    lower = search_html.lower()

    footer_start = lower.rfind("<footer")
    footer_text  = lower[footer_start:] if footer_start != -1 else lower[-8000:]

    has_privacy = bool(re.search(r'href=["\'][^"\']*privac[^"\']*["\']', footer_text))
    has_terms   = bool(re.search(r'href=["\'][^"\']*term[^"\']*["\']',   footer_text))
    has_cookie  = bool(re.search(r'href=["\'][^"\']*cook[^"\']*["\']',   footer_text))

    if has_privacy and has_terms:
        findings.append({
            "id": "footer_links", "pillar": "ux", "status": "pass",
            "title": "Privacy Policy and Terms links found in footer",
            "detail": "Policy links are where buyers expect them. This passes the basic procurement page-check.",
            "tag": None,
        })
    elif has_privacy:
        findings.append({
            "id": "footer_links", "pillar": "ux", "status": "warn",
            "title": "Privacy link in footer — Terms link missing",
            "detail": "Enterprise procurement teams look for both. Adding a Terms link is a quick win.",
            "tag": "QUICK WIN",
        })
    else:
        findings.append({
            "id": "footer_links", "pillar": "ux", "status": "fail",
            "title": "Policy links not found in footer",
            "detail": (
                "Buyers scan the footer for Privacy Policy and Terms before any meeting. "
                "Not finding them is one of the most common reasons trust drops silently."
            ),
            "tag": "FIX THIS WEEK",
        })

    if has_cookie:
        findings.append({
            "id": "cookie_policy_link", "pillar": "transparency", "status": "pass",
            "title": "Cookie policy/disclosure link found in footer",
            "detail": "A visible cookie disclosure link is good practice and increasingly expected by privacy-aware buyers.",
            "tag": None,
        })

    return findings


def check_policy_content(base: str) -> list:
    findings = []

    privacy_url = None
    for path in PRIVACY_PATHS:
        r = fetch(base + path, method="GET", max_bytes=500)
        if r["ok"] and r["status"] and r["status"] < 400:
            privacy_url = base + path
            break
    if not privacy_url:
        return findings

    r    = fetch(privacy_url, method="GET", max_bytes=200_000)
    text = r.get("text", "").lower()
    if not text:
        return findings

    has_gdpr = any(kw in text for kw in GDPR_KEYWORDS)
    has_ccpa = any(kw in text for kw in CCPA_KEYWORDS)

    if has_gdpr:
        findings.append({
            "id": "policy_gdpr", "pillar": "transparency", "status": "pass",
            "title": "Privacy policy includes GDPR-aligned language",
            "detail": (
                "Your policy references GDPR concepts (data subject rights, lawful basis, etc.). "
                "This is what EU clients and enterprise procurement teams need to see."
            ),
            "tag": None,
        })
    else:
        findings.append({
            "id": "policy_gdpr", "pillar": "transparency", "status": "warn",
            "title": "Privacy policy doesn't reference GDPR",
            "detail": (
                "If any of your clients are EU-based, your privacy policy should explicitly "
                "address GDPR rights. Enterprise procurement in the UK and Europe will check this."
            ),
            "tag": "REVIEW",
        })

    if has_ccpa:
        findings.append({
            "id": "policy_ccpa", "pillar": "transparency", "status": "pass",
            "title": "Privacy policy addresses CCPA / California consumer rights",
            "detail": "Your policy covers California privacy rights. Good for US enterprise clients.",
            "tag": None,
        })

    missing = []
    for topic, keywords in POLICY_REQUIRED_TOPICS.items():
        if not any(kw in text for kw in keywords):
            missing.append(topic)

    if not missing:
        findings.append({
            "id": "policy_coverage", "pillar": "transparency", "status": "pass",
            "title": "Privacy policy covers all required topics",
            "detail": (
                "Your policy explains what data is collected, why, third-party sharing, "
                "visitor rights, and how to get in touch. Strong foundation."
            ),
            "tag": None,
        })
    elif len(missing) <= 2:
        findings.append({
            "id": "policy_coverage", "pillar": "transparency", "status": "warn",
            "title": f"Privacy policy may be missing {len(missing)} required section(s)",
            "detail": (
                f"We couldn't find clear coverage of: {'; '.join(missing)}. "
                f"GDPR Article 13/14 requires these topics to be addressed."
            ),
            "tag": "REVIEW",
        })
    else:
        findings.append({
            "id": "policy_coverage", "pillar": "transparency", "status": "fail",
            "title": f"Privacy policy is missing {len(missing)} required sections",
            "detail": (
                f"Missing: {'; '.join(missing)}. "
                f"A privacy policy that doesn't explain what's collected, why, and how to exercise rights "
                f"is unlikely to satisfy enterprise procurement requirements."
            ),
            "tag": "FIX THIS WEEK",
        })

    has_dpa = any(kw in text for kw in DPA_KEYWORDS)
    if has_dpa:
        findings.append({
            "id": "policy_dpa", "pillar": "transparency", "status": "pass",
            "title": "Data Processing Agreement language present",
            "detail": (
                "Your policy references data processing agreements or standard contractual clauses. "
                "Enterprise clients in regulated sectors will often ask for a signed DPA — "
                "having the language in your policy is a good first step."
            ),
            "tag": None,
        })
    else:
        findings.append({
            "id": "policy_dpa", "pillar": "transparency", "status": "info",
            "title": "No Data Processing Agreement language found",
            "detail": (
                "Many enterprise and public sector L&D clients require a Data Processing Agreement "
                "before signing. Adding DPA language to your privacy policy (or offering a separate DPA) "
                "removes a common procurement blocker."
            ),
            "tag": None,
        })

    has_date = bool(re.search(
        r"(last updated|last revised|effective date|updated:)\s*[:\-]?\s*\w+\s+\d{4}",
        text, re.IGNORECASE
    ))
    if not has_date:
        findings.append({
            "id": "policy_date", "pillar": "transparency", "status": "warn",
            "title": "Privacy policy has no 'last updated' date",
            "detail": (
                "Policies without a visible update date look stale. "
                "A dated policy signals active governance — buyers notice when a policy "
                "looks like it hasn't been reviewed in years."
            ),
            "tag": "QUICK WIN",
        })

    found_cookie_policy, _ = page_exists(base, COOKIE_POLICY_PATHS)
    if found_cookie_policy:
        findings.append({
            "id": "cookie_policy_page", "pillar": "transparency", "status": "pass",
            "title": "Separate cookie policy/disclosure page found",
            "detail": "A dedicated cookie disclosure page shows buyers and regulators you take data governance seriously.",
            "tag": None,
        })

    return findings


def check_sitemap(base: str) -> dict:
    r = fetch(base + "/sitemap.xml", method="GET", max_bytes=500)
    if r["ok"] and r["status"] and r["status"] < 400:
        return {"id": "sitemap", "pillar": "ux", "status": "pass",
                "title": "sitemap.xml found",
                "detail": "Good. Your site structure is discoverable.", "tag": None}
    return {"id": "sitemap", "pillar": "ux", "status": "info",
            "title": "No sitemap.xml found",
            "detail": "A sitemap helps search engines and accessibility tools navigate your site. Not critical but worth adding.",
            "tag": None}


# ─────────────────────────────────────────────
# Scoring
# ─────────────────────────────────────────────
PILLAR_WEIGHTS = {"ux": 25, "transparency": 30, "safety": 30, "ai_trust": 15}
STATUS_SCORE   = {"pass": 1.0, "warn": 0.5, "fail": 0.0, "info": 0.8}

def compute_scores(findings: list) -> dict:
    pillar_totals = {p: [] for p in PILLAR_WEIGHTS}
    for f in findings:
        p = f.get("pillar")
        if p in pillar_totals and f["status"] in STATUS_SCORE:
            pillar_totals[p].append(STATUS_SCORE[f["status"]])

    pillar_scores = {}
    for p, vals in pillar_totals.items():
        pillar_scores[p] = round(sum(vals) / len(vals) * 100) if vals else 50

    weighted = sum(pillar_scores[p] * PILLAR_WEIGHTS[p] / 100 for p in PILLAR_WEIGHTS)
    overall  = round(weighted)

    if overall >= 80:
        label = "Mission Ready"
    elif overall >= 60:
        label = "Pilot Ready"
    elif overall >= 40:
        label = "Pre-Flight"
    else:
        label = "Ground Check Needed"

    return {"overall": overall, "label": label, "pillars": pillar_scores}


# ─────────────────────────────────────────────
# Main scan orchestrator
# ─────────────────────────────────────────────
def normalise_url(raw: str) -> str:
    raw = raw.strip()
    if not raw.startswith(("http://", "https://")):
        raw = "https://" + raw
    return raw.rstrip("/")


def run_scan(raw_url: str, tier: str = "free") -> dict:
    base = normalise_url(raw_url)

    # Fetch home page: standard read for content checks, larger read for footer
    home      = fetch(base, method="GET", max_bytes=MAX_HTML_BYTES)
    home_full = fetch(base, method="GET", max_bytes=MAX_FOOTER_BYTES)
    html      = home.get("text", "")
    html_full = home_full.get("text", html)
    headers   = home.get("headers", {})

    findings = []

    with ThreadPoolExecutor(max_workers=8) as ex:
        futures = {
            ex.submit(check_https,               base, home):          "https",
            ex.submit(check_privacy_page,        base):                "privacy",
            ex.submit(check_terms_page,          base):                "terms",
            ex.submit(check_contact_page,        base):                "contact",
            ex.submit(check_ai_disclosure,       html):                "ai",
            ex.submit(check_cookie_consent,      html):                "cookies",
            ex.submit(check_sitemap,             base):                "sitemap",
            ex.submit(check_footer_policy_links, html, html_full):     "footer_links",
            ex.submit(check_policy_content,      base):                "policy_content",
        }
        for future in as_completed(futures, timeout=TIMEOUT + 4):
            try:
                result = future.result()
                if isinstance(result, list):
                    findings.extend(result)
                else:
                    findings.append(result)
            except Exception:
                pass

    findings.extend(check_security_headers(headers))

    scores = compute_scores(findings)

    actionable = [f for f in findings if f["status"] in ("fail", "warn") and f.get("tag")]
    actionable.sort(key=lambda f: {"FIX THIS WEEK": 0, "QUICK WIN": 1, "REVIEW": 2}.get(f.get("tag", ""), 3))

    # Start Papaya run — returns the full Papaya run object (includes session_id, links, debug_url)
    papaya_run = papaya_start_run(base)
    papaya_session_id = papaya_run.get("session_id")

    return {
        "url":               base,
        "scanned_at":        datetime.utcnow().isoformat() + "Z",
        "score":             scores["overall"],
        "score_label":       scores["label"],
        "tier":              tier,
        "pillars": {
            "ux":           {"score": scores["pillars"]["ux"],           "label": "User Experience"},
            "transparency": {"score": scores["pillars"]["transparency"], "label": "Transparency"},
            "safety":       {"score": scores["pillars"]["safety"],       "label": "Safety"},
            "ai_trust":     {"score": scores["pillars"]["ai_trust"],     "label": "AI Trust"},
        },
        "free_findings":     actionable[:3],
        "total_issues":      len([f for f in findings if f["status"] in ("fail", "warn")]),
        "papaya_session_id": papaya_session_id,
        "note": (
            "Free check covers your public-facing website. "
            "Upgrade to Co-Pilot to scan your learning portal or platform "
            "and unlock full step-by-step fix guides."
            if tier == "free" else
            "Full Co-Pilot scan."
        ),
    }


# ─────────────────────────────────────────────
# HTTP Server
# ─────────────────────────────────────────────
class ScanHandler(BaseHTTPRequestHandler):

    def log_message(self, fmt, *args):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {fmt % args}", flush=True)

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin",  "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")

    def _send_json(self, data: dict, status: int = 200):
        body = json.dumps(data, indent=2).encode()
        self.send_response(status)
        self.send_header("Content-Type",   "application/json")
        self.send_header("Content-Length", str(len(body)))
        self._cors()
        self.end_headers()
        self.wfile.write(body)

    def _proxy_papaya(self, papaya_path: str):
        """Proxy a request to Papaya API, forwarding the response as-is."""
        resp = papaya_call("GET", papaya_path, max_bytes=500_000)
        if not resp["ok"]:
            self._send_json({"error": f"Papaya returned {resp.get('status')}"}, resp.get("status") or 502)
            return
        # Return as JSON if parsed, otherwise raw text
        if resp["data"] is not None:
            self._send_json(resp["data"])
        else:
            # e.g. markdown report (text/markdown)
            body = resp["text"].encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type",   "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self._cors()
            self.end_headers()
            self.wfile.write(body)

    def do_HEAD(self):
        self.send_response(200)
        self._cors()
        self.end_headers()

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_GET(self):
        if self.path == "/health":
            self._send_json({"status": "ok", "service": "Data Pilots Scan API", "version": "3.0"})

        elif self.path.startswith("/papaya/"):
            # Parse session_id and optional sub-path
            # Supported:
            #   /papaya/<id>              → /runs/<id>              (status)
            #   /papaya/<id>/screenshots  → /runs/<id>/screenshots  (image URLs)
            #   /papaya/<id>/report       → /runs/<id>/report       (markdown)
            rest = self.path[len("/papaya/"):]          # e.g. "abc123" or "abc123/screenshots"
            parts = rest.strip("/").split("/", 1)
            session_id = parts[0]
            sub = parts[1] if len(parts) > 1 else ""

            allowed_subs = {"", "screenshots", "report"}
            if sub not in allowed_subs:
                self._send_json({"error": "Not found"}, 404)
                return

            papaya_path = f"/runs/{session_id}" + (f"/{sub}" if sub else "")
            self._proxy_papaya(papaya_path)

        else:
            self._send_json({"error": "Not found"}, 404)

    def do_POST(self):
        if self.path != "/scan":
            self._send_json({"error": "Not found"}, 404)
            return

        length = int(self.headers.get("Content-Length", 0))
        body   = self.rfile.read(length)

        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            self._send_json({"error": "Invalid JSON"}, 400)
            return

        raw_url = payload.get("url", "").strip()
        if not raw_url:
            self._send_json({"error": "url is required"}, 400)
            return

        tier = payload.get("tier", "free")
        if tier not in ("free", "paid"):
            tier = "free"

        print(f"  Scanning: {raw_url}  tier={tier}", flush=True)
        try:
            result = run_scan(raw_url, tier=tier)
            self._send_json(result)
        except Exception as e:
            self._send_json({"error": f"Scan failed: {str(e)}"}, 500)


def main():
    port = PORT
    if "--port" in sys.argv:  # local override still works: python3 scan_server.py --port 3002
        port = int(sys.argv[sys.argv.index("--port") + 1])

    server = HTTPServer(("0.0.0.0", port), ScanHandler)
    print(f"Data Pilots Scan API v3  http://localhost:{port}", flush=True)
    print(f"  POST /scan", flush=True)
    print(f"  GET  /papaya/<id>             → proxies to Papaya GET /runs/<id>", flush=True)
    print(f"  GET  /papaya/<id>/screenshots → proxies to Papaya GET /runs/<id>/screenshots", flush=True)
    print(f"  GET  /papaya/<id>/report      → proxies to Papaya GET /runs/<id>/report", flush=True)
    print(f"  GET  /health", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
